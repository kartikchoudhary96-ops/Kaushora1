"""Analytics unit tests on the real public CSV dataset.
Run: python tests/test_analytics.py (no server needed; uses SQLite DB).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DATABASE_PATH"] = str(ROOT / "database" / "kaushora.db")
sys.path.insert(0, str(ROOT))

from services.analytics_service import (compute_skill_demand, dashboard_overview, district_summary,  # noqa: E402
                                        evidence_metrics, labour_indicators, recommendations_live, trends_data)
from services.skill_gap_service import career_analyze, course_alignment, district_detail, skill_gap_for_skill  # noqa: E402

# 1. skill demand: 20 real skills, honestly no scores (source assessment NULL)
skills = compute_skill_demand()
assert len(skills) == 20, len(skills)
assert all(s["is_synthetic"] == 0 and s["data_source"] == "REAL" for s in skills)
assert all(s["demand_score"] is None for s in skills)
assert all(s["demand_status"] == "Insufficient data" for s in skills)
skl001 = next(s for s in skills if s["id"] == "SKL001")
assert skl001["related_roles"] == ["OCC013"] and "CRS001" in skl001["taught_by_courses"]

# 2. dashboard overview derived from real counts
ov = dashboard_overview()
t = ov["totals"]
assert (t["unique_skills"], t["courses"], t["roles"]) == (20, 15, 32)
assert (t["districts"], t["centres"], t["trends"]) == (36, 8, 3)
assert t["jobs_analysed"] == 0 and t["high_demand_skills"] == 0
assert t["avg_placement_rate"] is None and t["capacity_gap"] is None
assert t["avg_alignment"] is not None and 0 <= t["avg_alignment"] <= 100
assert len(ov["sector_demand"]) > 0 and len(ov["district_demand"]) == 2
assert "demand_score" in str(ov["meta"]["insufficient"]) or ov["meta"]["insufficient"]

# 3. trends: 3 WEF signals, no invented time series
tr = trends_data()
assert len(tr["trend_signals"]) == 3
assert tr["monthly_postings"] == [] and tr["growing_skills"] == []

# 4. course alignment from explicit mappings + reference pairs
al = course_alignment("CRS001")
assert al["alignment_score"] == round((0 + 0.5 * 1) / 6 * 100, 1) == 8.3, al["alignment_score"]
assert al["matched_roles"] == ["OCC013"]
assert any(r["occupation_id"] == "OCC025" and r["alignment_score"] == 100.0 for r in al["reference_pairs"])
assert al["missing_count"] == 5
no_cov = course_alignment("CRS005")
assert no_cov["alignment_score"] is None and no_cov["recommended_action"] == "Cannot assess"
assert course_alignment("NOPE") is None

# 5. skill gap view
gap = skill_gap_for_skill("SKL001")
assert gap["skill_id"] == "SKL001"
assert gap["required_by_roles"] == ["OCC013"]
assert "CRS001" in gap["taught_by_courses"]
assert skill_gap_for_skill("NOPE") is None

# 6. district detail is real (Nagpur)
dd = district_detail("DT019")
assert dd["district"]["district_name"] == "Nagpur"
assert len(dd["training_centres"]) == 1
assert dd["summary"]["recommendations"] == 2
assert dd["data_source"] == "REAL"
assert district_detail("DT999") is None

# 7. indicators + evidence + recommendations are observed
assert len(labour_indicators()) == 15
assert len(evidence_metrics()) == 10
recs = recommendations_live()
assert len([r for r in recs if not r["engine"]]) == 3
assert any(r["engine"] for r in recs)
assert len(district_summary()) == 36

# 8. career matching deterministic + input-sensitive
cr = career_analyze({"current_skills": "Data Entry"})
assert cr["recommended_roles"], "must return roles"
cr2 = career_analyze({"current_skills": "Data Entry"})
assert cr == cr2, "matching must be deterministic"
cr3 = career_analyze({"current_skills": "Plumbing Installation"})
assert cr3["recommended_roles"][0]["role_id"] == "OCC013", "SKL007 is required by OCC013"
assert cr["recommended_roles"][0]["role_id"] != "OCC013", "SKL011 is required by no occupation"

print("test_analytics: ALL PASSED")
