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
assert ds["data"]["record_counts"]["skills"] == 27
assert ds["data"]["record_counts"]["districts"] == 36
assert ds["data"]["record_counts"]["job_postings"] == DB.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0] == 0
assert DB.execute("SELECT COUNT(*) FROM job_postings WHERE is_synthetic!=0").fetchone()[0] == 0
assert "job_postings" in ds["data"]["empty_entities"]
assert ds["data"]["last_ingestion"]["status"] == "success"
print("data/status OK:", ds["data"]["record_counts"])

ov = get("/api/dashboard/overview")
ov = ov["data"] if isinstance(ov, dict) and "data" in ov else ov
db_counts = {t: DB.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ["skills", "courses", "job_roles", "trends"]}
assert ov["totals"]["jobs_analysed"] == DB.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0] == 0, ov["totals"]
assert ov["totals"]["unique_skills"] == db_counts["skills"] == 27
assert ov["totals"]["courses"] == db_counts["courses"] == 29
assert ov["totals"]["roles"] == db_counts["job_roles"] == 33
assert ov["totals"]["trends"] == db_counts["trends"] == 9
assert ov["totals"]["avg_placement_rate"] is None
assert ov["totals"]["capacity_gap"] is None
assert ov["totals"]["districts"] == 36 and ov["totals"]["centres"] == 8
assert ov["totals"]["high_demand_skills"] == 7, ov["totals"]["high_demand_skills"]
assert len(ov["sector_demand"]) > 0
assert "Kaushora real public dataset" in ov["meta"]["source"], ov["meta"]
assert ov["meta"]["limitations"], "limitations must be disclosed"
assert 0 <= (ov["totals"]["avg_alignment"] or 0) <= 100
print("overview OK:", ov["totals"])

dd = get("/api/dashboard/demand")
assert dd["success"] is True
assert dd["data"]["status"] == "mixed"  # now has 7 real + 20 insufficient
assert len(dd["data"]["skills"]) == 27
demand_with_score = [s for s in dd["data"]["skills"] if s.get("demand_score") is not None]
assert len(demand_with_score) == 7, len(demand_with_score)
print("dashboard/demand OK: %d skills with real scores, %d insufficient" % (len(demand_with_score), 27 - len(demand_with_score)))

tr = get("/api/dashboard/trends")
tr = tr["data"] if isinstance(tr, dict) and "data" in tr else tr
assert tr["monthly_postings"] == [] and tr["growing_skills"] == []
assert len(tr["trend_signals"]) == 9
trend_ids = {t["trend_id"] for t in tr["trend_signals"]}
assert "TREND-001" in trend_ids and "TR001" in trend_ids
print("trends OK: %d signals" % len(tr["trend_signals"]))

sk = get("/api/skills")
assert len(sk) == 27
assert all(s["is_synthetic"] == 0 and s["data_source"] == "REAL" for s in sk)
assert {s["id"] for s in sk} == {r[0] for r in DB.execute("SELECT id FROM skills")}
assert len(get("/api/skills?q=plumbing")) >= 1
assert len(get("/api/skills?sector=Electronics")) >= 1
d = get("/api/skills/SKL001")
assert d["skill_name"] == "Communication"
assert "CRS001" in d["taught_by_courses"]
assert d["provenance"]["source_url"].startswith("https://"), d["provenance"]
assert d["provenance"]["is_synthetic"] == 0 and d["provenance"]["data_source"] == "REAL"
assert any(r["role_id"] == "OCC013" for r in d["evidence_roles"])
dem = get("/api/skills/SKL001/demand")
assert dem["demand_score"] is None and "methodology" in dem
gap = get("/api/skills/SKL001/gap")
assert gap["skill_id"] == "SKL001" and "CRS001" in gap["taught_by_courses"]
try:
    get("/api/skills/NOPE/gap")
    raise AssertionError("expected 404")
except urllib.error.HTTPError as e:
    assert e.code == 404
print("skills OK (27 real, 7 with demand scores, gap works)")

sec = get("/api/sectors")
assert len(sec) >= 13 and {s["sector_name"] for s in sec} >= {"Electronics", "Healthcare", "IT-ITeS"}
assert len(get("/api/roles")) == 33

co = get("/api/courses")
assert len(co) == 29
al = get("/api/courses/CRS001/alignment")
assert al["alignment_score"] == 8.3, al["alignment_score"]
assert al["matched_roles"] == ["OCC013"], al["matched_roles"]
assert any(r["occupation_id"] == "OCC025" and r["alignment_score"] == 100.0 for r in al["reference_pairs"])
assert al["missing_count"] == 5 and len(al["partial_skills"]) == 1
assert any("Plumbing Installation" in r for r in al["recommended_additions"])
no_cov = get("/api/courses/CRS005/alignment")
assert no_cov["alignment_score"] is None and no_cov["recommended_action"] == "Cannot assess"
assert ov["totals"]["avg_alignment"] == 8.3
print("courses OK: %d courses, CRS001 8.3%% vs OCC013" % len(co))

districts = get("/api/districts")
assert len(districts) == 36 and all(d["data_source"] == "REAL" for d in districts)
assert sum(d["training_centres"] for d in districts) == 8
nagpur = get("/api/districts/DT019")
assert nagpur["district"]["district_name"] == "Nagpur"
assert len(nagpur["training_centres"]) == 1
assert nagpur["data_source"] == "REAL"
try:
    get("/api/districts/D001")
    raise AssertionError("expected 404")
except urllib.error.HTTPError as e:
    assert e.code == 404
print("districts OK (36 real districts, Nagpur detail populated)")

crl = get("/api/careers/roles")
assert len(crl) == 33
assert any(r["role_id"] == "OCC013" and r["scorable"] for r in crl)
cr = post("/api/careers/analyze", {"current_skills": "Plumbing Installation"})
assert cr[0] == 200, cr
top = cr[1]["recommended_roles"][0]
assert top["role_id"] == "OCC013" and top["match_score"] == round(100 / 6, 1), top
assert cr[1]["learning_pathway"] and cr[1]["trend_context"]
bad_career = post("/api/careers/analyze", {"current_skills": "   "})
assert bad_career[0] == 400
print("career OK:", top["job_title"], top["match_score"])

sv = post("/api/employers/survey", {"employer_name": "TestCoE2E", "job_role": "Tester",
                                    "skill": "Plumbing Installation", "importance": 5, "hiring_demand": 4})
assert sv[0] == 201 and sv[1]["skill_id"] == "SKL007", sv
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
assert ai[1]["grounded"] is True and ai[1]["data_source"] == "REAL"
assert ai[1]["evidence"], "AI must cite evidence sources"
ind = get("/api/indicators")
assert len(ind["data"]) == 15 and ind["data"][0]["indicator_value"] == 59.3
ev = get("/api/evidence")
assert len(ev["data"]) == 14, len(ev["data"])
rec = get("/api/recommendations")
assert len(rec["data"]) >= 6 and any(r["engine"] for r in rec["data"])
print("login + AI OK (ai_available=%s, grounded=%s)" % (ai[1].get("ai_available"), ai[1].get("grounded")))

print("ALL API/E2E TESTS PASSED")
