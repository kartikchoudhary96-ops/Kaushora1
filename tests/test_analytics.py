"""Analytics unit tests — deterministic checks on the Real Evidence Dataset.
Run: python tests/test_analytics.py (no server needed; uses the real SQLite DB).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DATABASE_PATH"] = str(ROOT / "database" / "kaushora.db")
sys.path.insert(0, str(ROOT))

from services.analytics_service import compute_skill_demand, dashboard_overview, trends_data  # noqa: E402
from services.skill_gap_service import career_analyze, course_alignment, skill_gap_for_skill  # noqa: E402

# 1. skill demand: 9 real skills, no fabricated scores
skills = compute_skill_demand()
assert len(skills) == 9, skills
assert all(s["is_synthetic"] == 0 for s in skills)
assert all(s["demand_score"] is not None for s in skills), "synthetic demo signals should produce scores"
assert any(s["demand_status"] in ("Critical Demand", "High Demand") for s in skills)

# 2. dashboard overview is derived, not hardcoded
ov = dashboard_overview()
assert ov["totals"]["unique_skills"] == 9
assert ov["totals"]["courses"] == 3
assert ov["totals"]["roles"] == 4
assert ov["totals"]["trends"] == 3
assert ov["totals"]["jobs_analysed"] == 180
assert ov["totals"]["capacity_gap"] is not None
assert ov["totals"]["avg_placement_rate"] is not None
assert ov["totals"]["avg_alignment"] == 75.0, ov["totals"]["avg_alignment"]  # synthetic employer votes: SK-JSD-01 Advanced, SK-JSD-04 Intermediate

# 3. trends: 3 qualitative WEF signals, no time series invented
tr = trends_data()
assert len(tr["trend_signals"]) == 3
assert len(tr["monthly_postings"]) > 0

# 4. course alignment: QP-JSD scores 75.0 (2 adequate + 0.5x2 partial)/4; QP-DEO honestly unassessable
al = course_alignment("QP-JSD")
assert al["alignment_score"] == 75.0, al["alignment_score"]
assert al["missing_count"] == 0 and len(al["partial_skills"]) == 2
deo = course_alignment("QP-DEO")
assert deo["alignment_score"] is None and deo["recommended_action"] == "Cannot assess"
assert course_alignment("NOPE") is None

# 5. skill gap view
gap = skill_gap_for_skill("SK-JSD-02")
assert gap["skill_id"] == "SK-JSD-02"
assert "NCO-2511" in gap["required_by_roles"]
assert "QP-JSD" in gap["taught_by_courses"]
assert skill_gap_for_skill("NOPE") is None

# 6. career matching is deterministic
cr = career_analyze({"current_skills": "Python"})
assert cr["recommended_roles"][0]["role_id"] == "NCO-2511"
assert cr["recommended_roles"][0]["match_score"] == 25.0
cr2 = career_analyze({"current_skills": "Python"})
assert cr == cr2, "matching must be deterministic"

print("test_analytics: ALL PASSED")
