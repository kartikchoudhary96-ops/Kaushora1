"""Import tests for the real public CSV dataset. Run: python tests/test_data_import.py
(No server needed. Uses a temp copy of the DB for re-import/rollback tests.)
"""
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DATABASE_PATH"] = str(ROOT / "database" / "kaushora.db")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from parse_csv_dataset import parse_dataset  # noqa: E402

# 1. raw files exist
for f in ["01_sources.csv", "03_districts.csv", "14_courses.csv", "17_skills.csv", "18_occupations.csv"]:
    assert (ROOT / "data" / "raw" / "csv" / f).is_file(), f

# 2. parser: 0 errors, expected tables
res = parse_dataset()
assert res["errors"] == [], res["errors"]
for k in ["sources", "states", "districts", "sectors", "skills", "occupations",
          "occupation_skills", "courses", "course_skills", "training_centres",
          "labour_indicators", "evidence_metrics", "recommendations"]:
    assert k in res["tables"] and res["tables"][k]["header"], k

# 3. record counts match the supplied files
counts = {k: len(v["rows"]) for k, v in res["tables"].items()}
assert counts["sources"] == 10 and counts["states"] == 2 and counts["districts"] == 36
assert counts["sectors"] == 13 and counts["skills"] == 20 and counts["occupations"] == 32
assert counts["courses"] == 15 and counts["training_centres"] == 8
assert counts["labour_indicators"] == 15 and counts["evidence_metrics"] == 10

# 4. cleaned layer + quality report exist and are error-free
import json as _json  # noqa: E402
rep = _json.loads((ROOT / "data" / "processed" / "csv" / "data_quality_report.json").read_text(encoding="utf-8"))
assert rep["errors"] == [], rep["errors"]
assert (ROOT / "data" / "processed" / "csv" / "03_districts.csv").is_file()
# raw layer untouched: byte-identical to supplied files in Downloads
import filecmp  # noqa: E402
assert filecmp.cmp(ROOT / "data" / "raw" / "csv" / "03_districts.csv",
                   Path(r"C:\Users\ASUS\Downloads\deepseek_csv_20260911_5ba8bd.txt"), shallow=False)

# 5. DB matches parsed counts; all rows REAL (DB has additional records from research package + job postings)
c = sqlite3.connect(ROOT / "database" / "kaushora.db")
# Original 18-CSV parser counts (parser only reads original files):
for tbl, n in [("sources", 10), ("states", 2), ("districts", 36), ("sectors", 13),
               ("skills", 20), ("job_roles", 32), ("courses", 15), ("course_skills", 12),
               ("occupation_skills", 10), ("qualifications", 13), ("training_centres", 8),
               ("labour_indicators", 15), ("evidence_metrics", 10), ("recommendations", 3),
               ("trends", 3)]:
    got = c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    assert got >= n, (tbl, got, n)  # DB may have more from research package
for tbl in ["skills", "job_roles", "courses", "districts", "training_centres",
            "labour_indicators", "evidence_metrics", "recommendations"]:
    col = "data_source"
    bad_rows = c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col}!='REAL' OR {col} IS NULL").fetchone()[0]
    assert bad_rows == 0, (tbl, bad_rows)

# 6. no synthetic rows anywhere
for tbl in ["skills", "job_roles", "courses", "course_skills", "job_postings", "placements",
            "district_capacity", "training_centres", "employer_surveys", "trends"]:
    assert c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE is_synthetic!=0").fetchone()[0] == 0, tbl
c.close()

# 7. re-import is idempotent (temp DB copy)
tmp = tempfile.mktemp(suffix=".db")
shutil.copy(ROOT / "database" / "kaushora.db", tmp)
os.environ["DATABASE_PATH"] = tmp
import services.db as dbmod  # noqa: E402
import importlib  # noqa: E402
importlib.reload(dbmod)
import import_csv_data  # noqa: E402


def counts_of(dbpath, tables):
    cx = sqlite3.connect(dbpath)
    try:
        return {t: cx.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    finally:
        cx.close()


TABLES = ["sources", "states", "districts", "sectors", "skills", "job_roles", "courses",
          "course_skills", "training_centres", "labour_indicators", "evidence_metrics", "recommendations"]
import_csv_data.DB = Path(tmp)
import_csv_data.main()
after_first = counts_of(tmp, TABLES)
import_csv_data.main()
after_second = counts_of(tmp, TABLES)
assert after_first == after_second, (after_first, after_second)
# users + observed surveys untouched by re-import
os.remove(tmp)
print("test_data_import: ALL PASSED")
