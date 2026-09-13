"""Gap analysis on the Kaushora real public CSV dataset.

Coverage-alignment methodology (explicit mappings only, never fabricated):
  required(course) = skills required by the best-matching SAME-SECTOR
    occupation, where requirements come from the explicit occupation_skills
    table (NOS-coded, observed). Cross-sector pairings are never scored
    (an Electrician course is not judged against Inline Checker requirements).
    Best match = highest |course skills ∩ required| / |required|, tie-break
    larger overlap then occupation_id (deterministic).
  alignment_score  = (adequate + 0.5 * partial) / len(required) * 100
  Provided curriculum_alignment_ref pairs are shown verbatim as observed
  reference alongside the independent engine score.
  Courses with no recorded skill coverage, or with no same-sector occupation
  carrying explicit requirements, are Cannot Assess (never scored 0 as a
  false signal — except recorded-empty coverage vs explicit requirements).
Industry proficiency: observed employer surveys (deterministic majority,
ties to lower rank) else importance mapping High->Advanced,
Medium->Intermediate, else Intermediate. Curriculum proficiency: taught at
Intermediate baseline (no per-skill proficiency published in source).
Coverage_level from course_skills (all Full in source).
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


IMP_TO_PROF = {"High": "Advanced", "Medium": "Intermediate", "Low": "Basic"}


def course_alignment(course_id):
    c = get_db()
    try:
        co = c.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        if not co:
            return None
        co = dict(co)
        roles = {r["role_id"]: dict(r) for r in c.execute("SELECT * FROM job_roles").fetchall()}
        skills = {r["id"]: dict(r) for r in c.execute("SELECT * FROM skills").fetchall()}
        taught_rows = [dict(r) for r in c.execute("SELECT * FROM course_skills WHERE course_id=?", (course_id,)).fetchall()]
        occ_reqs = {}
        occ_imp = {}
        for m in c.execute("SELECT occupation_id, skill_id, importance FROM occupation_skills").fetchall():
            occ_reqs.setdefault(m["occupation_id"], set()).add(m["skill_id"])
            occ_imp[(m["occupation_id"], m["skill_id"])] = m["importance"]
        refs = [dict(r) for r in c.execute("SELECT * FROM curriculum_alignment_ref WHERE course_id=?", (course_id,)).fetchall()]
    finally:
        c.close()
    taught = set(split_ids(co.get("skills_taught")))
    taught |= {m["skill_id"] for m in taught_rows if m.get("skill_id")}
    coverage = {m["skill_id"]: (m.get("coverage_level") or "Full") for m in taught_rows if m.get("skill_id")}
    course_sector = co.get("sector_id")
    occ_sector_of = {oid: roles[oid].get("sector_id") for oid in occ_reqs if oid in roles}

    def _cannot_assess(reason):
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
            "reference_pairs": refs,
            "unmapped_role_phrases": [],
            "unmapped_requirement_phrases": [],
            "methodology": reason,
            "evidence": {
                "source": "NSDC occupation_skills + ITI course_skills (real public CSV)",
                "data_type": "real public sources (is_synthetic=0, data_source=REAL)",
            },
        }

    if not taught:
        return _cannot_assess("withheld: course has no recorded skill coverage in course_skills")
    # Same-sector explicit matches only — cross-sector pairings are fabricated
    candidates = [oid for oid in occ_reqs if occ_reqs[oid] and occ_sector_of.get(oid) == course_sector]
    if not candidates:
        return _cannot_assess(
            "withheld: no same-sector occupation carries explicit skill requirements "
            "(cross-sector matching would fabricate a mapping)"
        )
    scored = []
    for oid in candidates:
        req = occ_reqs[oid]
        inter = taught & req
        scored.append((len(inter) / len(req), len(inter), oid))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
    best_oid = scored[0][2]
    required = set(occ_reqs[best_oid])
    matched_roles = [best_oid]
    unmapped_phrases = []
    unmatched_targets = []
    emp = [e for e in _rows("SELECT skill_id, required_proficiency FROM employer_surveys") if (e.get("skill_id") or "") in skills]
    prof = {}
    for e in emp:
        prof.setdefault(e["skill_id"], []).append(e.get("required_proficiency") or "Intermediate")

    def ind_prof(sid):
        lst = prof.get(sid, [])
        if lst:
            # Deterministic majority vote; ties resolve to lower rank
            # (never overstate a gap; set order is hash-randomized).
            best, best_n = "Intermediate", -1
            for cand in sorted(set(lst), key=lambda p: PROF_RANK.get(p, 2)):
                n = lst.count(cand)
                if n > best_n:
                    best, best_n = cand, n
            return best
        imp = occ_imp.get((best_oid, sid))
        if imp:
            return IMP_TO_PROF.get(imp, "Intermediate")
        return "Intermediate"

    def cur_prof(sid):
        # Source publishes no per-skill proficiency: Full coverage taught at
        # Intermediate baseline (documented convention, not a measurement).
        if sid not in taught:
            return "Beginner"
        return "Intermediate" if coverage.get(sid, "Full") == "Full" else "Basic"

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
            "reference_pairs": refs,
            "unmapped_role_phrases": unmatched_targets,
            "unmapped_requirement_phrases": unmapped_phrases,
            "methodology": "coverage alignment = (adequate + 0.5*partial)/required vs best explicit occupation match; requirements from NOS-coded occupation_skills; curriculum proficiency baseline Intermediate (no per-skill proficiency published)",
            "evidence": {
                "source": "NSDC occupation_skills + ITI course_skills (real public CSV)",
                "data_type": "real public sources (is_synthetic=0, data_source=REAL)",
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
        "methodology": "explicit NOS-coded occupation_skills vs course_skills coverage; unmapped occupations excluded, never forced",
        "evidence": "NSDC occupation_skills + ITI course_skills (real public CSV, is_synthetic=0, data_source=REAL)",
    }


def district_detail(district_id):
    """Real district intelligence: master record + centres + capacity facts +
    state-level indicators (explicitly labeled, never downscaled) +
    recommendations + provided gap assessment."""
    c = get_db()
    try:
        d = c.execute("SELECT * FROM districts WHERE district_id=?", (district_id,)).fetchone()
        if not d:
            return None
        district = dict(d)
        centres = [dict(r) for r in c.execute(
            "SELECT * FROM training_centres WHERE district_id=? ORDER BY centre_name", (district_id,)
        ).fetchall()]
        caps = [dict(r) for r in c.execute(
            "SELECT * FROM district_capacity WHERE district_id=?", (district_id,)
        ).fetchall()]
        placements = [dict(r) for r in c.execute(
            "SELECT p.*, co.course_name FROM placements p LEFT JOIN courses co ON co.id=p.course_id "
            "WHERE p.district_id=? ORDER BY p.training_year DESC, p.course_id", (district_id,)
        ).fetchall()]
        jobs = [dict(r) for r in c.execute(
            "SELECT job_title, sector, posting_date, salary_min, salary_max, skill_ids FROM job_postings "
            "WHERE district=? ORDER BY posting_date DESC LIMIT 12", (district["district_name"],)
        ).fetchall()]
        recs = [dict(r) for r in c.execute(
            "SELECT r.*, s.skill_name FROM recommendations r LEFT JOIN skills s ON s.id=r.skill_id "
            "WHERE r.district_id=? ORDER BY r.priority, r.recommendation_id", (district_id,)
        ).fetchall()]
        gaps = [dict(r) for r in c.execute(
            "SELECT g.*, s.skill_name FROM district_skill_gaps g LEFT JOIN skills s ON s.id=g.skill_id "
            "WHERE g.district_id=?", (district_id,)
        ).fetchall()]
        state_inds = [dict(r) for r in c.execute(
            "SELECT indicator_name, indicator_value, unit, period, population_group FROM labour_indicators "
            "WHERE state_id=? ORDER BY indicator_id", (district.get("state_id"),)
        ).fetchall()]
        avg_rate = round(sum(float(p["placement_rate"] or 0) for p in placements) / len(placements), 1) if placements else None
        return {
            "district": district,
            "capacity": caps,
            "capacity_gap": None,  # demand unpublished in source; honestly unavailable
            "training_centres": centres,
            "placements": placements,
            "job_postings": jobs,
            "recommendations": recs,
            "skill_gaps": gaps,
            "state_indicators": state_inds,
            "summary": {"job_postings": len(jobs), "training_centres": len(centres),
                        "placement_rate": avg_rate, "capacity_facts": len(caps),
                        "recommendations": len(recs)},
            "note": "Source data: PMKVY/DVET centre and capacity records (REAL). "
                    "Indicators shown are state-level (Maharashtra/national) — no district-level PLFS is published. "
                    "Capacity gaps cannot be estimated where training demand is unpublished.",
            "data_source": "REAL",
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
                    "reason": "No skill requirements mapped to this occupation in the source (only 4 of 32 occupations carry explicit NOS links)",
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
        "evidence_note": "Matched against NSDC occupations with explicit NOS skill links and ITI course coverage "
        "(Kaushora real public CSV dataset — PLFS/NSDC/MSDE/DGT/DVET sources). No employment guarantee.",
    }
