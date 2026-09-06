"""Gap analysis on the Real Evidence Dataset.

Coverage-alignment methodology (documented — market-demand component is
unavailable because JOB_DEMAND/EMPLOYER_REQUIREMENTS are empty):
  required(course) = union of catalog skills text-matched from the
                     related_skills of roles whose title matches the
                     course's target_roles phrases (match basis recorded;
                     unmapped phrases reported, never forced)
  alignment_score  = (adequate + 0.5 * partial) / len(required) * 100
Industry proficiency defaults to Intermediate (no employer evidence for
these skills); curriculum proficiency comes from CURRICULUM rows.
"""
from .db import get_db
from .data_service import split_ids, tokens, skill_ids_for_phrase, normalize_skill_name
from .analytics_service import compute_skill_demand

PROF_RANK = {"Basic": 1, "Beginner": 1, "Intermediate": 2, "Advanced": 3, "Expert": 4}


def _rows(q, args=()):
    c = get_db()
    try:
        return [dict(r) for r in c.execute(q, args).fetchall()]
    finally:
        c.close()


def _role_match_score(phrase, role):
    pt = tokens(phrase)
    for field in (role.get("normalized_role") or "", role.get("job_title") or ""):
        rt = tokens(field)
        if pt and rt and (pt <= rt or rt <= pt):
            return True
    return False


def course_alignment(course_id):
    c = get_db()
    try:
        co = c.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        if not co:
            return None
        co = dict(co)
        roles = [dict(r) for r in c.execute("SELECT * FROM job_roles").fetchall()]
        skills = {r["id"]: dict(r) for r in c.execute("SELECT * FROM skills").fetchall()}
        cur = [dict(r) for r in c.execute("SELECT * FROM curriculum WHERE course_id=?", (course_id,)).fetchall()]
    finally:
        c.close()
    taught = set(split_ids(co.get("skills_taught")))
    taught |= {m["skill_id"] for m in cur if m.get("skill_id")}
    required = set()
    matched_roles, unmapped_phrases, unmatched_targets = [], [], []
    for phrase in split_ids(co.get("target_roles")):
        hit_roles = [r for r in roles if _role_match_score(phrase, r)]
        if not hit_roles:
            unmatched_targets.append(phrase)
            continue
        for r in hit_roles:
            matched_roles.append(r["role_id"])
            for sp in split_ids(r.get("related_skills")):
                hits = skill_ids_for_phrase(sp, skills)
                if hits:
                    required.update(hits)
                elif sp not in unmapped_phrases:
                    unmapped_phrases.append(sp)
    emp = [e for e in _rows("SELECT skill_id, required_proficiency FROM employer_surveys") if (e.get("skill_id") or "") in skills]
    prof = {}
    for e in emp:
        prof.setdefault(e["skill_id"], []).append(e.get("required_proficiency") or "Intermediate")

    def ind_prof(sid):
        lst = prof.get(sid, [])
        if not lst:
            return "Intermediate"
        # Deterministic majority vote. Ties MUST NOT use max(set(...)) —
        # set iteration order depends on PYTHONHASHSEED, which made the same
        # DB return 75.0 in one process and 62.5 in another. Ties resolve to
        # the lower proficiency (conservative: never overstate a gap).
        best, best_n = "Intermediate", -1
        for cand in sorted(set(lst), key=lambda p: PROF_RANK.get(p, 2)):
            n = lst.count(cand)
            if n > best_n:
                best, best_n = cand, n
        return best

    def cur_prof(sid):
        for m in cur:
            if m.get("skill_id") == sid:
                return m.get("proficiency_level") or "Intermediate"
        return "Beginner" if sid not in taught else "Intermediate"

    demand = {s["id"]: s["demand_score"] for s in compute_skill_demand()}
    missing, partial, adequate = [], [], []
    for sid in sorted(required):
        sname = skills.get(sid, {}).get("skill_name", sid)
        if sid not in taught:
            missing.append(
                {
                    "skill_id": sid,
                    "skill_name": sname,
                    "gap": "Major gap",
                    "industry_proficiency": ind_prof(sid),
                    "demand_score": demand.get(sid),
                }
            )
        else:
            ip, cp = PROF_RANK.get(ind_prof(sid), 2), PROF_RANK.get(cur_prof(sid), 2)
            if cp >= ip:
                adequate.append(
                    {
                        "skill_id": sid,
                        "skill_name": sname,
                        "gap": "Covered",
                        "industry_proficiency": ind_prof(sid),
                        "curriculum_proficiency": cur_prof(sid),
                        "demand_score": demand.get(sid),
                    }
                )
            else:
                partial.append(
                    {
                        "skill_id": sid,
                        "skill_name": sname,
                        "gap": "Partial gap",
                        "industry_proficiency": ind_prof(sid),
                        "curriculum_proficiency": cur_prof(sid),
                        "demand_score": demand.get(sid),
                    }
                )
    denom = len(required) if required else 1
    if not required and unmatched_targets:
        # The course's stated target roles are absent from the role catalog:
        # scoring 0 would be a false signal, so assessment is withheld.
        return {
            "course": co,
            "alignment_score": None,
            "recommended_action": "Cannot assess",
            "industry_skill_count": 0,
            "curriculum_skill_count": len(taught),
            "matched": 0,
            "missing_count": 0,
            "missing_skills": [],
            "partial_skills": [],
            "adequate_skills": [],
            "obsolete_skills": [],
            "recommended_additions": [],
            "recommended_updates": [],
            "low_relevance_review": [],
            "matched_roles": [],
            "unmapped_role_phrases": unmatched_targets,
            "unmapped_requirement_phrases": unmapped_phrases,
            "methodology": "withheld: target roles not present in the role catalog",
            "evidence": {
                "source": "NCO 2015 job_roles + QP curriculum (Real Evidence Dataset)",
                "data_type": "real public sources (is_synthetic=0)",
            },
        }
    score = round((len(adequate) + 0.5 * len(partial)) / denom * 100, 1)
    if score >= 80:
        action = "Maintain"
    elif score >= 65:
        action = "Minor Update"
    elif score >= 45:
        action = "Major Update"
    else:
        action = "Retire (review)"
    rec_add = [
        f"Add {m['skill_name']} module (needs {m['industry_proficiency']}) — required by matched roles but not in this curriculum."
        for m in missing[:5]
    ]
    rec_up = [
        f"Deepen {m['skill_name']} from {m['curriculum_proficiency']} to {m['industry_proficiency']} (curriculum proficiency below role expectation)."
        for m in partial[:5]
    ]
    return {
        "course": co,
        "alignment_score": score,
        "recommended_action": action,
        "industry_skill_count": len(required),
        "curriculum_skill_count": len(taught),
        "matched": len(adequate) + len(partial),
        "missing_count": len(missing),
        "missing_skills": missing,
        "partial_skills": partial,
        "adequate_skills": adequate,
        "obsolete_skills": [],
        "recommended_additions": rec_add,
        "recommended_updates": rec_up,
        "low_relevance_review": [],
        "matched_roles": sorted(set(matched_roles)),
        "unmapped_role_phrases": unmatched_targets,
        "unmapped_requirement_phrases": unmapped_phrases,
        "methodology": "coverage alignment = matched/required role-mapped skills; market-demand component unavailable (no demand signals in dataset)",
        "evidence": {
            "source": "NCO 2015 job_roles + QP curriculum (Real Evidence Dataset)",
            "data_type": "real public sources (is_synthetic=0)",
        },
    }


