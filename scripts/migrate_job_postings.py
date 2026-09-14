"""Additive schema migration for job_postings + junction tables.
Run AFTER import_csv_data.py. Only adds columns/tables; never drops."""
import sqlite3, os, sys

DB = os.path.join(os.path.dirname(__file__), "..", "database", "kaushora.db")

def migrate():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    added = []

    # --- Additive columns on job_postings ---
    add_cols = [
        ("employer_name", "TEXT"),
        ("occupation", "TEXT"),
        ("remote_flag", "INTEGER DEFAULT 0"),
        ("scraped_at", "TEXT"),
        ("publication_year", "INTEGER"),
        ("data_period", "TEXT"),
        ("geography_level", "TEXT DEFAULT 'city'"),
        ("observed_or_derived", "TEXT DEFAULT 'observed'"),
        ("confidence", "TEXT DEFAULT 'high'"),
        ("notes", "TEXT"),
    ]
    existing = {row[1] for row in c.execute("PRAGMA table_info(job_postings)").fetchall()}
    for col, typ in add_cols:
        if col not in existing:
            c.execute(f"ALTER TABLE job_postings ADD COLUMN {col} {typ}")
            added.append(f"job_postings.{col}")

    # --- Junction table: job_posting_skills ---
    c.execute("""CREATE TABLE IF NOT EXISTS job_posting_skills (
        job_id TEXT NOT NULL,
        skill_id TEXT NOT NULL,
        confidence TEXT DEFAULT 'high',
        PRIMARY KEY (job_id, skill_id),
        FOREIGN KEY (job_id) REFERENCES job_postings(id),
        FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
    )""")
    added.append("job_posting_skills (created)")

    # --- Junction table: job_posting_occupations ---
    c.execute("""CREATE TABLE IF NOT EXISTS job_posting_occupations (
        job_id TEXT NOT NULL,
        occupation_id TEXT NOT NULL,
        PRIMARY KEY (job_id, occupation_id),
        FOREIGN KEY (job_id) REFERENCES job_postings(id),
        FOREIGN KEY (occupation_id) REFERENCES job_roles(occupation_id)
    )""")
    added.append("job_posting_occupations (created)")

    # --- Indexes ---
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_jp_state ON job_postings(state)",
        "CREATE INDEX IF NOT EXISTS idx_jp_industry ON job_postings(industry)",
        "CREATE INDEX IF NOT EXISTS idx_jp_employment ON job_postings(employment_type)",
        "CREATE INDEX IF NOT EXISTS idx_jps_skill ON job_posting_skills(skill_id)",
        "CREATE INDEX IF NOT EXISTS idx_jpo_occupation ON job_posting_occupations(occupation_id)",
    ]:
        c.execute(idx_sql)
    added.append("indexes (created)")

    conn.commit()
    conn.close()
    print(f"Migration complete. Added: {', '.join(added)}")

if __name__ == "__main__":
    migrate()
