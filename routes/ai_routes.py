from flask import Blueprint, jsonify, request
from services.ai_service import ask_ai
from services.analytics_service import dashboard_overview

bp = Blueprint("ai", __name__)


@bp.post("/api/ai/chat")
def chat():
    d = request.get_json(force=True, silent=True) or {}
    q = (d.get("question") or d.get("message") or "").strip()
    if not q:
        return jsonify({"error": "Please enter a question."}), 400
    try:
        ctx = dashboard_overview()
    except Exception:
        ctx = {}
    try:
        return jsonify(ask_ai(q, ctx))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
