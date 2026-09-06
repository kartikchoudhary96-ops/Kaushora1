from datetime import datetime, timezone

from flask import Blueprint, jsonify
from services.db import check_db

bp = Blueprint("health", __name__)


@bp.get("/api/health")
def health():
    ok = check_db()
    return (
        jsonify(
            {
                "status": "ok" if ok else "error",
                "database": "connected" if ok else "disconnected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        (200 if ok else 500),
    )
