from flask import Blueprint, jsonify
from services.db import get_db
from services.skill_gap_service import district_detail

bp = Blueprint("districts", __name__)


@bp.get("/api/districts")
def lst():
    c = get_db()
    try:
        rows = [dict(r) for r in c.execute("SELECT * FROM district_capacity").fetchall()]
    finally:
        c.close()
    out = []
    for d in rows:
        gap = (d["estimated_training_demand"] or 0) - (d["annual_training_capacity"] or 0)
        out.append({**d, "capacity_gap": gap})
    return jsonify(out)


@bp.get("/api/districts/<did>")
def one(did):
    d = district_detail(did)
    if not d:
        return jsonify({"error": "District not found"}), 404
    return jsonify(d)


@bp.get("/api/districts/<did>/skills")
def district_skills(did):
    d = district_detail(did)
    if not d:
        return jsonify({"error": "District not found"}), 404
    # Reuse the data-backed detail until a dedicated district-skill table is ingested.
    return jsonify(d)
