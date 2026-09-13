"""Additive migration for student profile tables (never wipes data).

Applies the student_* tables from schema.sql to the live database.
Safe to re-run (CREATE TABLE IF NOT EXISTS).

Run: python scripts/migrate_student.py
"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database" / "kaushora.db"

STUDENT_DDL = """
CREATE TABLE IF NOT EXISTS student_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  status TEXT NOT NULL,
  state_id TEXT,
  district_id TEXT,
  location_text TEXT,
  education_level TEXT,
  course_program TEXT,
  specialization TEXT,
  year_semester TEXT,
  qualification TEXT,
  nsqf_level TEXT,
  goal TEXT,
  FOREIGN KEY (state_id) REFERENCES states(state_id),
  FOREIGN KEY (district_id) REFERENCES districts(district_id)
);
CREATE TABLE IF NOT EXISTS student_profile_skills (
  profile_id INTEGER NOT NULL,
  skill_id TEXT NOT NULL,
  proficiency_label TEXT DEFAULT 'Comfortable',
  proficiency_rank TEXT DEFAULT 'Intermediate',
  PRIMARY KEY (profile_id, skill_id),
  FOREIGN KEY (profile_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (skill_id) REFERENCES skills(id)
);
CREATE TABLE IF NOT EXISTS student_profile_interests (
  profile_id INTEGER NOT NULL,
  interest TEXT NOT NULL,
  PRIMARY KEY (profile_id, interest),
  FOREIGN KEY (profile_id) REFERENCES student_profiles(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS student_profile_preferences (
  profile_id INTEGER NOT NULL,
  preference TEXT NOT NULL,
  PRIMARY KEY (profile_id, preference),
  FOREIGN KEY (profile_id) REFERENCES student_profiles(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sps_profile ON student_profile_skills(profile_id);
CREATE INDEX IF NOT EXISTS idx_spi_profile ON student_profile_interests(profile_id);
CREATE INDEX IF NOT EXISTS idx_spp_profile ON student_profile_preferences(profile_id);
"""


def main():
    conn = sqlite3.connect(DB)
    try:
        conn.executescript(STUDENT_DDL)
        conn.commit()
    finally:
        conn.close()
    print("Student profile tables ensured (additive, data preserved).")


if __name__ == "__main__":
    main()
