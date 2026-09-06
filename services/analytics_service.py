"""Analytics computed live from SQLite — Real + Synthetic Dataset.

Demand methodology:
  overall_demand_score = normalized_job_demand + normalized_growth_signal
                         + normalized_employer_evidence
  - normalized_job_demand: from job_postings (synthetic 180 records now present)
  - normalized_growth_signal: trend_direction weight growing=1, stable=0.5,
    declining=0 (sector-level WEF signals)
  - normalized_employer_evidence: proportion of employer_surveys citing skill
    (synthetic 24 records now present)
Demand score is now calculable; where components missing they are omitted.
"""
from collections import Counter, defaultdict
from .db import get_db
from .data_service import split_ids, skill_ids_for_phrase

TREND_WEIGHT = {"growing": 1.0, "stable": 0.5, "declining": 0.0}

META = {
    "source": "Kaushora Dataset: Real Evidence (NCO 2015, SSC QPs, WEF) + Synthetic demo (180 jobs, 4 districts, 24 placements, 24 employer surveys, is_synthetic=1)",
    "data_file": "data/raw/kaushora_real_evidence_dataset.md + synthetic seed (scripts/seed_synthetic.py)",
    "data_type": "real (is_synthetic=0) + synthetic demo (is_synthetic=1, data_type='synthetic') for feature completeness",
    "limitations": [
        "Synthetic data added for demo: job_postings (180), district_capacity (4), placements (24), employer_surveys (24) — all marked is_synthetic=1.",
        "Real dataset had no district/capacity/placement/employer records; synthetic fills the gap so charts and gaps are demonstrable.",
        "WEF trends remain sector-level qualitative evidence.",
    ],
}


def _rows(q, args=()):
    c = get_db()
    try:
        return [dict(r) for r in c.execute(q, args).fetchall()]
    finally:
        c.close()


def skill_maps():
    skills = {s["id"]: s for s in _rows("SELECT * FROM skills")}
    return skills


def distinct_sectors():
    vals = set()
    for t, col in [("job_roles", "sector"), ("skills", "sector"), ("courses", "sector")]:
        try:
            for r in _rows(f"SELECT DISTINCT {col} v FROM {t} WHERE {col} IS NOT NULL AND {col}<>''"):
                vals.add(r["v"])
        except Exception:
            pass
    return sorted(vals)


def job_skill_counts():
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


def role_skill_map():
    """Map each role to skill ids via related_skills free-text matching.

    Returns (role_req, unmapped) where unmapped lists phrases that could
    not be mapped to any catalog skill — reported, never forced.
    """
    skills = skill_maps()
    roles = _rows("SELECT * FROM job_roles")
    req, unmapped = {}, {}
    for r in roles:
        sids = set()
        misses = []
        for phrase in split_ids(r.get("related_skills")):
            hits = skill_ids_for_phrase(phrase, skills)
            if hits:
                sids.update(hits)
            else:
                misses.append(phrase)
        req[r["role_id"]] = sids
        if misses:
            unmapped[r["role_id"]] = misses
    return req, unmapped


def compute_skill_demand():
    skills = skill_maps()
    jobs, cnt, by_district, by_sector = job_skill_counts()
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

    # Normalization for demand score
    max_job = max(cnt.values()) if cnt else 0
    max_emp = max(emp_tot.values()) if emp_tot else 0

    out = []
    for sid, s in skills.items():
        job_c = cnt.get(sid, 0)
        emp_raw = emp_tot.get(sid, 0)
        place_n = float(skill_place.get(sid, 0))
        # Demand score: weighted normalized job + employer (0-100)
        if max_job or max_emp:
            nj = (job_c / max_job) if max_job else 0
            ne = (emp_raw / max_emp) if max_emp else 0
            # Weighted 60% job frequency, 40% employer demand
            score = round((nj * 0.6 + ne * 0.4) * 100, 1)
            # If score is 0 but has placement relevance, give minimal score
            if score == 0 and place_n > 0:
                score = round(min(place_n / 100 * 20, 15), 1)
        else:
            score = None
        status = demand_status(score, None, job_c, emp_raw, place_n)

        taught_by = sorted([cid for cid, ss in cmap.items() if sid in ss])

        # Top sectors/districts for this skill
        top_sectors = []
        for sec, counter in by_sector.items():
            if sid in counter:
                top_sectors.append({"sector": sec, "count": counter[sid]})
        top_sectors.sort(key=lambda x: -x["count"])
        top_sectors = top_sectors[:3]

        top_districts = []
        for dist, counter in by_district.items():
            if sid in counter:
                top_districts.append({"district": dist, "count": counter[sid]})
        top_districts.sort(key=lambda x: -x["count"])
        top_districts = top_districts[:3]

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
                "demand_score": score,
                "demand_status": status,
                "top_sectors": top_sectors,
                "top_districts": top_districts,
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
                "description": s.get("description"),
            }
        )
    # Sort by demand_score descending, then name
    out.sort(key=lambda x: (-(x["demand_score"] or -1), x["skill_name"]))
    return out


def demand_status(score, growth, count, employer=0, placement=0):
    if (count or 0) == 0 and (employer or 0) == 0 and (placement or 0) == 0:
        return "Insufficient Evidence"
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


