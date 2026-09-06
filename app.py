import os
from pathlib import Path

from dotenv import load_dotenv
from flask import jsonify, send_from_directory

load_dotenv()

BASE = Path(__file__).resolve().parent
FRONT = BASE / "frontend"

# Import Flask lazily so a helpful error is shown if deps are missing.
from flask import Flask  # noqa: E402

app = Flask(__name__, static_folder=str(FRONT), static_url_path="")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "kaushora-demo-secret")

from routes.ai_routes import bp as ai_bp  # noqa: E402
from routes.career_routes import bp as career_bp  # noqa: E402
from routes.course_routes import bp as course_bp  # noqa: E402
from routes.dashboard_routes import bp as health_bp  # noqa: E402
from routes.data_routes import bp as data_bp  # noqa: E402
from routes.district_routes import bp as district_bp  # noqa: E402
from routes.employer_routes import bp as employer_bp  # noqa: E402
from routes.skill_routes import bp as skill_bp  # noqa: E402

for b in (health_bp, data_bp, skill_bp, course_bp, district_bp, career_bp, employer_bp, ai_bp):
    app.register_blueprint(b)


@app.errorhandler(404)
def nf(e):
    from flask import request as freq

    path = (freq.path or "")
    if path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    # Missing static assets must 404, not silently return index.html (which
    # would mask broken <script>/<link> references during integration).
    if path.startswith("/assets/") or path.startswith("/css/") or path.startswith("/js/"):
        return jsonify({"error": "Not found"}), 404
    # Asset-like extensions anywhere should 404, not SPA-fallback.
    if Path(path).suffix.lower() in {".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp", ".map", ".json", ".woff", ".woff2"}:
        return jsonify({"error": "Not found"}), 404
    # Extensionless page URLs (e.g. /dashboard) reach this handler because the
    # static route shadows /<path:p> for missing files. Resolve them here.
    p = path.strip("/")
    if p and (FRONT / (p + ".html")).is_file():
        return send_from_directory(FRONT, p + ".html")
    return send_from_directory(FRONT, "index.html")


@app.route("/")
def index():
    return send_from_directory(FRONT, "index.html")


@app.route("/<path:p>")
def pages(p):
    f = FRONT / p
    if f.is_file():
        return send_from_directory(FRONT, p)
    # extensionless -> .html (only for page-like paths, not assets)
    if Path(p).suffix == "" and (FRONT / (p + ".html")).is_file():
        return send_from_directory(FRONT, p + ".html")
    # Asset missing or unknown route: let the 404 handler decide (assets 404, pages fallback)
    if Path(p).suffix.lower() in {".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp", ".map", ".json", ".woff", ".woff2"}:
        return jsonify({"error": "Not found"}), 404
    if (FRONT / (p + ".html")).is_file():
        return send_from_directory(FRONT, p + ".html")
    return send_from_directory(FRONT, "index.html")


if __name__ == "__main__":
    from services.db import DB_PATH

    print(f"[kaushora] database: {DB_PATH}")
    print(f"[kaushora] dataset: {BASE / 'data' / 'raw' / 'kaushora_real_evidence_dataset.md'}")
    # Debug only when explicitly enabled — never in production.
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=debug)
