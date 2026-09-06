"""Import tests for the Real Evidence Dataset. Run: python tests/test_data_import.py
(No server needed. Uses a temp copy of the DB for re-import/rollback tests.)
"""
import copy
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DATABASE_PATH"] = str(ROOT / "database" / "kaushora.db")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from parse_evidence_dataset import parse_dataset, DATASET_PATH  # noqa: E402

# 1. canonical dataset file exists
assert DATASET_PATH.is_file(), "canonical dataset missing"

# 2-3. parser reads it; all expected sections found
res = parse_dataset()
assert res["errors"] == [], res["errors"]
for k in ["job_roles", "skills", "courses", "course_skills", "curriculum", "trends"]:
    assert k in res["tables"] and res["tables"][k]["header"], k

# 4-5. record counts correct
assert res["counts"]["job_roles"] == 4, res["counts"]
assert res["counts"]["skills"] == 9
assert res["counts"]["courses"] == 3
assert res["counts"]["course_skills"] == 9
assert res["counts"]["curriculum"] == 9
assert res["counts"]["trends"] == 3

# 6. IDs unique
import sqlite3  # noqa: E402

c = sqlite3.connect(ROOT / "database" / "kaushora.db")
for tbl, pk in [("job_roles", "role_id"), ("skills", "id"), ("courses", "id"),
                ("curriculum", "curriculum_id"), ("trends", "trend_id")]:
    n = c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    u = c.execute(f"SELECT COUNT(DISTINCT {pk}) FROM {tbl}").fetchone()[0]
    assert n == u and n > 0, (tbl, n, u)

# 7. FKs valid
assert c.execute("SELECT COUNT(*) FROM course_skills WHERE course_id NOT IN (SELECT id FROM courses)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM course_skills WHERE skill_id NOT IN (SELECT id FROM skills)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM curriculum WHERE course_id NOT IN (SELECT id FROM courses)").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM curriculum WHERE skill_id NOT IN (SELECT id FROM skills)").fetchone()[0] == 0

# 8. provenance preserved: no synthetic dataset rows, URLs present
assert c.execute("SELECT COUNT(*) FROM skills WHERE is_synthetic!=0").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM skills WHERE source_url IS NULL OR source_url=''").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM job_roles WHERE is_synthetic!=0").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM courses WHERE is_synthetic!=0").fetchone()[0] == 0
assert c.execute("SELECT COUNT(*) FROM trends WHERE is_synthetic!=0").fetchone()[0] == 0
c.close()

# 9-10. re-import is idempotent; invalid data rolls back (temp DB)
tmp = tempfile.mktemp(suffix=".db")
shutil.copy(ROOT / "database" / "kaushora.db", tmp)
os.environ["DATABASE_PATH"] = tmp
import importlib  # noqa: E402

import services.db as dbmod  # noqa: E402

importlib.reload(dbmod)
import import_data  # noqa: E402


def counts(dbpath, tables):
    cx = sqlite3.connect(dbpath)
    try:
        return {t: cx.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    finally:
        cx.close()


TABLES = ["job_roles", "skills", "courses", "course_skills", "curriculum", "trends"]
before = counts(tmp, TABLES)
import_data.DB = Path(tmp)
import_data.main()
after = counts(tmp, TABLES)
assert before == after, (before, after)

bad = copy.deepcopy(res)
bad["tables"]["curriculum"]["rows"] = bad["tables"]["curriculum"]["rows"] + [{
    "curriculum_id": "CUR-BAD", "course_id": "NO-SUCH-COURSE", "module_name": "x",
    "skill_id": "SK-JSD-01", "proficiency_level": "Basic", "training_hours": "10",
    "module_status": "Active"}]
bad["errors"] = ["FK violation: curriculum.course_id='NO-SUCH-COURSE' unknown"]
import_data.parse_dataset = lambda path=None: bad
try:
    import_data.main()
    raise AssertionError("import should have aborted on validation errors")
except SystemExit as e:
    assert e.code == 1
rolled_back = counts(tmp, TABLES)
assert rolled_back == before, rolled_back
os.remove(tmp)
print("test_data_import: ALL PASSED")
