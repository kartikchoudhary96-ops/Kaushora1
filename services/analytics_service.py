"""Analytics computed live from SQLite — Kaushora real public CSV dataset.

Sources: PLFS (MoSPI), NSDC QPs, PMKVY Maharashtra centres (MSDE), NCS
portal stats, DVET Maharashtra ITIs, DGT CTS, WEF trends. All rows
is_synthetic=0, data_source='REAL'.

Demand methodology (honest):
  The dataset's skill_demand assessment row carries NULL for every signal
  (employment/occupation/training-gap/growth) with calculation_method
  'Not calculated - insufficient signals'. Kaushora therefore reports
  demand_score=None and demand_status='Insufficient data' for every skill.
  Macro labour signals (LFPR/WPR/UR, NCS vacancies) are national/platform
  aggregates — they are surfaced as evidence, never converted into
  per-skill demand scores.

Observed vs derived:
  OBSERVED  = rows present in the CSV source (catalog, mappings, centres,
              capacity facts, indicators, evidence, reference rows).
  DERIVED   = Kaushora calculations (coverage alignment, versatility ranks,
              engine recommendations, aggregates). Marked as such.
"""
from collections import Counter, defaultdict
from .db import get_db
from .data_service import split_ids, skill_ids_for_phrase

META = {
    "source": "Kaushora real public dataset: PLFS (MoSPI), NSDC Qualification Packs, PMKVY Maharashtra (MSDE), NCS portal, DVET Maharashtra, DGT CTS, WEF trends",
    "data_file": "data/raw/csv/*.csv (18 files)",
    "data_type": "official government statistics + public QP/course/centre records (is_synthetic=0, data_source=REAL)",
    "limitations": [
        "No per-skill demand signals in source (skill_demand row is NULL) — demand scores honestly unavailable.",
        "Labour indicators are state/national level; no district-level PLFS published — never downscaled.",
        "Capacity facts are sparse (3 districts); seats/enrolments mostly unpublished (NULL).",
        "Explicit occupation-skill links cover 4 of 32 occupations; the rest are honestly unscored.",
    ],
}


def _rows(q, args=()):
    c = get_db()
    try:
        return [dict(r) for r in c.execute(q, args).fetchall()]
    finally:
        c.close()


def skill_maps():
    return {s["id"]: s for s in _rows("SELECT * FROM skills")}


def distinct_sectors():
    try:
        return [r["sector_name"] for r in _rows("SELECT sector_name FROM sectors ORDER BY sector_name")]
    except Exception:
        return []


def _explicit_role_reqs():
    """Explicit occupation -> skill mapping from occupation_skills (observed)."""
    req = defaultdict(set)
    det = {}
    for r in _rows("SELECT occupation_id, skill_id, importance, competency_type, nos_code FROM occupation_skills"):
        req[r["occupation_id"]].add(r["skill_id"])
        det[(r["occupation_id"], r["skill_id"])] = r
    return req, det


def role_skill_map():
    """Required skills per occupation: explicit NOS mapping first, legacy
    related_skills text-match only as fallback. Returns (role_req, unmapped)
    where unmapped lists occupations/phrases with no mapping — reported,
    never forced."""
    skills = skill_maps()
    roles = _rows("SELECT * FROM job_roles")
    explicit, _ = _explicit_role_reqs()
    req, unmapped = {}, {}
    for r in roles:
        rid = r["role_id"]
        if rid in explicit and explicit[rid]:
            req[rid] = set(explicit[rid])
            continue
        # fallback: legacy free-text related_skills (NULL for CSV occupations)
        sids, misses = set(), []
        for phrase in split_ids(r.get("related_skills")):
            hits = skill_ids_for_phrase(phrase, skills)
            if hits:
                sids.update(hits)
            else:
                misses.append(phrase)
        req[rid] = sids
        if misses:
            unmapped[rid] = misses
        elif not sids:
            unmapped[rid] = ["no mapped skill requirements in source"]
    return req, unmapped


def job_skill_counts():
    # No job-posting table in the CSV source; job_postings stays empty.
    jobs = _rows("SELECT * FROM job_postings")
    cnt = Counter()
    by_district = defaultdict(Counter)
    by_sector = defaultdict(Counter)
    for j in jobs:
        for sid in split_ids(j.get("skill_ids")):
            cnt[sid] += 1
            by_district[(j.get("district") or "Unknown")][sid] += 1
            by_sector[(j.get("sector") or "UNK")][sid] += 1
    return jobs, cnt, by_district, by_sector


def employer_stats():
    # Only observed user submissions; source dataset carries none.
    skills = skill_maps()
    rows = [r for r in _rows("SELECT * FROM employer_surveys") if (r.get("skill_id") or "") in skills]
    tot = defaultdict(int)
    imp = defaultdict(list)
    for r in rows:
        tot[r["skill_id"]] += int(r.get("hiring_demand") or 0)
        try:
            imp[r["skill_id"]].append(int(r.get("importance") or 3))
        except Exception:
            pass
    return tot, imp


