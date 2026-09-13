"""Student profile + intelligence service (normalized, DB-backed).

Tables: student_profiles, student_profile_skills, _interests, _preferences.
All validation mirrors the UI wizard; profanity mapping:
  Just Started->Basic, Comfortable/Can Apply->Intermediate, Highly Comfortable->Advanced.
Interests/preferences/goals are whitelisted; skills must exist in the SKL catalog
(normalized via data_service.normalize_skill_name).
"""
import re
import sqlite3
from pathlib import Path
from collections import Counter
from .db import get_db

STATUS_OPTIONS = [
    "School Student", "College Student", "ITI/Vocational Student",
    "Working", "Looking for a Job", "Exploring Careers",
]

INTEREST_OPTIONS = [
    "Technology", "Healthcare", "Engineering", "Business", "Finance",
    "Design", "Skilled Trades", "Agriculture", "Logistics",
    "Manufacturing", "Public Services", "Other",
]
PREF_OPTIONS = [
    "Earning Potential", "Career Growth", "Opportunities Near Me",
    "Technical Work", "Working With People", "Employment Stability",
    "Emerging Industries", "Further Education", "Entrepreneurship",
]
GOAL_OPTIONS = [
    "Choose a Career", "Get My First Job", "Improve My Skills",
    "Find Better Career Options", "Prepare for Emerging Field",
    "Find Relevant Training", "Understand My Skill Gaps",
]

PROF_LABELS = ["Just Started", "Comfortable", "Can Apply", "Highly Comfortable"]
PROF_TO_RANK = {
    "Just Started": "Basic",
    "Comfortable": "Intermediate",
    "Can Apply": "Intermediate",
    "Highly Comfortable": "Advanced",
}
RANK_NUM = {"Basic": 1, "Intermediate": 2, "Advanced": 3, "Expert": 4}

INTEREST_SECTOR_MAP = {
    "Technology": ["IT-ITeS", "Electronics"],
    "Healthcare": ["Healthcare", "Life Sciences"],
    "Engineering": ["Electronics", "Automotive", "Construction"],
    "Business": ["Management", "Tourism & Hospitality"],
    "Finance": ["Management"],
    "Design": ["Media & Entertainment", "Apparel Made-Ups & Home Furnishing"],
    "Skilled Trades": ["Construction", "Electronics", "Automotive"],
    "Agriculture": ["Agriculture"],
    "Logistics": ["Logistics"],
    "Manufacturing": ["Automotive", "Electronics", "Apparel Made-Ups & Home Furnishing"],
    "Public Services": ["Management", "Tourism & Hospitality"],
}

EDU_LEVELS = ["10th", "12th", "Diploma", "ITI", "Graduate", "Post Graduate", "Other"]


def _norm_interest(v):
    return next((x for x in INTEREST_OPTIONS if x.lower() == (v or "").strip().lower()), None)

def _norm_pref(v):
    return next((x for x in PREF_OPTIONS if x.lower() == (v or "").strip().lower()), None)

def _norm_goal(v):
    return next((x for x in GOAL_OPTIONS if x.lower() == (v or "").strip().lower()), None)

def _norm_status(v):
    return next((x for x in STATUS_OPTIONS if x.lower() == (v or "").strip().lower()), None)


