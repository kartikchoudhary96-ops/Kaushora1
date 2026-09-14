"""Database integrity tests (read-only). Run: python tests/test_data_integrity.py"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(ROOT / "database" / "kaushora.db")

# foreign keys (0 violations)
assert c.execute("SELECT COUNT(*) FROM occupation_skills WHERE occupation_id NOT IN (SELECT role_id FROM job_roles)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM occupation_skills WHERE skill_id NOT IN (SELECT id FROM skills)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM course_skills WHERE course_id NOT IN (SELECT id FROM courses)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM course_skills WHERE skill_id NOT IN (SELECT id FROM skills)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM qualifications WHERE occupation_id NOT IN (SELECT role_id FROM job_roles)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM training_centres WHERE district_id NOT IN (SELECT district_id FROM districts)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM district_capacity WHERE district_id NOT IN (SELECT district_id FROM districts)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM recommendations WHERE district_id NOT IN (SELECT district_id FROM districts)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM skill_aliases WHERE skill_id NOT IN (SELECT id FROM skills)").fetchone()[0] == 0

# duplicate PKs
for tbl, pk in [("sources", "source_id"), ("states", "state_id"), ("districts", "district_id"),
                ("sectors", "sector_id"), ("skills", "id"), ("job_roles", "role_id"),
                ("courses", "id"), ("training_centres", "centre_id"),
                ("labour_indicators", "indicator_id"), ("evidence_metrics", "evidence_id"),
                ("recommendations", "recommendation_id"), ("trends", "trend_id")]:
    dup = c.execute(f"SELECT {pk}, COUNT(*) n FROM {tbl} GROUP BY {pk} HAVING n>1").fetchall()
    assert dup == [], (tbl, dup)
assert c.execute("SELECT occupation_id, skill_id, COUNT(*) FROM occupation_skills GROUP BY 1,2 HAVING COUNT(*)>1").fetchall() == []
assert c.execute("SELECT course_id, skill_id, COUNT(*) FROM course_skills GROUP BY 1,2 HAVING COUNT(*)>1").fetchall() == []

# NULL preservation (not published -> NULL, never 0/empty-string-filled)
assert c.execute("SELECT COUNT(*) FROM district_capacity WHERE training_seats IS NOT NULL").fetchone()[0] == 1  # only Nagpur CTS
assert c.execute("SELECT COUNT(*) FROM labour_indicators WHERE district_id IS NOT NULL").fetchone()[0] == 0
# skill_demand now has 7 real non-NULL scores (was 0 before new data)
assert c.execute("SELECT COUNT(*) FROM skill_demand WHERE demand_score IS NOT NULL").fetchone()[0] == 7

# no synthetic rows in production tables
for tbl in ["skills", "job_roles", "courses", "course_skills",
            "job_postings", "placements", "district_capacity", "training_centres",
            "employer_surveys", "trends"]:
    assert c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE is_synthetic!=0").fetchone()[0] == 0, tbl
for tbl in ["sources", "states", "districts", "sectors", "occupation_skills", "qualifications",
            "labour_indicators", "evidence_metrics", "skill_demand", "district_skill_gaps",
            "curriculum_alignment_ref", "recommendations"]:
    assert c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE data_source!='REAL'").fetchone()[0] == 0, tbl

# data_source labels
for tbl in ["skills", "job_roles", "courses", "districts", "training_centres",
            "labour_indicators", "evidence_metrics", "recommendations"]:
    n = c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE data_source!='REAL' OR data_source IS NULL").fetchone()[0]
    assert n == 0, (tbl, n)

# provenance present on catalog rows (new skills SKL021+ have source_url from WEF/NASSCOM)
assert c.execute("SELECT COUNT(*) FROM skills WHERE source_url IS NULL OR source_url=''").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM job_roles WHERE source_url IS NULL OR source_url=''").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM courses WHERE source_url IS NULL OR source_url=''").fetchone()[0] == 0

# required non-empty tables genuinely populated (updated counts after new research package)
for tbl, n in [("sources", 12), ("states", 2), ("districts", 36), ("sectors", 13), ("skills", 27),
               ("job_roles", 33), ("courses", 29), ("course_skills", 12), ("occupation_skills", 10),
               ("qualifications", 14), ("training_centres", 8), ("labour_indicators", 15),
               ("evidence_metrics", 14), ("recommendations", 3), ("trends", 9),
               ("skill_demand", 7), ("placements", 5), ("skill_aliases", 52)]:
    assert c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0] == n, (tbl, n)

# honestly-empty tables stay empty (source carries none)
for tbl in ["curriculum"]:
    assert c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0] == 0, tbl

# employer_evidence (new table from research package)
assert c.execute("SELECT COUNT(*) FROM employer_evidence").fetchone()[0] == 5

# job_postings (Role Radar: 2,471 real LinkedIn postings)
assert c.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0] == 2471
assert c.execute("SELECT COUNT(*) FROM job_postings WHERE is_synthetic!=0").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM job_posting_skills").fetchone()[0] > 0
assert c.execute("SELECT COUNT(*) FROM job_posting_occupations").fetchone()[0] > 0

# users preserved
assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] >= 2

c.close()
print("test_data_integrity: ALL PASSED")
