from flask import Blueprint, jsonify, request
from services.analytics_service import compute_skill_demand, dashboard_overview, trends_data
from services.db import get_db
from services.skill_gap_service import skill_gap_for_skill

bp = Blueprint("dash_skill", __name__)


@bp.get("/api/dashboard/overview")
def overview():
    try:
        return jsonify({"success": True, "data": dashboard_overview(), "error": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "error": str(e)}), 500


@bp.get("/api/dashboard/trends")
def trends():
    try:
        return jsonify({"success": True, "data": trends_data(), "error": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "error": str(e)}), 500


@bp.get("/api/sectors")
def sectors():
    # No sectors table in the Real Evidence Dataset: distinct values only.
    from services.analytics_service import distinct_sectors

    return jsonify([{"sector_id": s, "sector_name": s} for s in distinct_sectors()])


@bp.get("/api/roles")
def roles():
    c = get_db()
    try:
        return jsonify([dict(r) for r in c.execute("SELECT * FROM job_roles").fetchall()])
    finally:
        c.close()


@bp.get("/api/skills")
def skills():
    try:
        data = compute_skill_demand()
        q = (request.args.get("q") or "").lower()
        sector = request.args.get("sector") or ""
        status = request.args.get("status") or ""
        if q:
            data = [s for s in data if q in s["skill_name"].lower()]
        if sector:
            data = [s for s in data if (s.get("sector") or "") == sector]
        if status:
            data = [s for s in data if s["demand_status"] == status]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/api/skills/<sid>")
def skill_one(sid):
    data = compute_skill_demand()
    hit = next((s for s in data if s["id"] == sid), None)
    if not hit:
        return jsonify({"error": "Skill not found"}), 404
    c = get_db()
    try:
        jobs = [
            dict(r)
            for r in c.execute(
                "SELECT job_title, district, sector, posting_date, salary_min, salary_max, source_type FROM job_postings WHERE skill_ids LIKE ?",
                (f"%{sid}%",),
            ).fetchall()
        ][:20]
        emp = [
            dict(r)
            for r in c.execute(
                "SELECT employer_name, job_role, importance, hiring_demand, difficulty, data_type FROM employer_surveys WHERE skill_id=?",
                (sid,),
            ).fetchall()
        ]
        cur = [
            dict(r)
            for r in c.execute(
                "SELECT c.id, c.course_name FROM courses c JOIN course_skills cs ON cs.course_id=c.id WHERE cs.skill_id=?", (sid,)
            ).fetchall()
        ]
        roles = [dict(r) for r in c.execute("SELECT role_id, job_title, normalized_role, sector, related_skills FROM job_roles").fetchall()]
    finally:
        c.close()
    from services.data_service import skill_ids_for_phrase
    from services.data_service import split_ids as _split

    hit_roles = []
    solo = {sid: {"skill_name": hit["skill_name"], "normalized_skill_name": hit.get("normalized_skill_name")}}
    for r in roles:
        if any(sid in skill_ids_for_phrase(ph, solo) for ph in _split(r.get("related_skills"))):
            hit_roles.append(r)
    hit["evidence_jobs"] = jobs
    hit["evidence_employers"] = emp
    hit["evidence_courses"] = cur
    hit["evidence_roles"] = hit_roles
    hit["provenance"] = {
        "source": hit.get("source"),
        "source_url": hit.get("source_url"),
        "source_title": hit.get("source_title"),
        "publisher": hit.get("publisher"),
        "publication_date": hit.get("publication_date"),
        "data_period": hit.get("data_period"),
        "data_type": hit.get("data_type"),
        "is_synthetic": hit.get("is_synthetic"),
    }
    return jsonify(hit)


@bp.get("/api/skills/<sid>/demand")
def skill_demand(sid):
    data = compute_skill_demand()
    hit = next((s for s in data if s["id"] == sid), None)
    if not hit:
        return jsonify({"error": "Skill not found"}), 404
    return jsonify(
        {
            "skill_id": sid,
            "demand_score": hit["demand_score"],
            "demand_status": hit["demand_status"],
            "demand_count": hit["demand_count"],
            "growth_rate": hit["growth_rate"],
            "methodology": "Demo demand score = 60% normalized synthetic job-posting frequency + 40% normalized synthetic employer hiring demand. "
            "WEF trends are shown separately because they are qualitative sector signals, not skill-level measurements.",
        }
    )


@bp.get("/api/skills/<sid>/gap")
def skill_gap(sid):
    gap = skill_gap_for_skill(sid)
    if not gap:
        return jsonify({"error": "Skill not found"}), 404
    return jsonify(gap)
