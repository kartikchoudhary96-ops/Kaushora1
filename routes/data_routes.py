"""Data-status + dashboard-demand endpoints.

GET /api/data/status — real ingestion state from SQLite (record counts,
available entities, coverage, last ingestion run).
GET /api/dashboard/demand — honest demand summary (unavailable where the
dataset has no demand signals).
"""
from flask import Blueprint, jsonify
from services.analytics_service import META, compute_skill_demand, trend_signals
from services.db import get_db

bp = Blueprint("data_status", __name__)

TABLES = ["job_roles", "skills", "courses", "course_skills", "curriculum", "trends",
          "job_postings", "placements", "district_capacity", "training_centres", "employer_surveys"]


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
                "dataset_loaded": counts.get("skills", 0) > 0,
                "last_ingestion": last_run,
                "record_counts": counts,
                "available_entities": [t for t in TABLES if (counts.get(t) or 0) > 0],
                "empty_entities": [t for t in TABLES if (counts.get(t) or 0) == 0],
                "sectors": sectors,
                "periods": ["2015 (NCO)", "2018-2019 (QPs)", "2020-2027 (WEF trends)"],
                "geographic_scope": "National (India) real catalog; Maharashtra synthetic demo coverage for districts, jobs and placements",
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
                "status": "available" if any(s["demand_score"] is not None for s in skills) else "insufficient_data",
                "reason": "Demand scores combine job-posting frequency and employer hiring demand. Current signals are synthetic demo records and are explicitly labelled as such; WEF trends remain qualitative sector-level evidence.",
                "methodology": "overall_demand_score = 60% normalized job-posting frequency + 40% normalized employer hiring demand; unavailable components are omitted.",
            },
            "meta": {"source": META["source"], "record_count": len(skills)},
            "error": None,
        }
    )
