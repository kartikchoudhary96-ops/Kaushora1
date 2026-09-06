from flask import Blueprint, jsonify
from services.curriculum_service import analyze_course
from services.db import get_db

bp = Blueprint("courses", __name__)


@bp.get("/api/courses")
def lst():
    c = get_db()
    try:
        courses = [dict(r) for r in c.execute("SELECT * FROM courses").fetchall()]
        places = {}
        for p in c.execute("SELECT course_id, AVG(placement_rate) r, AVG(median_salary) s FROM placements GROUP BY course_id").fetchall():
            places[p["course_id"]] = {"avg_placement": round(p["r"] or 0, 1), "avg_salary": round(p["s"] or 0)}
    finally:
        c.close()
    out = []
    for co in courses:
        a = analyze_course(co["id"])
        out.append(
            {
                **co,
                "alignment_score": a["alignment_score"] if a else None,
                "recommended_action": a["recommended_action"] if a else None,
                "placement": places.get(co["id"], {}),
            }
        )
    return jsonify(out)


@bp.get("/api/courses/<cid>")
def one(cid):
    c = get_db()
    try:
        r = c.execute("SELECT * FROM courses WHERE id=?", (cid,)).fetchone()
    finally:
        c.close()
    if not r:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(dict(r))


@bp.get("/api/courses/<cid>/alignment")
def align(cid):
    a = analyze_course(cid)
    if not a:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(a)
