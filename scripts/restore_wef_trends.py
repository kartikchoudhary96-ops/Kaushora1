"""One-off restore of the 3 real WEF trend rows from the legacy .md dataset.

The fresh CSV migration recreated the DB file, which dropped the previously
imported WEF trends (the CSV source carries no replacement). Trends are real
public evidence (World Economic Forum), so they are restored verbatim with
full provenance rather than re-typed. Idempotent (DELETE+INSERT by PK).

Run once: python scripts/restore_wef_trends.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "archive"))
from parse_evidence_dataset import parse_dataset

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database" / "kaushora.db"


def main():
    # Archived parser resolves paths from its own dir; point it at the real file.
    res = parse_dataset(path=BASE / "data" / "raw" / "kaushora_real_evidence_dataset.md")
    if res["errors"]:
        print("Parser errors, aborting:")
        for e in res["errors"]:
            print(" ", e)
        raise SystemExit(1)
    rows = res["tables"]["trends"]["rows"]
    conn = sqlite3.connect(DB)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        c.execute("DELETE FROM trends WHERE trend_id IN ('TREND-001','TREND-002','TREND-003')")
        for r in rows:
            c.execute("INSERT INTO trends VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["trend_id"], r.get("technology_or_skill", ""), r.get("sector", ""),
                       r.get("trend_description", ""), r.get("evidence", ""),
                       r.get("trend_direction", ""), r.get("period", ""), r.get("source", ""),
                       r.get("source_url", ""), r.get("source_title", ""), r.get("publisher", ""),
                       r.get("data_type", "official_report"), int(r.get("is_synthetic") or 0)))
        c.execute("INSERT OR REPLACE INTO dataset_meta VALUES (?,?,?,?)",
                  ("trends", "3 WEF Future of Jobs rows restored from legacy .md (no replacement in CSV source).",
                   len(rows), "imported"))
        conn.commit()
    finally:
        conn.close()
    print(f"Restored {len(rows)} WEF trend rows (is_synthetic=0).")


if __name__ == "__main__":
    main()
