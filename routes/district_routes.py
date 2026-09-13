from flask import Blueprint, jsonify
from services.db import get_db
from services.skill_gap_service import district_detail

bp = Blueprint("districts", __name__)


@bp.get("/api/districts")
def lst():
    """All 36 Maharashtra districts (master registry) with real centre counts
    and capacity facts where published. No estimated gaps — demand is
    unpublished in the source."""
    c = get_db()
    try:
        districts = [dict(r) for r in c.execute("SELECT * FROM districts ORDER BY district_name").fetchall()]
        centres = [dict(r) for r in c.execute(
            "SELECT district_id, COUNT(*) n FROM training_centres GROUP BY district_id").fetchall()]
        caps = {r["district_id"]: dict(r) for r in c.execute("SELECT * FROM district_capacity").fetchall()}
        recs = [dict(r) for r in c.execute(
            "SELECT district_id, COUNT(*) n FROM recommendations GROUP BY district_id").fetchall()]
    finally:
        c.close()
    n_centres = {r["district_id"]: r["n"] for r in centres}
    n_recs = {r["district_id"]: r["n"] for r in recs}
    out = []
    for d in districts:
        did = d["district_id"]
        cap = caps.get(did)
        out.append({
            "district_id": did,
            "district": d["district_name"],
            "district_code": d.get("district_code"),
            "state": d.get("state_name"),
            "training_centres": n_centres.get(did, 0),
            "capacity": cap,
            "capacity_gap": None,  # demand unpublished -> honestly unavailable
            "recommendations": n_recs.get(did, 0),
            "data_source": "REAL",
        })
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
