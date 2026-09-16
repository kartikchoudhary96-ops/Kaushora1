"""Student profile + career intelligence routes.

POST   /api/student/profile              (create, 201)
GET    /api/student/profile/<id>         (full profile)
PUT    /api/student/profile/<id>         (partial update)
DELETE /api/student/profile/<id>         (remove)
GET    /api/student/profiles             (list recent)
POST   /api/student/<id>/skills          {skill_id, proficiency_label}
DELETE /api/student/<id>/skills/<skill_id>
GET    /api/student/<id>/analysis        (full intelligence: matches, gaps, pathway, next actions)
POST   /api/student/validate             (dry-run validation, no DB write)
GET    /api/meta/states                  (all states for location dropdowns)
GET    /api/meta/districts[?state_id=]   (district registry, now from districts table)
GET    /api/meta/skills[q]               (SKL registry, searchable)
GET    /api/meta/occupations[q]          (occupation registry, searchable)
"""
from flask import Blueprint, jsonify, request
from services.student_service import (
    GOAL_OPTIONS, INTEREST_OPTIONS, PREF_OPTIONS, PROF_LABELS, STATUS_OPTIONS,
    create_profile, delete_profile, get_student_analysis, list_profiles, update_profile, validate_profile,
)
from services.db import get_db

bp = Blueprint("student", __name__)


@bp.post("/api/student/validate")
def validate():
    data = request.get_json(force=True, silent=True) or {}
    errs = validate_profile(data)
    return jsonify({"valid": not errs, "errors": errs}), (200 if not errs else 400)


@bp.post("/api/student/profile")
def create():
    data = request.get_json(force=True, silent=True) or {}
    errs = validate_profile(data)
    if errs:
        return jsonify({"error": "Validation failed", "errors": errs}), 400
    try:
        pid = create_profile(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"id": pid, "message": "Profile created"}), 201


@bp.get("/api/student/profiles")
def list_all():
    limit = request.args.get("limit", 20, type=int)
    return jsonify(list_profiles(limit=min(limit, 100)))


@bp.get("/api/student/profile/<int:pid>")
def get_one(pid):
    from services.student_service import _profile_row
    row = _profile_row(pid)
    if not row:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(row)