def placement_stats():
    rows = _rows("SELECT * FROM placements")
    by_course = defaultdict(list)
    for r in rows:
        by_course[r["course_id"]].append(r)
    avg = {}
    for cid, lst in by_course.items():
        rates = [float(x["placement_rate"] or 0) for x in lst]
        avg[cid] = sum(rates) / len(rates) if rates else 0
    return rows, avg


def course_skill_map():
    courses = _rows("SELECT * FROM courses")
    cmap = {}
    for co in courses:
        taught = set(split_ids(co.get("skills_taught")))
        for m in _rows("SELECT skill_id FROM course_skills WHERE course_id=?", (co["id"],)):
            if m.get("skill_id"):
                taught.add(m["skill_id"])
        cmap[co["id"]] = taught
    return courses, cmap


def compute_skill_demand():
    """Per-skill demand: honestly insufficient (source assessment is NULL).
    Returns catalog rows with related roles/courses from explicit mappings."""
    skills = skill_maps()
    _, cnt, _, _ = job_skill_counts()
    emp_tot, _ = employer_stats()
    _, avg_place = placement_stats()
    courses, cmap = course_skill_map()
    skill_place = {}
    for sid in skills:
        rel = [avg_place[cid] for cid, ss in cmap.items() if sid in ss and cid in avg_place]
        skill_place[sid] = (sum(rel) / len(rel)) if rel else 0
    role_req, _ = role_skill_map()
    skill_roles = defaultdict(list)
    for rid, sids in role_req.items():
        for sid in sids:
            skill_roles[sid].append(rid)
    # Source demand assessment (single honest row, all signals NULL)
    assessments = {r["skill_id"]: r for r in _rows("SELECT * FROM skill_demand")}
    out = []
    for sid, s in skills.items():
        job_c = cnt.get(sid, 0)
        emp_raw = emp_tot.get(sid, 0)
        place_n = float(skill_place.get(sid, 0))
        status = demand_status(None, None, job_c, emp_raw, place_n)
        taught_by = sorted([cid for cid, ss in cmap.items() if sid in ss])
        out.append(
            {
                "id": sid,
                "skill_name": s["skill_name"],
                "normalized_skill_name": s.get("normalized_skill_name"),
                "category": s.get("skill_category"),
                "sector": s.get("sector"),
                "technology_status": s.get("technology_status"),
                "growth_rate": None,
                "demand_count": job_c,
                "employer_demand": emp_raw,
                "placement_relevance": round(place_n, 1),
                "demand_score": None,
                "demand_status": status,
                "demand_assessment": assessments.get(sid),
                "top_sectors": [],
                "top_districts": [],
                "taught_by_courses": taught_by,
                "related_roles": sorted(skill_roles.get(sid, [])),
                "source": s.get("source"),
                "source_url": s.get("source_url"),
                "source_title": s.get("source_title"),
                "publisher": s.get("publisher"),
                "publication_date": s.get("publication_date"),
                "data_period": s.get("data_period"),
                "data_type": s.get("data_type"),
                "is_synthetic": s.get("is_synthetic"),
                "data_source": s.get("data_source") or "REAL",
                "description": s.get("description"),
            }
        )
    out.sort(key=lambda x: x["skill_name"])
    return out


def demand_status(score, growth, count, employer=0, placement=0):
    # Source skill_demand assessment is NULL for every signal: no score can
    # be calculated. Thresholds below apply only if real signals arrive.
    if (count or 0) == 0 and (employer or 0) == 0 and (placement or 0) == 0:
        return "Insufficient data"
    if growth is not None and growth < 0 and (score or 0) < 45:
        return "Declining"
    if (score or 0) >= 75:
        return "Critical Demand"
    if (score or 0) >= 55:
        return "High Demand"
    if (score or 0) >= 35:
        return "Moderate"
    if (score or 0) >= 15:
        return "Low"
    return "Low"


def trend_signals():
    return _rows("SELECT * FROM trends ORDER BY trend_id")


def dataset_limitations():
    try:
        return [
            dict(r)
            for r in _rows("SELECT section, methodology_note, record_count, status FROM dataset_meta ORDER BY section")
        ]
    except Exception:
        return []


def labour_indicators(state_id=None):
    q = "SELECT li.*, s.source_name, s.organization FROM labour_indicators li LEFT JOIN sources s ON s.source_id=li.source_id"
    if state_id:
        q += " WHERE li.state_id=?"
        return _rows(q + " ORDER BY li.indicator_id", (state_id,))
    return _rows(q + " ORDER BY li.indicator_id")