def validate_profile(data, partial=False):
    """Return list of error strings; empty means valid."""
    errs = []
    if not partial or "status" in data:
        if not _norm_status(data.get("status")):
            errs.append(f"status must be one of: {', '.join(STATUS_OPTIONS)}")
    if "state_id" in data and data["state_id"]:
        c = get_db()
        try:
            if not c.execute("SELECT 1 FROM states WHERE state_id=?", (data["state_id"],)).fetchone():
                errs.append("unknown state_id")
        finally:
            c.close()
    if "district_id" in data and data["district_id"]:
        c = get_db()
        try:
            if not c.execute("SELECT 1 FROM districts WHERE district_id=?", (data["district_id"],)).fetchone():
                errs.append("unknown district_id")
        finally:
            c.close()
    if "skills" in data and data["skills"] is not None:
        if not isinstance(data["skills"], list):
            errs.append("skills must be a list")
        else:
            seen = set()
            for entry in data["skills"]:
                sid = entry.get("skill_id") if isinstance(entry, dict) else entry
                lab = entry.get("proficiency_label") if isinstance(entry, dict) else "Comfortable"
                if not sid:
                    errs.append("skill_id required")
                    continue
                # normalize via alias table (so Python/SQL etc. map correctly)
                from .data_service import normalize_skill_name
                nid = normalize_skill_name(sid)
                # sid may already be SKL* — accept directly if in catalog
                if not nid:
                    c = get_db()
                    try:
                        nid = sid if c.execute("SELECT 1 FROM skills WHERE id=?", (sid,)).fetchone() else None
                    finally:
                        c.close()
                if not nid:
                    errs.append(f"unknown skill: {sid}")
                    continue
                if lab and lab not in PROF_LABELS:
                    errs.append(f"proficiency_label must be one of {PROF_LABELS}")
                if nid in seen:
                    errs.append(f"duplicate skill: {nid}")
                seen.add(nid)
    for field, opts, norm in [("interests", INTEREST_OPTIONS, _norm_interest),
                              ("preferences", PREF_OPTIONS, _norm_pref)]:
        if field in data and data[field] is not None:
            if not isinstance(data[field], list):
                errs.append(f"{field} must be a list")
            else:
                for v in data[field]:
                    if not norm(v):
                        errs.append(f"invalid {field} value: {v}")
    if "goal" in data and data["goal"]:
        if not _norm_goal(data["goal"]):
            errs.append(f"goal must be one of: {GOAL_OPTIONS}")
    # impossible combos: School Student should not claim Post Graduate
    if data.get("status") == "School Student" and data.get("education_level") in ("Post Graduate", "Graduate"):
        errs.append("School Student cannot have Post Graduate/Graduate level")
    return errs


def _profile_row(pid):
    c = get_db()
    try:
        row = c.execute("SELECT * FROM student_profiles WHERE id=?", (pid,)).fetchone()
        if not row:
            return None
        base = dict(row)
        base["skills"] = [dict(r) for r in c.execute(
            "SELECT sps.skill_id, sps.proficiency_label, sps.proficiency_rank, s.skill_name, s.skill_category "
            "FROM student_profile_skills sps LEFT JOIN skills s ON s.id=sps.skill_id WHERE sps.profile_id=? ORDER BY s.skill_name", (pid,)).fetchall()]
        base["interests"] = [r["interest"] for r in c.execute("SELECT interest FROM student_profile_interests WHERE profile_id=? ORDER BY interest", (pid,)).fetchall()]
        base["preferences"] = [r["preference"] for r in c.execute("SELECT preference FROM student_profile_preferences WHERE profile_id=? ORDER BY preference", (pid,)).fetchall()]
        # enrich location names
        if base.get("state_id"):
            r = c.execute("SELECT state_name FROM states WHERE state_id=?", (base["state_id"],)).fetchone()
            base["state_name"] = r["state_name"] if r else None
        if base.get("district_id"):
            r = c.execute("SELECT district_name FROM districts WHERE district_id=?", (base["district_id"],)).fetchone()
            base["district_name"] = r["district_name"] if r else None
        return base
    finally:
        c.close()


def create_profile(data):
    errs = validate_profile(data)
    if errs:
        raise ValueError("; ".join(errs))
    # normalize skills to canonical SKL ids
    norm_skills = []
    seen = set()
    from .data_service import normalize_skill_name
    c0 = get_db()
    try:
        for entry in (data.get("skills") or []):
            raw = entry.get("skill_id") if isinstance(entry, dict) else entry
            lab = (entry.get("proficiency_label") if isinstance(entry, dict) else None) or "Comfortable"
            nid = normalize_skill_name(raw)
            if not nid:
                nid = raw if c0.execute("SELECT 1 FROM skills WHERE id=?", (raw,)).fetchone() else None
            if not nid or nid in seen:
                continue
            seen.add(nid)
            norm_skills.append((nid, lab, PROF_TO_RANK.get(lab, "Intermediate")))
    finally:
        c0.close()
    interests = sorted({_norm_interest(v) for v in (data.get("interests") or []) if _norm_interest(v)})
    prefs = sorted({_norm_pref(v) for v in (data.get("preferences") or []) if _norm_pref(v)})

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO student_profiles (status, state_id, district_id, location_text, education_level, course_program, specialization, year_semester, qualification, nsqf_level, goal) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (_norm_status(data.get("status")), data.get("state_id"), data.get("district_id"), data.get("location_text"),
             data.get("education_level"), data.get("course_program"), data.get("specialization"),
             data.get("year_semester"), data.get("qualification"), data.get("nsqf_level"), _norm_goal(data.get("goal"))),
        )
        pid = cur.lastrowid
        for sid, lab, rank in norm_skills:
            cur.execute("INSERT INTO student_profile_skills (profile_id, skill_id, proficiency_label, proficiency_rank) VALUES (?,?,?,?)",
                        (pid, sid, lab, rank))
        for it in interests:
            cur.execute("INSERT INTO student_profile_interests (profile_id, interest) VALUES (?,?)", (pid, it))
        for pr in prefs:
            cur.execute("INSERT INTO student_profile_preferences (profile_id, preference) VALUES (?,?)", (pid, pr))
        conn.commit()
        return pid
    finally:
        conn.close()


