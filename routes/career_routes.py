from flask import Blueprint, jsonify, request
from services.analytics_service import role_skill_map
from services.db import get_db
from services.skill_gap_service import career_analyze

bp = Blueprint("career", __name__)


@bp.get("/api/careers/roles")
def roles():
    """Roles with their mappable skill requirements (evidence for guidance)."""
    c = get_db()
    try:
        roles = [dict(r) for r in c.execute("SELECT role_id, job_title, normalized_role, sector, qualification_level FROM job_roles").fetchall()]
    finally:
        c.close()
    req, _ = role_skill_map()
    return jsonify(
        [
            {"role_id": r["role_id"], "job_title": r["job_title"], "normalized_role": r.get("normalized_role"),
             "sector": r.get("sector"), "required_skills": sorted(req.get(r["role_id"], set())),
             "scorable": len(req.get(r["role_id"], set())) > 0}
            for r in roles
        ]
    )


@bp.post("/api/careers/analyze")
def analyze():
    data = request.get_json(force=True, silent=True) or {}
    if not (data.get("current_skills") or "").strip():
        return jsonify({"error": "Please list at least one current skill."}), 400
    try:
        return jsonify(career_analyze(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Backwards-compatible alias (older frontend path).
@bp.post("/api/career/analyze")
def analyze_alias():
    return analyze()