def skill_gap_for_skill(skill_id):
    """Gap view for a single skill: which courses teach it, which roles need it."""
    from .analytics_service import role_skill_map, course_skill_map, skill_maps

    skills = skill_maps()
    if skill_id not in skills:
        return None
    role_req, _ = role_skill_map()
    _courses, cmap = course_skill_map()
    required_by = sorted([rid for rid, sids in role_req.items() if skill_id in sids])
    taught_by = sorted([cid for cid, sids in cmap.items() if skill_id in sids])
    if required_by and not taught_by:
        severity, status = "High", "Missing from all courses"
    elif required_by and taught_by:
        severity, status = "Low", "Covered by at least one course"
    elif not required_by and taught_by:
        severity, status = "Info", "Taught but no mapped role requirement in current catalog"
    else:
        severity, status = "Unknown", "No mapped requirement or course coverage"
    return {
        "skill_id": skill_id,
        "skill_name": skills[skill_id]["skill_name"],
        "required_by_roles": required_by,
        "taught_by_courses": taught_by,
        "gap_status": status,
        "gap_severity": severity,
        "methodology": "role requirements text-matched from NCO related_skills vs QP-taught skills; unmapped phrases excluded, never forced",
        "evidence": "NCO 2015 job_roles + QP curriculum (Real Evidence Dataset, is_synthetic=0)",
    }


