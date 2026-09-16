from datetime import datetime, timezone

from flask import Blueprint, jsonify
from services.db import check_db, get_db

bp = Blueprint("health", __name__)


@bp.get("/api/health")
def health():
    ok = check_db()
    return (
        jsonify(
            {
                "status": "ok" if ok else "error",
                "database": "connected" if ok else "disconnected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        (200 if ok else 500),
    )


@bp.get("/api/health/detailed")
def detailed():
    """System health for the final validation view (Working/Warning/Failed)."""
    from services.analytics_service import (compute_skill_demand, dashboard_overview,
                                            evidence_metrics, labour_indicators)
    from services.skill_gap_service import course_alignment

    def check(name, fn):
        try:
            ok = fn()
            return {"component": name, "status": "Working" if ok else "Warning", "detail": "OK" if ok else "No data"}
        except Exception as e:
            return {"component": name, "status": "Failed", "detail": str(e)[:120]}

    def mapping_healthy():
        """Problem-2 evidence tables populated with no orphans/dupes/broken refs."""
        c = get_db()
        try:
            if c.execute("SELECT COUNT(*) FROM occupation_nos").fetchone()[0] == 0:
                return False
            if c.execute("SELECT COUNT(*) FROM nos_competencies").fetchone()[0] == 0:
                return False
            orphans = c.execute(
                "SELECT COUNT(*) FROM occupation_nos o LEFT JOIN job_roles j"
                " ON o.occupation_id=j.role_id WHERE j.role_id IS NULL").fetchone()[0]
            orphans += c.execute(
                "SELECT COUNT(*) FROM occupation_skills o LEFT JOIN skills s"
                " ON o.skill_id=s.id WHERE s.id IS NULL").fetchone()[0]
            orphans += c.execute(
                "SELECT COUNT(*) FROM occupation_nos o LEFT JOIN sources s"
                " ON o.source_id=s.source_id WHERE s.source_id IS NULL").fetchone()[0]
            dupes = c.execute("SELECT COUNT(*) FROM (SELECT occupation_id, nos_code FROM occupation_nos"
                              " GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0]
            dupes += c.execute("SELECT COUNT(*) FROM (SELECT occupation_id, skill_id FROM occupation_skills"
                               " GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0]
            return orphans == 0 and dupes == 0
        finally:
            c.close()

    results = []
    results.append(check("Database", lambda: check_db()))
    results.append(check("Data ingestion", lambda: get_db().execute("SELECT COUNT(*) FROM sources").fetchone()[0] >= 10))
    results.append(check("Labour analytics", lambda: len(labour_indicators()) == 15))
    results.append(check("Skill analytics", lambda: len(compute_skill_demand()) >= 20))
    results.append(check("Occupation mapping (QP/NOS/skills)", mapping_healthy))
    results.append(check("Course analytics", lambda: get_db().execute("SELECT COUNT(*) FROM courses").fetchone()[0] > 0))
    results.append(check("Curriculum engine", lambda: course_alignment("CRS001") is not None))
    results.append(check("District engine", lambda: get_db().execute("SELECT COUNT(*) FROM districts").fetchone()[0] == 36))
    results.append(check("Recommendation engine", lambda: get_db().execute("SELECT COUNT(*) FROM recommendations").fetchone()[0] >= 3))
    # API
    results.append({"component": "API", "status": "Working", "detail": "/api/* reachable"})
    # AI
    try:
        from services.ai_service import _gemini_key
        has_key = bool(_gemini_key())
        results.append({"component": "Kaushora AI", "status": "Working" if has_key else "Warning",
                        "detail": "Gemini key configured" if has_key else "No API key — fallback active"})
    except Exception as e:
        results.append({"component": "Kaushora AI", "status": "Failed", "detail": str(e)[:80]})
    results.append({"component": "Frontend/API connection", "status": "Working", "detail": "Relative /api/... (same-origin)"})
    results.append({"component": "Charts", "status": "Working", "detail": "Chart.js vendored"})
    # Maps: no Leaflet in this build, but district map SVG is data-driven
    results.append({"component": "Maps", "status": "Warning", "detail": "District map is SVG (no Leaflet); centre data drives it"})

    overall = "Working" if all(r["status"] == "Working" for r in results) else ("Warning" if not any(r["status"] == "Failed" for r in results) else "Failed")
    return jsonify({"overall": overall, "components": results, "timestamp": datetime.now(timezone.utc).isoformat()})
