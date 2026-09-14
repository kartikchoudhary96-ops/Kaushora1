"""Data-status + dashboard-demand + evidence endpoints.

GET /api/data/status — real ingestion state from SQLite (record counts,
available entities, coverage, last ingestion run).
GET /api/dashboard/demand — honest demand summary (insufficient: source
skill_demand assessment is NULL for every signal).
GET /api/indicators — PLFS labour-market indicators (observed).
GET /api/evidence — citable evidence metrics (observed).
GET /api/recommendations — provided + engine recommendations (derived).
GET /api/jobs — job market intelligence from real LinkedIn postings.
"""
from flask import Blueprint, jsonify
from services.analytics_service import (META, compute_skill_demand, evidence_metrics,
                                        labour_indicators, recommendations_live,
                                        trend_signals, vacancy_evidence)
from services.db import get_db

bp = Blueprint("data_status", __name__)

TABLES = ["job_roles", "skills", "courses", "course_skills", "curriculum", "trends",
          "job_postings", "job_posting_skills", "job_posting_occupations",
          "placements", "district_capacity", "training_centres", "employer_surveys",
          "sources", "states", "districts", "sectors", "occupation_skills", "qualifications",
          "labour_indicators", "evidence_metrics", "skill_demand", "district_skill_gaps",
          "curriculum_alignment_ref", "recommendations"]


@bp.get("/api/data/status")
def data_status():
    c = get_db()
    try:
        counts = {}
        for t in TABLES:
            try:
                counts[t] = c.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
            except Exception:
                counts[t] = None
        try:
            meta = [dict(r) for r in c.execute("SELECT section, methodology_note, record_count, status FROM dataset_meta ORDER BY section").fetchall()]
        except Exception:
            meta = []
        try:
            run = c.execute("SELECT started_at, dataset_file, records_imported, records_rejected, status FROM ingestion_runs ORDER BY id DESC LIMIT 1").fetchone()
            last_run = dict(run) if run else None
        except Exception:
            last_run = None
        try:
            sectors = sorted({r["sector"] for r in c.execute("SELECT DISTINCT sector FROM skills WHERE sector<>''").fetchall()} |
                             {r["sector"] for r in c.execute("SELECT DISTINCT sector FROM courses WHERE sector<>''").fetchall()})
        except Exception:
            sectors = []
    finally:
        c.close()
    return jsonify(
        {
            "success": True,
            "data": {
                "dataset_loaded": (counts.get("skills") or 0) > 0,
                "last_ingestion": last_run,
                "record_counts": counts,
                "available_entities": [t for t in TABLES if (counts.get(t) or 0) > 0],
                "empty_entities": [t for t in TABLES if (counts.get(t) or 0) == 0],
                "sectors": sectors,
                "periods": ["2018-2020 (NSDC QPs)", "2024-2026 (PLFS/PMKVY/ITI)", "2020-2027 (WEF trends)"],
                "geographic_scope": "Maharashtra districts (36) + All-India labour indicators; no district-level PLFS published",
                "methodology": meta,
            },
            "meta": {"source": META["source"]},
            "error": None,
        }
    )


@bp.get("/api/dashboard/demand")
def dashboard_demand():
    skills = compute_skill_demand()
    trends = trend_signals()
    demand_with_score = [s for s in skills if s.get("demand_score") is not None]
    demand_insufficient = [s for s in skills if s["demand_status"] == "Insufficient data"]
    if demand_with_score and demand_insufficient:
        status = "mixed"
        reason = f"{len(demand_with_score)} skills have observed demand signals from WEF/NASSCOM; {len(demand_insufficient)} skills have insufficient source evidence for demand scoring."
    elif demand_with_score:
        status = "data_available"
        reason = f"All {len(demand_with_score)} skills have observed demand signals."
    else:
        status = "insufficient_data"
        reason = "The source skill_demand assessment carries NULL for every signal."
    return jsonify(
        {
            "success": True,
            "data": {
                "skills": [
                    {"id": s["id"], "skill_name": s["skill_name"], "demand_score": s["demand_score"],
                     "demand_status": s["demand_status"], "demand_count": s["demand_count"]}
                    for s in skills
                ],
                "trend_signals": trends,
                "status": status,
                "reason": reason,
                "methodology": "Observed demand scores from WEF/NASSCOM reports where available; insufficient for remaining skills.",
            },
            "meta": {"source": META["source"], "record_count": len(skills)},
            "error": None,
        }
    )


@bp.get("/api/indicators")
def indicators():
    """15 PLFS indicators (observed). Optional ?state_id=ST001 filter."""
    from flask import request
    state_id = request.args.get("state_id") or None
    rows = labour_indicators(state_id)
    return jsonify({
        "success": True,
        "data": rows,
        "meta": {"source": META["source"], "record_count": len(rows),
                 "note": "State/national level only; district_id NULL means not published at district level."},
        "error": None,
    })


@bp.get("/api/evidence")
def evidence():
    """10 citable evidence metrics (observed, with source references)."""
    rows = evidence_metrics()
    return jsonify({
        "success": True,
        "data": rows,
        "meta": {"source": META["source"], "record_count": len(rows)},
        "error": None,
    })


@bp.get("/api/recommendations")
def recommendations():
    """Provided recommendations (derived by compiler) + deterministic engine
    recommendations from real evidence. Engine rows carry engine:true."""
    rows = recommendations_live()
    return jsonify({
        "success": True,
        "data": rows,
        "meta": {"source": META["source"], "record_count": len(rows),
                 "note": "Provided rows: dataset compiler derivations. Engine rows: Kaushora derivations from live evidence (marked engine:true)."},
        "error": None,
    })


@bp.get("/api/jobs")
def job_market():
    """Job market intelligence from 2,500 real LinkedIn postings (Role Radar, Apache 2.0).
    Optional filters: ?state=X&sector=X&skill=X&limit=N"""
    from flask import request
    vac = vacancy_evidence()
    state_f = request.args.get("state") or None
    sector_f = request.args.get("sector") or None
    skill_f = request.args.get("skill") or None
    limit = min(int(request.args.get("limit", 50)), 200)
    c = get_db()
    try:
        q = "SELECT * FROM job_postings WHERE 1=1"
        params = []
        if state_f:
            q += " AND state LIKE ?"
            params.append(f"%{state_f}%")
        if sector_f:
            q += " AND sector LIKE ?"
            params.append(f"%{sector_f}%")
        if skill_f:
            q += " AND skill_ids LIKE ?"
            params.append(f"%{skill_f}%")
        q += f" ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)
        postings = [dict(r) for r in c.execute(q, params).fetchall()]
    finally:
        c.close()
    return jsonify({
        "success": True,
        "data": {
            "summary": {
                "total": vac.get("total", 0),
                "maharashtra": vac.get("maharashtra", 0),
                "source": vac.get("source", ""),
                "period": vac.get("period", ""),
            },
            "by_state": vac.get("by_state", []),
            "by_sector": vac.get("by_sector", []),
            "top_skills": vac.get("top_skills", []),
            "by_employment": vac.get("by_employment", []),
            "postings": postings,
        },
        "meta": {"source": "Role Radar (HuggingFace, Apache 2.0)", "record_count": len(postings)},
        "error": None,
    })