def evidence_metrics():
    return _rows(
        "SELECT e.*, s.source_name, s.organization FROM evidence_metrics e "
        "LEFT JOIN sources s ON s.source_id=e.source_id ORDER BY e.evidence_id"
    )


def recommendations_live():
    """Provided recommendations (derived by compiler) + deterministic engine
    recommendations from real evidence. Engine rows are marked engine:true."""
    provided = _rows(
        "SELECT r.*, d.district_name, s.skill_name, o.job_title FROM recommendations r "
        "LEFT JOIN districts d ON d.district_id=r.district_id "
        "LEFT JOIN skills s ON s.id=r.skill_id "
        "LEFT JOIN job_roles o ON o.role_id=r.occupation_id "
        "ORDER BY CASE r.priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, r.recommendation_id"
    )
    out = []
    for r in provided:
        r["engine"] = False
        r["data_source"] = "REAL"
        out.append(r)
    # Engine: districts with zero recorded centres -> evidence-collection rec
    centres = Counter(r["district_id"] for r in _rows("SELECT district_id FROM training_centres"))
    for d in _rows("SELECT district_id, district_name FROM districts ORDER BY district_id"):
        if centres.get(d["district_id"], 0) == 0 and d["district_id"] != "DT019":
            pass  # too noisy for 34 districts; covered by the aggregate note below
    # Engine: capacity rows with NULL seats -> data-collection rec (real gap)
    for cap in _rows(
        "SELECT dc.*, d.district_name FROM district_capacity dc "
        "LEFT JOIN districts d ON d.district_id=dc.district_id"
    ):
        if cap.get("training_seats") is None:
            out.append({
                "recommendation_id": f"ENG-CAP-{cap['district_id']}",
                "district_id": cap["district_id"],
                "district_name": cap.get("district_name"),
                "skill_id": None, "skill_name": None, "occupation_id": None, "job_title": None,
                "recommendation_type": "Collect data",
                "recommendation_text": f"Publish training-seat and enrolment figures for {cap.get('district_name')} ({cap.get('scheme')})",
                "priority": "Medium",
                "reason": "Centre count is recorded but seats/enrolments are unpublished, so capacity gaps cannot be estimated.",
                "supporting_evidence": None, "source_ids": cap.get("source_id"),
                "is_derived": 1, "data_source": "REAL", "engine": True,
            })
    # Engine: occupations without mapped requirements -> mapping rec (sampled)
    req, _ = role_skill_map()
    unmapped = [rid for rid, sids in req.items() if not sids][:3]
    if unmapped:
        names = {r["role_id"]: r["job_title"] for r in _rows("SELECT role_id, job_title FROM job_roles")}
        out.append({
            "recommendation_id": "ENG-MAP-001",
            "district_id": None, "district_name": None, "skill_id": None, "skill_name": None,
            "occupation_id": None, "job_title": None,
            "recommendation_type": "Map requirements",
            "recommendation_text": "Publish NOS-coded skill requirements for occupations lacking explicit mappings (e.g. %s)" % (
                ", ".join(f"{rid} {names.get(rid, '')}" for rid in unmapped)),
            "priority": "Low",
            "reason": "Only 4 of 32 occupations carry explicit occupation-skill links, limiting gap analysis.",
            "supporting_evidence": None, "source_ids": "SRC003,SRC004",
            "is_derived": 1, "data_source": "REAL", "engine": True,
        })
    return out


def district_summary():
    """Per-district rollup from real centres + capacity + recommendations."""
    districts = _rows("SELECT * FROM districts ORDER BY district_name")
    centres = _rows("SELECT * FROM training_centres")
    caps = {r["district_id"]: r for r in _rows("SELECT * FROM district_capacity")}
    recs = _rows("SELECT * FROM recommendations")
    by_dist = defaultdict(list)
    for r in recs:
        if r.get("district_id"):
            by_dist[r["district_id"]].append(r["recommendation_id"])
    out = []
    for d in districts:
        did = d["district_id"]
        dc = [x for x in centres if x["district_id"] == did]
        cap = caps.get(did)
        out.append({
            "district_id": did,
            "district": d["district_name"],
            "district_code": d.get("district_code"),
            "state": d.get("state_name"),
            "training_centres": len(dc),
            "centre_list": [{"centre_id": x["centre_id"], "centre_name": x["centre_name"],
                             "centre_type": x.get("centre_type"), "provider": x.get("provider"),
                             "scheme": x.get("scheme")} for x in dc],
            "capacity": cap,
            "capacity_gap": None,  # demand unpublished -> honestly unavailable
            "recommendations": by_dist.get(did, []),
            "data_source": "REAL",
        })
    return out


