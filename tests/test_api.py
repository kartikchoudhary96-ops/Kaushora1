"""API + end-to-end tests on the Real Evidence Dataset.
Start the app separately, then: python tests/test_api.py
Values are cross-checked against SQLite (not just status codes).
"""
import json
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:5000"
ROOT = Path(__file__).resolve().parent.parent
DB = sqlite3.connect(ROOT / "database" / "kaushora.db")
DB.row_factory = sqlite3.Row


def get(p):
    with urllib.request.urlopen(BASE + p) as r:
        return json.loads(r.read())


def post(p, body):
    req = urllib.request.Request(BASE + p, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


h = get("/api/health")
assert h["status"] == "ok" and h["database"] == "connected", h
print("health OK")

ds = get("/api/data/status")
assert ds["success"] is True
assert ds["data"]["dataset_loaded"] is True
assert ds["data"]["record_counts"]["skills"] == 9
assert ds["data"]["record_counts"]["job_postings"] == DB.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0] == 180
assert DB.execute("SELECT COUNT(*) FROM job_postings WHERE is_synthetic=1").fetchone()[0] == 180
assert ds["data"]["empty_entities"] == []
assert ds["data"]["last_ingestion"]["status"] == "success"
print("data/status OK:", ds["data"]["record_counts"])

ov = get("/api/dashboard/overview")
ov = ov["data"] if isinstance(ov, dict) and "data" in ov else ov
db_counts = {t: DB.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ["skills", "courses", "job_roles", "trends"]}
assert ov["totals"]["jobs_analysed"] == DB.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0] == 180, ov["totals"]
assert ov["totals"]["unique_skills"] == db_counts["skills"] == 9
assert ov["totals"]["courses"] == db_counts["courses"] == 3
assert ov["totals"]["roles"] == db_counts["job_roles"] == 4
assert ov["totals"]["trends"] == db_counts["trends"] == 3
assert ov["totals"]["avg_placement_rate"] is not None
assert ov["totals"]["capacity_gap"] is not None and ov["totals"]["capacity_gap"] > 0
assert ov["totals"]["districts"] == 4
assert ov["totals"]["high_demand_skills"] > 0
assert len(ov["sector_demand"]) > 0 and len(ov["district_demand"]) == 4
assert "Real Evidence" in ov["meta"]["source"], ov["meta"]
assert ov["meta"]["limitations"], "limitations must be disclosed"
assert 0 <= (ov["totals"]["avg_alignment"] or 0) <= 100
print("overview OK:", ov["totals"])

dd = get("/api/dashboard/demand")
assert dd["success"] is True
assert dd["data"]["status"] == "available"
assert len(dd["data"]["skills"]) == 9
assert all(s["demand_score"] is not None for s in dd["data"]["skills"])
assert "synthetic" in dd["data"]["reason"].lower()
print("dashboard/demand OK (synthetic-backed scores, disclosed)")

tr = get("/api/dashboard/trends")
tr = tr["data"] if isinstance(tr, dict) and "data" in tr else tr
assert len(tr["monthly_postings"]) > 0 and len(tr["growing_skills"]) > 0
assert len(tr["trend_signals"]) == 3
assert {t["trend_id"] for t in tr["trend_signals"]} == {"TREND-001", "TREND-002", "TREND-003"}

sk = get("/api/skills")
assert len(sk) == 9
assert all(s["is_synthetic"] == 0 and s["demand_score"] is not None
           and s["demand_status"] in ("Critical Demand", "High Demand", "Moderate", "Low") for s in sk), sk
assert {s["id"] for s in sk} == {r[0] for r in DB.execute("SELECT id FROM skills")}
assert len(get("/api/skills?q=database")) >= 1
assert len(get("/api/skills?sector=Healthcare")) == 3
d = get("/api/skills/SK-JSD-02")
assert d["skill_name"] == "Database Management"
assert "QP-JSD" in d["taught_by_courses"]
assert d["provenance"]["source_url"].startswith("https://"), d["provenance"]
assert d["provenance"]["is_synthetic"] == 0
assert any(r["role_id"] == "NCO-2511" for r in d["evidence_roles"])
dem = get("/api/skills/SK-JSD-02/demand")
assert dem["demand_score"] is not None and "methodology" in dem
gap = get("/api/skills/SK-JSD-02/gap")
assert gap["skill_id"] == "SK-JSD-02" and "QP-JSD" in gap["taught_by_courses"]
try:
    get("/api/skills/NOPE/gap")
    raise AssertionError("expected 404")