@bp.put("/api/student/profile/<int:pid>")
def update(pid):
    data = request.get_json(force=True, silent=True) or {}
    # no required-field check on partial updates: only validate supplied keys
    errs = validate_profile(data, partial=True)
    if errs:
        return jsonify({"error": "Validation failed", "errors": errs}), 400
    try:
        row = update_profile(pid, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if row is None:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(row)


@bp.delete("/api/student/profile/<int:pid>")
def remove(pid):
    ok = delete_profile(pid)
    if not ok:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify({"message": "Deleted"}), 200


@bp.post("/api/student/<int:pid>/skills")
def add_skill(pid):
    from services.student_service import _profile_row
    if not _profile_row(pid):
        return jsonify({"error": "Profile not found"}), 404
    d = request.get_json(force=True, silent=True) or {}
    errs = validate_profile({"skills": [d]}, partial=True)
    if errs:
        return jsonify({"error": "Validation failed", "errors": errs}), 400
    # append via update_profile
    cur = _profile_row(pid)
    existing = [{"skill_id": s["skill_id"], "proficiency_label": s["proficiency_label"]} for s in cur["skills"]]
    if any(s["skill_id"] == d.get("skill_id") for s in existing):
        return jsonify({"error": "Skill already added"}), 409
    existing.append(d)
    row = update_profile(pid, {"skills": existing})
    return jsonify(row)


@bp.delete("/api/student/<int:pid>/skills/<skill_id>")
def remove_skill(pid, skill_id):
    from services.student_service import _profile_row
    cur = _profile_row(pid)
    if not cur:
        return jsonify({"error": "Profile not found"}), 404
    kept = [s for s in cur["skills"] if s["skill_id"] != skill_id]
    if len(kept) == len(cur["skills"]):
        return jsonify({"error": "Skill not in profile"}), 404
    row = update_profile(pid, {"skills": [{"skill_id": s["skill_id"], "proficiency_label": s["proficiency_label"]} for s in kept]})
    return jsonify(row)


@bp.get("/api/student/<int:pid>/analysis")
def analysis(pid):
    from services.student_service import _profile_row
    if not _profile_row(pid):
        return jsonify({"error": "Profile not found"}), 404
    try:
        data = get_student_analysis(pid)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(data)


# Meta lookups (real registries, searchable, for wizard dropdowns)
@bp.get("/api/meta/states")
def meta_states():
    c = get_db()
    try:
        return jsonify([dict(r) for r in c.execute("SELECT state_id, state_name, state_code FROM states ORDER BY state_name").fetchall()])
    finally:
        c.close()


@bp.get("/api/meta/districts")
def meta_districts():
    c = get_db()
    try:
        q = request.args.get("q", "").strip().lower()
        sid = request.args.get("state_id")
        sql = "SELECT district_id, district_name, district_code, state_id, state_name FROM districts"
        args = []
        where = []
        if sid:
            where.append("state_id=?")
            args.append(sid)
        if q:
            where.append("lower(district_name) LIKE ?")
            args.append(f"%{q}%")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY district_name"
        return jsonify([dict(r) for r in c.execute(sql, args).fetchall()])
    finally:
        c.close()


@bp.get("/api/meta/skills")
def meta_skills():
    c = get_db()
    try:
        q = (request.args.get("q") or "").strip().lower()
        sql = "SELECT id, skill_name, skill_category, sector FROM skills"
        args = []
        if q:
            sql += " WHERE lower(skill_name) LIKE ? OR lower(id) LIKE ?"
            args.extend([f"%{q}%", f"%{q}%"])
        sql += " ORDER BY skill_name LIMIT 80"
        return jsonify([dict(r) for r in c.execute(sql, args).fetchall()])
    finally:
        c.close()


@bp.get("/api/meta/occupations")
def meta_occs():
    c = get_db()
    try:
        q = (request.args.get("q") or "").strip().lower()
        sector = request.args.get("sector_id")
        sql = "SELECT role_id as occupation_id, job_title as occupation_name, occupation_code, sector, nsqf_level, qp_name, standard_status FROM job_roles"
        where = []
        args = []
        if q:
            where.append("(lower(job_title) LIKE ? OR lower(occupation_code) LIKE ? OR lower(role_id) LIKE ? OR lower(qp_code) LIKE ?)")
            args.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        if sector:
            where.append("sector=?")
            args.append(sector)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY job_title LIMIT 80"
        rows = [dict(r) for r in c.execute(sql, args).fetchall()]
        # Attach per-occupation vacancy counts
        vac = {}
        for r in c.execute("""
            SELECT jpo.occupation_id, COUNT(*) c FROM job_posting_occupations jpo
            GROUP BY jpo.occupation_id
        """).fetchall():
            vac[r["occupation_id"]] = r["c"]
        skill_vac = {}
        for r in c.execute("""
            SELECT os.occupation_id, COUNT(DISTINCT jps.job_id) c
            FROM occupation_skills os
            JOIN job_posting_skills jps ON os.skill_id = jps.skill_id
            GROUP BY os.occupation_id
        """).fetchall():
            skill_vac[r["occupation_id"]] = r["c"]
        for row in rows:
            oid = row["occupation_id"]
            row["posting_count"] = vac.get(oid, 0) or skill_vac.get(oid, 0)
        return jsonify(rows)
    finally:
        c.close()


@bp.get("/api/meta/goals")
def meta_goals():
    return jsonify([{"id": g, "label": g} for g in GOAL_OPTIONS])


@bp.get("/api/meta/interests")
def meta_interests():
    return jsonify([{"id": v, "label": v} for v in INTEREST_OPTIONS])


@bp.get("/api/meta/preferences")
def meta_prefs():
    return jsonify([{"id": v, "label": v} for v in PREF_OPTIONS])


@bp.get("/api/meta/statuses")
def meta_statuses():
    return jsonify([{"id": v, "label": v} for v in STATUS_OPTIONS])


@bp.get("/api/meta/proficiencies")
def meta_profs():
    return jsonify([{"id": v, "label": v} for v in PROF_LABELS])
