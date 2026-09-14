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

# 1. skill demand: 27 real skills (20 original + 7 WEF/NASSCOM), 7 with observed scores
skills = compute_skill_demand()
assert len(skills) == 27, len(skills)
assert all(s["is_synthetic"] == 0 and s["data_source"] == "REAL" for s in skills)
demand_with_score = [s for s in skills if s["demand_status"] in ("Critical Demand", "High Demand")]
demand_insufficient = [s for s in skills if s["demand_status"] == "Insufficient data"]
demand_low = [s for s in skills if s["demand_status"] == "Low"]
assert len(demand_with_score) == 7, len(demand_with_score)
assert len(demand_insufficient) == 13, len(demand_insufficient)  # 27 - 7 scored - 7 low = 13 insufficient
assert len(demand_low) == 7, len(demand_low)  # skills with job posting counts but no source score
# Verify real demand scores exist
assert any(s["demand_score"] == 85.0 for s in demand_with_score), "Expected at least one 85% score"
assert any(s["demand_score"] == 60.0 for s in demand_with_score), "Expected at least one 60% score"
skl001 = next(s for s in skills if s["id"] == "SKL001")
assert skl001["related_roles"] == ["OCC013"] and "CRS001" in skl001["taught_by_courses"]

# 2. dashboard overview derived from real counts
ov = dashboard_overview()
t = ov["totals"]
assert (t["unique_skills"], t["courses"], t["roles"]) == (27, 29, 33), (t["unique_skills"], t["courses"], t["roles"])
assert (t["districts"], t["centres"]) == (36, 8)
assert t["jobs_analysed"] == 2471, t["jobs_analysed"]
assert t["high_demand_skills"] == 7, t["high_demand_skills"]
assert t["avg_placement_rate"] is None and t["capacity_gap"] is None
assert t["avg_alignment"] is not None and 0 <= t["avg_alignment"] <= 100
assert len(ov["sector_demand"]) > 0
assert "demand_score" in str(ov["meta"]["insufficient"]) or ov["meta"]["insufficient"]

# 3. trends: 9 signals (3 original WEF + 6 new WEF/NSDC/SIDH)
tr = trends_data()
assert len(tr["trend_signals"]) == 9, len(tr["trend_signals"])
assert len(tr["monthly_postings"]) >= 1, "Should have monthly posting data from ingested job postings"
assert tr["growing_skills"] == []

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
assert dd["data_source"] == "REAL"
assert district_detail("DT999") is None

# 7. indicators + evidence + recommendations are observed
assert len(labour_indicators()) == 15
assert len(evidence_metrics()) == 14, len(evidence_metrics())
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