def dashboard_overview():
    skills = compute_skill_demand()
    jobs = _rows("SELECT COUNT(*) c FROM job_postings")[0]["c"]
    courses = _rows("SELECT * FROM courses")
    placements = _rows("SELECT * FROM placements")
    roles = _rows("SELECT * FROM job_roles")
    districts = _rows("SELECT * FROM districts")
    centres = _rows("SELECT * FROM training_centres")
    from .skill_gap_service import course_alignment

    aligns = []
    for co in courses:
        a = course_alignment(co["id"])
        if a and a["alignment_score"] is not None:
            aligns.append(a["alignment_score"])
    avg_align = round(sum(aligns) / len(aligns), 1) if aligns else None
    need_review = sum(1 for a in aligns if a < 65)

    avg_placement = None  # placements table empty in source
    capacity_gap = None  # demand unpublished in source
    high_demand = sum(1 for s in skills if s["demand_status"] in ("Critical Demand", "High Demand"))

    # Sector composition from real occupations + courses (observed counts)
    occ_sec = Counter(r["sector"] for r in roles if r.get("sector"))
    course_sec = Counter(co["sector"] for co in courses if co.get("sector"))
    sector_demand = [
        {"sector": s, "occupations": occ_sec.get(s, 0), "courses": course_sec.get(s, 0),
         "demand": occ_sec.get(s, 0) + course_sec.get(s, 0)}
        for s in sorted(set(list(occ_sec) + list(course_sec)))
    ]
    sector_demand.sort(key=lambda x: -x["demand"])

    # District composition from real centre counts
    centre_dist = Counter(r["district_id"] for r in centres)
    dnames = {r["district_id"]: r["district_name"] for r in districts}
    district_demand = [
        {"district": dnames.get(did, did), "district_id": did, "demand": None,
         "capacity": None, "gap": None, "training_centres": n, "postings": 0}
        for did, n in sorted(centre_dist.items(), key=lambda x: -x[1])
    ]

    trends = trend_signals()
    growing = [t for t in trends if (t.get("trend_direction") or "").lower() == "growing"]
    actions = []
    for rec in recommendations_live()[:6]:
        actions.append({
            "type": "recommendation",
            "priority": rec.get("priority") or "Medium",
            "title": f"{rec.get('recommendation_type')}: {rec.get('recommendation_text')}"[:140],
            "reason": rec.get("reason") or "",
        })
    for co in courses:
        a = course_alignment(co["id"])
        if not a:
            continue
        if a["alignment_score"] is None:
            actions.append({
                "type": "course", "priority": "Medium",
                "title": f"{a['course']['course_name']} — cannot assess alignment",
                "reason": a.get("methodology") or "No mapped occupation requirements.",
            })
        elif a["alignment_score"] < 100:
            actions.append({
                "type": "course", "priority": "Medium",
                "title": f"{a['course']['course_name']} — coverage {a['alignment_score']}%",
                "reason": a["recommended_action"],
            })
    for t in growing:
        actions.append(
            {"type": "trend", "priority": "Medium", "title": f"Trend: {t['technology']}",
             "reason": (t.get("evidence") or "")[:160]}
        )
    if not jobs:
        ncs = next((e for e in _rows(
            "SELECT metric_value, unit FROM evidence_metrics WHERE evidence_id='EV008'") or []), None)
        ncs_txt = f"{ncs['metric_value']} {ncs['unit']}" if ncs else "published aggregates"
        actions.append({
            "type": "data", "priority": "Low",
            "title": "No job-posting records in the source dataset",
            "reason": f"The CSV source carries no vacancy microdata; NCS aggregate vacancies ({ncs_txt}) shown as evidence.",
        })
    return {
        "totals": {
            "jobs_analysed": jobs,
            "unique_skills": len(skills),
            "high_demand_skills": high_demand,
            "avg_alignment": avg_align,
            "capacity_gap": capacity_gap,
            "courses_needing_review": need_review,
            "avg_placement_rate": avg_placement,
            "districts": len(districts),
            "courses": len(courses),
            "centres": len(centres),
            "roles": len(roles),
            "trends": len(trends),
            "indicators": len(_rows("SELECT indicator_id FROM labour_indicators")),
            "evidence": len(_rows("SELECT evidence_id FROM evidence_metrics")),
        },
        "top_skills": skills[:8],
        "sector_demand": sector_demand,
        "district_demand": district_demand,
        "actions": actions[:8],
        "meta": {
            **META,
            "insufficient": ["demand_score", "monthly_postings", "capacity_gap", "placement_rate", "district_indicators"],
        },
    }


def trends_data():
    trends = trend_signals()
    return {
        "monthly_postings": [],
        "growing_skills": [],
        "declining_skills": [],
        "trend_signals": trends,
        "note": "No vacancy time series in the source dataset. WEF signals are qualitative sector-level evidence, not skill-level measurements.",
    }
