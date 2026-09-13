"""Data-status + dashboard-demand + evidence endpoints.

GET /api/data/status — real ingestion state from SQLite (record counts,
available entities, coverage, last ingestion run).
GET /api/dashboard/demand — honest demand summary (insufficient: source
skill_demand assessment is NULL for every signal).
GET /api/indicators — PLFS labour-market indicators (observed).
GET /api/evidence — citable evidence metrics (observed).
GET /api/recommendations — provided + engine recommendations (derived).
"""
from flask import Blueprint, jsonify
from services.analytics_service import (META, compute_skill_demand, evidence_metrics,
                                        labour_indicators, recommendations_live, trend_signals)
from services.db import get_db

bp = Blueprint("data_status", __name__)

TABLES = ["job_roles", "skills", "courses", "course_skills", "curriculum", "trends",
          "job_postings", "placements", "district_capacity", "training_centres", "employer_surveys",
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
                "status": "insufficient_data",
                "reason": "The source skill_demand assessment carries NULL for every signal (employment, occupation, training-gap, growth) with method 'Not calculated - insufficient signals'. National aggregates (LFPR/WPR/UR, NCS vacancies) are shown as evidence, never converted into per-skill scores.",
                "methodology": "No per-skill demand score is calculated: insufficient source signals.Demand would combine normalized vacancy, growth and employer evidence if published.",
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
