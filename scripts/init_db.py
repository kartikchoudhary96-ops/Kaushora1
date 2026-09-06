import hashlib
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database" / "kaushora.db"
SCHEMA = BASE / "database" / "schema.sql"


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.execute(
        "INSERT OR IGNORE INTO users (email,password_hash,role) VALUES (?,?,?)",
        ("demo@kaushora.in", hashlib.sha256("demo123".encode()).hexdigest(), "admin"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (email,password_hash,role) VALUES (?,?,?)",
        ("employer@demo.in", hashlib.sha256("demo123".encode()).hexdigest(), "employer"),
    )
    conn.commit()
    conn.close()
    print(f"DB initialised at {DB}")
    print("Next run: python scripts/import_data.py; python scripts/seed_synthetic.py")


if __name__ == "__main__":
    main()