def district_detail(district_id):
    c = get_db()
    try:
        d = c.execute("SELECT * FROM district_capacity WHERE district_id=?", (district_id,)).fetchone()
        if not d:
            return None
        district = dict(d)
        centres = [dict(r) for r in c.execute(
            "SELECT * FROM training_centres WHERE district=? ORDER BY centre_name", (district["district"],)
        ).fetchall()]
        placements = [dict(r) for r in c.execute(
            "SELECT p.*, co.course_name FROM placements p LEFT JOIN courses co ON co.id=p.course_id "
            "WHERE p.district_id=? ORDER BY p.training_year DESC, p.course_id", (district_id,)
        ).fetchall()]
        jobs = [dict(r) for r in c.execute(
            "SELECT job_title, sector, posting_date, salary_min, salary_max, skill_ids FROM job_postings "
            "WHERE district=? ORDER BY posting_date DESC LIMIT 12", (district["district"],)
        ).fetchall()]
        avg_rate = round(sum(float(p["placement_rate"] or 0) for p in placements) / len(placements), 1) if placements else None
        return {
            "district": district,
            "capacity_gap": int(district.get("estimated_training_demand") or 0) - int(district.get("annual_training_capacity") or 0),
            "training_centres": centres,
            "placements": placements,
            "job_postings": jobs,
            "summary": {"job_postings": len(jobs), "training_centres": len(centres), "placement_rate": avg_rate},
            "note": "All district, placement and job-posting records on this page are deterministic synthetic demo data (is_synthetic=1).",
        }
    finally:
        c.close()


def career_analyze(payload):
    known = [s.strip() for s in (payload.get("current_skills") or "").replace(";", ",").split(",") if s.strip()]
    have = set()
    c = get_db()
    try:
        all_skills = {r["id"]: dict(r) for r in c.execute("SELECT * FROM skills").fetchall()}
        for n in known:
            nid = normalize_skill_name(n)
            if nid and nid in all_skills:
                have.add(nid)
            else:
                for sid, s in all_skills.items():
                    if tokens(n) and tokens(n) <= (tokens(s.get("normalized_skill_name")) | tokens(s.get("skill_name"))):
                        have.add(sid)
        roles = [dict(r) for r in c.execute("SELECT * FROM job_roles").fetchall()]
        courses = [dict(r) for r in c.execute("SELECT * FROM courses").fetchall()]
    finally:
        c.close()
    from .analytics_service import role_skill_map

    role_req, _ = role_skill_map()
    sector_f = (payload.get("target_sector") or "").strip().lower()
    out_roles, unscored = [], []
    for r in roles:
        if sector_f and sector_f not in (r.get("sector") or "").lower():
            continue
        req = set(role_req.get(r["role_id"], set()))
        if not req:
            unscored.append(
                {
                    "role_id": r["role_id"],
                    "job_title": r["job_title"],
                    "reason": "No skill requirements mappable to the current 9-skill catalog",
                }
            )
            continue
        hit = req & have
        score = round(len(hit) / len(req) * 100, 1)
        missing = [
            {"skill_id": sid, "skill_name": all_skills.get(sid, {}).get("skill_name", sid), "demand_score": None}
            for sid in sorted(req - have)
        ]
        out_roles.append(
            {
                "role_id": r["role_id"],
                "job_title": r["job_title"],
                "sector": r.get("sector"),
                "match_score": score,
                "have": sorted(have & req),
                "missing_skills": missing,
                "required_skills": sorted(req),
            }
        )
    out_roles.sort(key=lambda x: -x["match_score"])
    top_roles = out_roles[:5]
    rec_courses = []
    if top_roles:
        need = {m["skill_id"] for rr in top_roles[:2] for m in rr["missing_skills"]}
        for co in courses:
            taught = set(split_ids(co.get("skills_taught")))
            cov = need & taught
            if cov:
                rec_courses.append({"course_id": co["id"], "course_name": co["course_name"], "covers": sorted(cov), "coverage": len(cov)})
        rec_courses.sort(key=lambda x: -x["coverage"])
    pathway = []
    if top_roles:
        for m in top_roles[0]["missing_skills"][:5]:
            via = ", ".join([cc["course_name"] for cc in rec_courses if m["skill_id"] in cc["covers"]][:2])
            pathway.append(f"Learn {m['skill_name']}" + (f" via {via}." if via else " — no course in the current catalog covers it yet."))
    trends = _rows("SELECT technology, evidence, trend_direction FROM trends")
    return {
        "recommended_roles": top_roles,
        "unscored_roles": unscored,
        "recommended_courses": rec_courses[:5],
        "learning_pathway": pathway,
        "trend_context": [
            {"technology": t["technology"], "direction": t.get("trend_direction"), "evidence": t.get("evidence")} for t in trends
        ],
        "evidence_note": "Matched against NCO 2015 roles and NSQF Qualification Pack curricula "
        "(Kaushora Real Evidence Dataset — real public sources). No employment guarantee.",
    }