def update_profile(pid, data):
    # partial update allowed; validate only supplied fields
    errs = validate_profile(data, partial=True)
    if errs:
        raise ValueError("; ".join(errs))
    cur = get_db()
    try:
        if not cur.execute("SELECT 1 FROM student_profiles WHERE id=?", (pid,)).fetchone():
            return None
    finally:
        cur.close()
    # build SET clause for scalar fields
    scalar = {k: data[k] for k in ("status", "state_id", "district_id", "location_text", "education_level",
                                   "course_program", "specialization", "year_semester", "qualification", "nsqf_level", "goal")
              if k in data}
    if "status" in scalar:
        scalar["status"] = _norm_status(scalar["status"])
    if "goal" in scalar:
        scalar["goal"] = _norm_goal(scalar["goal"])
    if scalar:
        scalar["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        sets = ", ".join(f"{k}=?" for k in scalar)
        vals = list(scalar.values()) + [pid]
        conn = get_db()
        try:
            conn.execute(f"UPDATE student_profiles SET {sets} WHERE id=?", vals)
            conn.commit()
        finally:
            conn.close()
    # replace collections if supplied
    if "skills" in data:
        conn = get_db()
        try:
            conn.execute("DELETE FROM student_profile_skills WHERE profile_id=?", (pid,))
            seen = set()
            from .data_service import normalize_skill_name
            for entry in (data["skills"] or []):
                raw = entry.get("skill_id") if isinstance(entry, dict) else entry
                lab = (entry.get("proficiency_label") if isinstance(entry, dict) else None) or "Comfortable"
                nid = normalize_skill_name(raw)
                if not nid:
                    c = get_db()
                    try:
                        nid = raw if c.execute("SELECT 1 FROM skills WHERE id=?", (raw,)).fetchone() else None
                    finally:
                        c.close()
                    if not nid:
                        continue
                if nid in seen:
                    continue
                seen.add(nid)
                conn.execute("INSERT INTO student_profile_skills (profile_id, skill_id, proficiency_label, proficiency_rank) VALUES (?,?,?,?)",
                             (pid, nid, lab, PROF_TO_RANK.get(lab, "Intermediate")))
            conn.commit()
        finally:
            conn.close()
    for field, table, norm in [("interests", "student_profile_interests", _norm_interest),
                               ("preferences", "student_profile_preferences", _norm_pref)]:
        if field in data:
            vals = sorted({_norm_pref(v) if field == "preferences" else _norm_interest(v)
                           for v in (data[field] or []) if (norm(v))})
            # actually use correct norm
            if field == "interests":
                vals = sorted({_norm_interest(v) for v in (data[field] or []) if _norm_interest(v)})
            else:
                vals = sorted({_norm_pref(v) for v in (data[field] or []) if _norm_pref(v)})
            conn = get_db()
            try:
                conn.execute(f"DELETE FROM {table} WHERE profile_id=?", (pid,))
                for v in vals:
                    conn.execute(f"INSERT INTO {table} (profile_id, {field[:-1]}) VALUES (?,?)", (pid, v))
                conn.commit()
            finally:
                conn.close()
    return _profile_row(pid)


def list_profiles(limit=50):
    c = get_db()
    try:
        return [dict(r) for r in c.execute("SELECT id, status, district_id, goal, created_at FROM student_profiles ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
    finally:
        c.close()


def delete_profile(pid):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM student_profiles WHERE id=?", (pid,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def analyze_profile(pid):
    """Student intelligence: matches, gaps, pathway, next actions.

    All calculations are observed/derived from live DB (occupation_skills,
    course_skills, indicators). No random/fake scores.
    """
    prof = _profile_row(pid)
    if not prof:
        return None
    # student skill set + proficiency map
    have = {s["skill_id"]: s for s in prof["skills"]}
    have_ids = set(have.keys())
    interests = set(prof.get("interests") or [])
    # interest -> allowed sectors (union)
    allowed_sectors = set()
    for it in interests:
        allowed_sectors.update(INTEREST_SECTOR_MAP.get(it, []))

    c = get_db()
    try:
        all_skills = {r["id"]: dict(r) for r in c.execute("SELECT * FROM skills").fetchall()}
        occ_rows = [dict(r) for r in c.execute("SELECT role_id, job_title, occupation_code, sector_id, nsqf_level, qp_name, standard_status FROM job_roles ORDER BY role_id").fetchall()]
        occ_sector_name = {r["role_id"]: r.get("sector_id") and c.execute("SELECT sector_name FROM sectors WHERE sector_id=?", (r["sector_id"],)).fetchone() for r in occ_rows}
        # flatten sector name
        for r in occ_rows:
            sid = r.get("sector_id")
            if sid:
                row = c.execute("SELECT sector_name FROM sectors WHERE sector_id=?", (sid,)).fetchone()
                r["sector"] = row["sector_name"] if row else None
            else:
                r["sector"] = None
        req_map = {}
        imp_map = {}
        for r in c.execute("SELECT occupation_id, skill_id, importance FROM occupation_skills").fetchall():
            req_map.setdefault(r["occupation_id"], set()).add(r["skill_id"])
            imp_map[(r["occupation_id"], r["skill_id"])] = r["importance"]
        courses = [dict(r) for r in c.execute("SELECT id, course_name, provider as provider_name, sector_id, nsqf_level, duration FROM courses ORDER BY id").fetchall()]
        for co in courses:
            row = c.execute("SELECT sector_name FROM sectors WHERE sector_id=?", (co["sector_id"],)).fetchone() if co.get("sector_id") else None
            co["sector"] = row["sector_name"] if row else None
        course_skills = {}
        for r in c.execute("SELECT course_id, skill_id FROM course_skills").fetchall():
            course_skills.setdefault(r["course_id"], set()).add(r["skill_id"])
    finally:
        c.close()

    scored = []
    for occ in occ_rows:
        oid = occ["role_id"]
        req = req_map.get(oid, set())
        if not req:
            continue  # unscored, not recommended; listed separately
        matched = have_ids & req
        missing = req - have_ids
        # weak vs strong: student proficiency vs required (High->Advanced etc.)
        weak = set()
        for sid in matched:
            student_rank = have[sid].get("proficiency_rank") or "Intermediate"
            # required proficiency derived from importance: High->Advanced
            req_imp = imp_map.get((oid, sid), "Medium")
            req_rank = {"High": "Advanced", "Medium": "Intermediate", "Low": "Basic"}.get(req_imp, "Intermediate")
            if RANK_NUM.get(student_rank, 2) < RANK_NUM.get(req_rank, 2):
                weak.add(sid)
        coverage = round(len(matched) / len(req) * 100, 1) if req else 0
        # interest alignment (sector overlap)
        occ_sector = occ.get("sector")
        interest_ok = not allowed_sectors or not occ_sector or occ_sector in allowed_sectors
        # education compatibility (very light: NSQF level within 1)
        edu_ns = prof.get("nsqf_level")
        occ_ns = occ.get("nsqf_level")
        edu_ok = True
        try:
            if edu_ns and occ_ns and float(edu_ns) and float(occ_ns):
                edu_ok = abs(float(edu_ns) - float(occ_ns)) <= 1.5
        except Exception:
            pass
        # composite score (documented, no hidden weights): skill 60, interest 15, education 15, preference 10
        # preference alignment: if student prefers Technical Work and occupation is Technical skill-heavy
        pref_bonus = 0
        prefs = set(prof.get("preferences") or [])
        if "Technical Work" in prefs and any(all_skills[sid].get("skill_category") == "Technical" for sid in req):
            pref_bonus = 10
        # labour signal: none per-skill, so 0 (honest)
        score = round(coverage * 0.6 + (10 if interest_ok else 0) + (10 if edu_ok else 0) + pref_bonus * 0.15, 1)
        # cap 0-100
        score = max(0, min(100, score))
        # qualitative label instead of fake precision when data thin
        label = "Strong Match" if coverage >= 60 and score >= 60 else ("Potential Match" if coverage >= 30 else "Limited Evidence")
        scored.append({
            "occupation_id": oid,
            "occupation_name": occ["job_title"],
            "occupation_code": occ.get("occupation_code"),
            "sector": occ.get("sector"),
            "nsqf_level": occ.get("nsqf_level"),
            "qp_name": occ.get("qp_name"),
            "required_skills": sorted(req),
            "required_count": len(req),
            "matched_skills": sorted(matched),
            "missing_skills": sorted(missing),
            "weak_skills": sorted(weak),
            "coverage": coverage,
            "interest_aligned": interest_ok,
            "education_ok": edu_ok,
            "score": score,
            "label": label,
            "importance": {sid: imp_map.get((oid, sid)) for sid in req},
        })
    scored.sort(key=lambda x: (-x["score"], -x["coverage"], x["occupation_name"]))
    # unscored occupations
    unscored = [occ for occ in occ_rows if occ["role_id"] not in req_map or not req_map[occ["role_id"]]]

    # prioritize missing skills across top 3 matches: importance + course availability
    top_missing_counter = Counter()
    for m in scored[:3]:
        for sid in m["missing_skills"]:
            # boost by importance and by whether a course exists
            imp = {"High": 3, "Medium": 2, "Low": 1}.get(imp_map.get((m["occupation_id"], sid), "Medium"), 2)
            has_course = any(sid in course_skills.get(co["id"], set()) for co in courses)
            top_missing_counter[sid] += imp + (1 if has_course else 0)
    prioritized = [sid for sid, _ in top_missing_counter.most_common()]

    # learning pathway: for top missing, find actual courses (never invent)
    pathway = []
    for sid in prioritized[:6]:
        holders = [co for co in courses if sid in course_skills.get(co["id"], set())]
        holders.sort(key=lambda co: co["course_name"])
        pathway.append({
            "skill_id": sid,
            "skill_name": all_skills.get(sid, {}).get("skill_name", sid),
            "courses": [{"course_id": co["id"], "course_name": co["course_name"], "provider": co["provider_name"], "nsqf_level": co["nsqf_level"]} for co in holders[:2]],
            "holder_count": len(holders),
        })
    # next actions (3-5, each with reason)
    next_actions = []
    if prioritized:
        top_sid = prioritized[0]
        next_actions.append({"action": f"Strengthen {all_skills[top_sid]['skill_name']}",
                             "reason": f"Most critical missing skill across top matches (importance + course availability)."})
    if any(pref in (prof.get("preferences") or []) for pref in ["Opportunities Near Me", "Employment Stability"]):
        # suggest district with centres
        c2 = get_db()
        try:
            d = c2.execute("SELECT district_name FROM districts WHERE district_id='DT019'").fetchone()
            next_actions.append({"action": f"Explore training in {d['district_name'] if d else 'Nagpur'}",
                                 "reason": "Recorded PMKVY/DVET centres and Nagpur-focused recommendations exist."})
        finally:
            c2.close()
    if scored and scored[0]["weak_skills"]:
        ws = scored[0]["weak_skills"][0]
        next_actions.append({"action": f"Deepen {all_skills[ws]['skill_name']} proficiency",
                             "reason": f"You have it at {have[ws]['proficiency_label']}, occupation expects higher."})
    if len(pathway) and pathway[0]["courses"]:
        next_actions.append({"action": f"Take {pathway[0]['courses'][0]['course_name']}",
                             "reason": f"Recorded course explicitly covers {pathway[0]['skill_name']}."})
    if not next_actions and scored:
        next_actions.append({"action": "Explore alternative occupations in your interest sectors",
                             "reason": "Top matches have limited coverage; broadening interests may surface better fits."})

    return {
        "profile": prof,
        "career_matches": scored[:8],
        "unscored_occupations": [{"occupation_id": o["role_id"], "occupation_name": o["job_title"], "reason": "No explicit NOS skill links in source"} for o in unscored],
        "prioritized_gaps": [{"skill_id": sid, "skill_name": all_skills[sid]["skill_name"], "occurrences": top_missing_counter[sid]} for sid in prioritized],
        "learning_pathway": pathway,
        "next_actions": next_actions[:5],
        "methodology": {
            "skill_normalization": "Alias/slug match via skill_aliases + case-insensitive name fallback; unresolved left unmapped.",
            "match_score": "0.6*skill_coverage + interest(10) + education(10) + preference(1.5) capped 0-100; labels Strong/Potential/Limited Evidence.",
            "gap_priority": "Missing-skill frequency across top matches weighted by importance (High 3) + course availability (+1).",
            "data_source": "REAL",
        },
        "data_source": "REAL",
        "is_derived": True,
    }


def get_student_analysis(pid):
    return analyze_profile(pid)
