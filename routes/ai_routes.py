from flask import Blueprint, jsonify, request
from services.ai_service import ask_ai, build_context

bp = Blueprint("ai", __name__)


@bp.post("/api/ai/chat")
def chat():
    d = request.get_json(force=True, silent=True) or {}
    q = (d.get("question") or d.get("message") or "").strip()
    if not q:
        return jsonify({"error": "Please enter a question."}), 400
    # Build grounded context from live DB (student-aware if student_id provided)
    student_id = d.get("student_id") or request.args.get("student_id")
    entity = d.get("entity") or request.args.get("entity")
    entity_id = d.get("entity_id") or request.args.get("entity_id")
    try:
        return jsonify(ask_ai(q, student_id=student_id, entity=entity, entity_id=entity_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/api/ai/context")
def context():
    """Structured context for debugging / transparency (no model call)."""
    student_id = request.args.get("student_id")
    entity = request.args.get("entity")
    entity_id = request.args.get("entity_id")
    try:
        ctx = build_context(student_id=student_id, entity=entity, entity_id=entity_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(ctx)
