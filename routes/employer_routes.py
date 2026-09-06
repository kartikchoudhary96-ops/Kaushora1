import hashlib

from flask import Blueprint, jsonify, request, session
from services.data_service import normalize_skill_name
from services.db import get_db

bp = Blueprint("employer_auth", __name__)


def _skill_id_for(name):
    if not name:
        return None
    nid = normalize_skill_name(name)
    if nid:
        return nid
    c = get_db()
    try:
        r = c.execute("SELECT id FROM skills WHERE lower(skill_name)=lower(?)", (name.strip(),)).fetchone()
        return r["id"] if r else None
    finally:
        c.close()


@bp.post("/api/employers/survey")
def survey():
    d = request.get_json(force=True, silent=True) or {}
    req = ["employer_name", "job_role", "skill"]
    missing = [f for f in req if not (d.get(f) or "").strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    try:
        imp = int(d.get("importance", 3))
        assert 1 <= imp <= 5
    except Exception:
        return jsonify({"error": "importance must be 1-5"}), 400
    try:
        dem = int(d.get("hiring_demand", 1))
        assert dem >= 0
    except Exception:
        return jsonify({"error": "hiring_demand must be >= 0"}), 400
    skill_raw = d["skill"].strip()
    sid = _skill_id_for(skill_raw)
    c = get_db()
    try:
        cur = c.execute(
            """INSERT INTO employer_surveys
          (employer_name, industry, state, district, job_role, skill_id, skill_name, importance,
           required_proficiency, hiring_demand, difficulty, data_type, is_synthetic)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                d["employer_name"].strip(),
                d.get("industry", ""),
                d.get("state", ""),
                d.get("district", ""),
                d["job_role"].strip(),
                sid,
                skill_raw,
                imp,
                d.get("required_proficiency", "Intermediate"),
                dem,
                d.get("difficulty", "Medium"),
                "observed",
                0,
            ),
        )
        c.commit()
        rid = cur.lastrowid
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        c.close()
    return jsonify({"message": "Survey saved. Thank you — your input improves demand signals.", "id": rid, "skill_id": sid}), 201


@bp.get("/api/employers/requirements")
def requirements():
    """Genuine user-submitted employer evidence only (source dataset has none)."""
    c = get_db()
    try:
        rows = [dict(r) for r in c.execute("SELECT * FROM employer_surveys ORDER BY id DESC LIMIT 100").fetchall()]
    finally:
        c.close()
    return jsonify(
        {
            "data": rows,
            "note": "Source dataset contains no employer requirements; rows below are user submissions (data_type='observed') only.",
        }
    )


@bp.post("/api/auth/login")
def login():
    d = request.get_json(force=True, silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""
    c = get_db()
    try:
        r = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    finally:
        c.close()
    if not r or r["password_hash"] != hashlib.sha256(pw.encode()).hexdigest():
        return jsonify({"error": "Invalid credentials. Try demo@kaushora.in / demo123"}), 401
    session["user"] = {"email": r["email"], "role": r["role"]}
    return jsonify({"message": "Logged in", "user": session["user"]})


@bp.post("/api/auth/logout")
def logout():
    session.pop("user", None)
    return jsonify({"message": "Logged out"})


@bp.get("/api/auth/me")
def me():
    return jsonify({"user": session.get("user")})
