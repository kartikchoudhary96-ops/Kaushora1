"""DDL migration for Problem #2 occupation->QP->NOS->skill evidence.

Creates: occupation_nos, nos_competencies, new_skill_candidates,
candidate_aliases. Extends occupation_skills with provenance columns
(all nullable so existing 10 rows are untouched).
Idempotent: safe to run multiple times. DDL only, no data import.
"""
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database" / "kaushora.db"

NEW_COLUMNS = [
    ("qp_code", "TEXT"),
    ("mapping_method", "TEXT"),
    ("mapping_source", "TEXT"),
    ("source_url", "TEXT"),
    ("confidence", "TEXT"),
    ("observed_or_derived", "TEXT"),
    ("evidence_text", "TEXT"),
    ("review_status", "TEXT"),
]


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("""CREATE TABLE IF NOT EXISTS occupation_nos (
          occupation_id TEXT NOT NULL,
          research_occupation_id TEXT NOT NULL,
          occupation_name TEXT NOT NULL,
          qp_code TEXT NOT NULL,
          qp_title TEXT,
          originating_qp_code TEXT,
          sector_skill_council TEXT,
          nsqf_level TEXT,
          qp_status TEXT NOT NULL,
          nos_code TEXT NOT NULL,
          nos_title TEXT,
          nos_status TEXT,
          source_id TEXT NOT NULL,
          source_url TEXT,
          publication_year INTEGER,
          observed_or_derived TEXT NOT NULL,
          confidence TEXT NOT NULL,
          notes TEXT,
          data_source TEXT DEFAULT 'REAL',
          PRIMARY KEY (occupation_id, nos_code),
          FOREIGN KEY (occupation_id) REFERENCES job_roles(role_id),
          FOREIGN KEY (source_id) REFERENCES sources(source_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS nos_competencies (
          competency_id TEXT PRIMARY KEY,
          qp_code TEXT NOT NULL,
          nos_code TEXT NOT NULL,
          nos_title TEXT,
          competency_text TEXT,
          knowledge_text TEXT,
          performance_text TEXT,
          source_id TEXT NOT NULL,
          source_url TEXT,
          evidence_type TEXT,
          observed_or_derived TEXT NOT NULL,
          confidence TEXT NOT NULL,
          notes TEXT,
          data_source TEXT DEFAULT 'REAL',
          FOREIGN KEY (source_id) REFERENCES sources(source_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS new_skill_candidates (
          candidate_skill_id TEXT NOT NULL,
          skill_name TEXT NOT NULL,
          occupation_id TEXT NOT NULL,
          qp_code TEXT,
          nos_code TEXT,
          original_competency TEXT,
          mapping_explanation TEXT,
          classification TEXT NOT NULL,
          possible_skl_match TEXT,
          confidence TEXT,
          source_id TEXT,
          source_url TEXT,
          review_status TEXT DEFAULT 'pending',
          notes TEXT,
          data_source TEXT DEFAULT 'REAL',
          PRIMARY KEY (candidate_skill_id, occupation_id, nos_code),
          FOREIGN KEY (occupation_id) REFERENCES job_roles(role_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS candidate_aliases (
          alias TEXT PRIMARY KEY,
          candidate_skill_id TEXT NOT NULL,
          source_context TEXT,
          mapping_basis TEXT,
          source_id TEXT,
          confidence TEXT,
          review_status TEXT DEFAULT 'pending',
          notes TEXT,
          data_source TEXT DEFAULT 'REAL'
        )""")
        existing = {r[1] for r in c.execute("PRAGMA table_info(occupation_skills)").fetchall()}
        for col, typ in NEW_COLUMNS:
            if col not in existing:
                c.execute(f"ALTER TABLE occupation_skills ADD COLUMN {col} {typ}")
                print(f"added occupation_skills.{col}")
            else:
                print(f"occupation_skills.{col} already exists")
        conn.commit()
        print("migration OK: 4 tables ensured, occupation_skills extended")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