def dashboard_overview():
    skills = compute_skill_demand()
    jobs = _rows("SELECT COUNT(*) c FROM job_postings")[0]["c"]
    courses = _rows("SELECT * FROM courses")
    placements = _rows("SELECT * FROM placements")
    roles = _rows("SELECT * FROM job_roles")
    districts = _rows("SELECT * FROM district_capacity")
    centres = _rows("SELECT * FROM training_centres")
    from .skill_gap_service import course_alignment

    aligns = []
    for co in courses:
        a = course_alignment(co["id"])
        if a and a["alignment_score"] is not None:
            aligns.append(a["alignment_score"])
    avg_align = round(sum(aligns) / len(aligns), 1) if aligns else None
    need_review = sum(1 for a in aligns if a < 65)

    # Placement stats
    avg_placement = round(sum(float(p["placement_rate"] or 0) for p in placements) / len(placements), 1) if placements else None
    # Capacity gap
    total_demand = sum(int(d.get("estimated_training_demand") or 0) for d in districts)
    total_capacity = sum(int(d.get("annual_training_capacity") or 0) for d in districts)
    capacity_gap = total_demand - total_capacity if districts else None
    # High demand skills
    high_demand = sum(1 for s in skills if s["demand_status"] in ("Critical Demand", "High Demand"))
    # Sector demand aggregation
    _, cnt, _, by_sector = job_skill_counts()
    sector_demand = []
    for sector, counter in by_sector.items():
        total = sum(counter.values())
        sector_demand.append({"sector": sector, "demand": total})
    sector_demand.sort(key=lambda x: -x["demand"])
    # District demand — use training demand vs capacity from district_capacity (synthetic), not raw job count
    district_demand = []
    for d in districts:
        dem = int(d.get("estimated_training_demand") or 0)
        cap = int(d.get("annual_training_capacity") or 0)
        # Also include job postings count for context
        postings = _rows("SELECT COUNT(*) c FROM job_postings WHERE district=?", (d["district"],))[0]["c"]
        district_demand.append({"district": d["district"], "district_id": d["district_id"], "demand": dem, "capacity": cap, "gap": dem - cap, "postings": postings, "priority": d.get("priority_level")})
    district_demand.sort(key=lambda x: -x["gap"])

    trends = trend_signals()
    growing = [t for t in trends if (t.get("trend_direction") or "").lower() == "growing"]
    actions = []
    for co in courses:
        a = course_alignment(co["id"])
        if not a:
            continue
        if a["alignment_score"] is None:
            actions.append(
                {
                    "type": "course",
                    "priority": "Medium",
                    "title": f"{a['course']['course_name']} — cannot assess alignment",
                    "reason": "Target roles are not in the current role catalog.",
                }
            )
        elif a["alignment_score"] < 70:
            actions.append(
                {
                    "type": "course",
                    "priority": "High" if a["alignment_score"] < 60 else "Medium",
                    "title": f"{a['course']['course_name']} — coverage {a['alignment_score']}%",
                    "reason": a["recommended_action"],
                }
            )
    for t in growing:
        actions.append(
            {"type": "trend", "priority": "Medium", "title": f"Trend: {t['technology']}", "reason": (t.get("evidence") or "")[:160]}
        )
    # District gaps as actions
    for dd in district_demand:
        if dd["gap"] and dd["gap"] > 20:
            actions.append(
                {"type": "district", "priority": "High" if dd["gap"] > 50 else "Medium",
                 "title": f"{dd['district']} — capacity gap {dd['gap']}",
                 "reason": f"Demand {dd['demand']} vs capacity {dd['capacity']}."}
            )
    if not jobs:
        actions.append(
            {
                "type": "data",
                "priority": "Medium",
                "title": "No demand signals in the current dataset",
                "reason": "JOB_DEMAND and EMPLOYER_REQUIREMENTS are empty — demand scores cannot be calculated.",
            }
        )
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
        },
        "top_skills": skills[:8],
        "sector_demand": sector_demand,
        "district_demand": district_demand,
        "actions": actions[:8],
        "meta": {
            **META,
            "insufficient": [] if jobs else ["sector_demand", "district_demand", "monthly_postings", "capacity_gap", "placement_rate"],
        },
    }


def trends_data():
    trends = trend_signals()
    # Monthly postings time series from synthetic job_postings
    try:
        rows = _rows("SELECT substr(posting_date,1,7) as ym, COUNT(*) c FROM job_postings WHERE posting_date IS NOT NULL GROUP BY ym ORDER BY ym")
        monthly = [{"month": r["ym"], "count": r["c"]} for r in rows]
    except Exception:
        monthly = []
    growing = [t for t in trends if (t.get("trend_direction") or "").lower() == "growing"]
    # Also compute growing skills by demand_score
    skills = compute_skill_demand()
    growing_skills = [s for s in skills if s["demand_status"] in ("Critical Demand", "High Demand")]
    declining_skills = [s for s in skills if s["demand_status"] == "Declining"]
    return {
        "monthly_postings": monthly,
        "growing_skills": growing_skills[:5],
        "declining_skills": declining_skills[:5],
        "trend_signals": trends,
        "note": "Monthly postings derived from synthetic job_postings (180 records over last 10 months). WEF signals remain qualitative sector-level evidence." if monthly else "No job-posting time series in the current dataset. Growth signals below are qualitative sector-level evidence (WEF), not skill-level measurements.",
    }
