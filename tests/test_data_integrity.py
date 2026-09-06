"""Database integrity tests (read-only). Run: python tests/test_data_integrity.py"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(ROOT / "database" / "kaushora.db")

# foreign keys
assert c.execute("SELECT COUNT(*) FROM course_skills WHERE course_id NOT IN (SELECT id FROM courses)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM course_skills WHERE skill_id NOT IN (SELECT id FROM skills)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM curriculum WHERE course_id NOT IN (SELECT id FROM courses)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM curriculum WHERE skill_id NOT IN (SELECT id FROM skills)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM skill_aliases WHERE skill_id NOT IN (SELECT id FROM skills)").fetchone()[0] == 0

# duplicate IDs
for tbl, pk in [("job_roles", "role_id"), ("skills", "id"), ("courses", "id"),
                ("curriculum", "curriculum_id"), ("trends", "trend_id")]:
    dup = c.execute(f"SELECT {pk}, COUNT(*) n FROM {tbl} GROUP BY {pk} HAVING n>1").fetchall()
    assert dup == [], (tbl, dup)
assert c.execute("SELECT course_id, skill_id, COUNT(*) FROM course_skills GROUP BY 1,2 HAVING COUNT(*)>1").fetchall() == []

# invalid numerics / null handling
assert c.execute("SELECT COUNT(*) FROM curriculum WHERE training_hours IS NULL OR training_hours<=0").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM course_skills WHERE hours IS NULL OR hours<=0").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM skills WHERE id IS NULL OR skill_name IS NULL OR skill_name=''").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM job_roles WHERE role_id IS NULL OR job_title IS NULL").fetchone()[0] == 0

# provenance: factual rows real, URLs present, derived marked
for tbl in ["job_roles", "skills", "courses", "curriculum", "trends"]:
    assert c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE is_synthetic!=0").fetchone()[0] == 0, tbl
    assert c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE source_url IS NULL OR source_url=''").fetchone()[0] == 0, tbl
assert c.execute("SELECT COUNT(*) FROM course_skills WHERE data_type!='derived_metric'").fetchone()[0] == 0
assert set(r[0] for r in c.execute("SELECT DISTINCT data_type FROM skills")) == {"official_report"}
assert set(r[0] for r in c.execute("SELECT DISTINCT data_type FROM job_roles")) == {"official_dataset"}

# relationships: every course has skills + modules; every skill taught somewhere
assert c.execute("SELECT COUNT(*) FROM courses WHERE id NOT IN (SELECT course_id FROM course_skills)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM courses WHERE id NOT IN (SELECT course_id FROM curriculum)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM skills WHERE id NOT IN (SELECT skill_id FROM course_skills)").fetchone()[0] == 0

# Synthetic demo rows are explicitly marked, while observed submissions remain separate.
assert c.execute("SELECT COUNT(*) FROM employer_surveys WHERE is_synthetic=1 AND data_type='synthetic'").fetchone()[0] == 24

# Demo tables are populated only with clearly marked synthetic rows.
for tbl in ["job_postings", "placements", "district_capacity", "training_centres"]:
    assert c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE is_synthetic!=1 OR data_type!='synthetic'").fetchone()[0] == 0, tbl

c.close()
print("test_data_integrity: ALL PASSED")