except urllib.error.HTTPError as e:
    assert e.code == 404
print("skills OK (9 real, synthetic-backed demand scores, gap works)")

sec = get("/api/sectors")
assert {s["sector_name"] for s in sec} >= {"IT-ITeS", "Healthcare", "Finance & Accounting"}
assert len(get("/api/roles")) == 4

co = get("/api/courses")
assert len(co) == 3
assert {c["id"] for c in co} == {"QP-JSD", "QP-DEO", "QP-GDA"}
al = get("/api/courses/QP-JSD/alignment")
assert al["alignment_score"] == 75.0, al["alignment_score"]  # (2 adequate + 0.5x2 partial)/4; synthetic surveys vote SK-JSD-01 Advanced
assert "NCO-2511" in al["matched_roles"], al["matched_roles"]
assert al["evidence"]["data_type"].startswith("real"), al["evidence"]
assert al["missing_count"] == 0 and len(al["partial_skills"]) == 2
assert any("Technical Documentation" in r for r in al["recommended_updates"])
deo = get("/api/courses/QP-DEO/alignment")
assert deo["alignment_score"] is None and deo["recommended_action"] == "Cannot assess", deo
assert ov["totals"]["avg_alignment"] == 75.0
print("courses OK; QP-JSD 75.0% (synthetic employer votes deepen 2 partials); QP-DEO honestly unassessable")

districts = get("/api/districts")
assert len(districts) == 4 and all(d["capacity_gap"] > 0 for d in districts), districts
assert all(d["is_synthetic"] == 1 for d in districts)
nagpur = get("/api/districts/MH-NAG")
assert nagpur["district"]["district"] == "Nagpur" and len(nagpur["placements"]) == 6 and len(nagpur["job_postings"]) == 12
try:
    get("/api/districts/D001")
    raise AssertionError("expected 404")
except urllib.error.HTTPError as e:
    assert e.code == 404
print("districts OK (4 synthetic districts with gaps, detail populated)")

crl = get("/api/careers/roles")
assert len(crl) == 4
assert any(r["role_id"] == "NCO-2511" and r["scorable"] for r in crl)
cr = post("/api/careers/analyze", {"current_skills": "Python"})
assert cr[0] == 200, cr
top = cr[1]["recommended_roles"][0]
assert top["role_id"] == "NCO-2511" and top["match_score"] == 25.0, top
assert any(c["course_id"] == "QP-JSD" for c in cr[1]["recommended_courses"])
assert cr[1]["learning_pathway"] and cr[1]["trend_context"]
bad_career = post("/api/careers/analyze", {"current_skills": "   "})
assert bad_career[0] == 400
print("career OK:", top["job_title"], top["match_score"])

sv = post("/api/employers/survey", {"employer_name": "TestCoE2E", "job_role": "Tester",
                                    "skill": "Software Testing", "importance": 5, "hiring_demand": 4})
assert sv[0] == 201 and sv[1]["skill_id"] == "SK-JSD-03", sv
row = DB.execute("SELECT data_type, is_synthetic FROM employer_surveys WHERE employer_name='TestCoE2E'").fetchone()
assert tuple(row) == ("observed", 0), row
bad = post("/api/employers/survey", {"employer_name": "X"})
assert bad[0] == 400
DB.execute("DELETE FROM employer_surveys WHERE employer_name='TestCoE2E'")
DB.commit()
print("employer OK (stored observed, validated, test row cleaned)")

lg = post("/api/auth/login", {"email": "demo@kaushora.in", "password": "demo123"})
assert lg[0] == 200 and lg[1]["user"]["email"] == "demo@kaushora.in"
ai = post("/api/ai/chat", {"question": "Which skills are most demanded?"})
assert ai[0] == 200 and ai[1]["answer"], ai
print("login + AI OK (ai_available=%s)" % ai[1].get("ai_available"))

print("ALL API/E2E TESTS PASSED")
