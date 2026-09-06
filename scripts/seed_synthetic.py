"""Seed synthetic data to make all features functional.

This generates realistic, deterministic synthetic data for the tables that
are intentionally empty in the Real Evidence Dataset. All synthetic rows
have is_synthetic=1 and data_type='synthetic' so they are distinguishable
from real evidence, but analytics will include them so dashboards, districts,
placements, etc. actually populate.

Run: python scripts/seed_synthetic.py  (idempotent - clears old synthetic first)
"""
import sqlite3
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database" / "kaushora.db"

random.seed(42)

# Real catalog from DB (to keep FKs valid)
def get_real():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    skills = [dict(r) for r in c.execute("SELECT id, skill_name, sector FROM skills").fetchall()]
    courses = [dict(r) for r in c.execute("SELECT id, course_name, sector FROM courses").fetchall()]
    roles = [dict(r) for r in c.execute("SELECT role_id, job_title, sector FROM job_roles").fetchall()]
    c.close()
    return skills, courses, roles

DISTRICTS = [
    {"district_id": "MH-NAG", "district": "Nagpur", "state": "Maharashtra", "pop": "Large", "sectors": "IT-ITeS, Manufacturing, Logistics", "priority": "High"},
    {"district_id": "MH-PUN", "district": "Pune", "state": "Maharashtra", "pop": "Large", "sectors": "IT-ITeS, Automotive, Healthcare", "priority": "High"},
    {"district_id": "MH-MUM", "district": "Mumbai", "state": "Maharashtra", "pop": "Metro", "sectors": "IT-ITeS, Finance, Healthcare", "priority": "Critical"},
    {"district_id": "MH-NSK", "district": "Nashik", "state": "Maharashtra", "pop": "Medium", "sectors": "Manufacturing, Agriculture, Healthcare", "priority": "Medium"},
]

CENTRES = [
    ("TC-NAG-01", "Nagpur Skill Centre", "MH-NAG", "Nagpur", "QP-JSD,QP-DEO", 120, 95, 8),
    ("TC-NAG-02", "Nagpur Healthcare Institute", "MH-NAG", "Nagpur", "QP-GDA", 80, 70, 6),
    ("TC-PUN-01", "Pune IT Park Training Hub", "MH-PUN", "Pune", "QP-JSD", 150, 130, 10),
    ("TC-PUN-02", "Pune Data Entry Academy", "MH-PUN", "Pune", "QP-DEO", 100, 85, 5),
    ("TC-MUM-01", "Mumbai Metro Skill Centre", "MH-MUM", "Mumbai", "QP-JSD,QP-GDA", 200, 180, 12),
    ("TC-NSK-01", "Nashik Industrial Training Centre", "MH-NSK", "Nashik", "QP-DEO,QP-GDA", 90, 60, 4),
]

def seed():
    skills, courses, roles = get_real()
    skill_ids = [s["id"] for s in skills]
    # Weight IT skills higher for realism
    weights = {"SK-JSD-01": 3.0, "SK-JSD-02": 2.5, "SK-JSD-03": 2.0, "SK-JSD-04": 1.2,
               "SK-DEO-01": 2.2, "SK-DEO-02": 1.5,
               "SK-GDA-01": 1.8, "SK-GDA-02": 1.0, "SK-GDA-03": 1.3}
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Clear old synthetic (idempotent)
    for tbl in ["job_postings", "district_capacity", "training_centres", "placements", "employer_surveys"]:
        # Keep real user submissions (is_synthetic=0) but clear synthetic
        cur.execute(f"DELETE FROM {tbl} WHERE is_synthetic=1")
    # Also clear synthetic dataset_meta entries if any, then re-add
    cur.execute("DELETE FROM dataset_meta WHERE section IN ('synthetic_districts','synthetic_jobs','synthetic_placements','synthetic_employers')")

    now = datetime.now(timezone.utc)
    today = now.date()

    # 1. District capacity (realistic demand > capacity for high-priority districts)
    for d in DISTRICTS:
        # Mumbai highest demand, Nagpur/Pune high, Nashik medium
        base = {"MH-MUM": (1800, 1200), "MH-PUN": (1500, 1100), "MH-NAG": (1200, 900), "MH-NSK": (800, 750)}[d["district_id"]]
        demand, capacity = base
        # Add small jitter
        demand = int(demand * random.uniform(0.95, 1.05))
        capacity = int(capacity * random.uniform(0.95, 1.05))
        cur.execute("""INSERT INTO district_capacity
          (district_id, state, district, population_category, major_sectors, training_centres, annual_training_capacity, estimated_training_demand, priority_level, source, source_url, data_date, data_type, is_synthetic)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (d["district_id"], d["state"], d["district"], d["pop"], d["sectors"], str(random.randint(8, 18)),
           capacity, demand, d["priority"], "Synthetic (demo)", "synthetic://kaushora/demo", today.isoformat(), "synthetic", 1))

    # 2. Training centres
    for cid, name, did, city, course_ids, cap, enroll, trainers in CENTRES:
        district = next(x["district"] for x in DISTRICTS if x["district_id"] == did)
        cur.execute("""INSERT INTO training_centres
          (centre_id, centre_name, state, district, city, course_ids, annual_capacity, current_enrollment, trainer_count, equipment_status, source, source_url, data_date, data_type, is_synthetic)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (cid, name, "Maharashtra", district, city, course_ids, cap, enroll, trainers,
           random.choice(["Adequate", "Adequate", "Needs upgrade"]), "Synthetic (demo)", "synthetic://kaushora/demo", today.isoformat(), "synthetic", 1))

    # 3. Job postings - 180 postings over last 10 months for time-series
    job_titles = {
        "IT-ITeS": ["Junior Software Developer", "Database Administrator", "IT Support Technician", "Data Entry Operator"],
        "Healthcare": ["General Duty Assistant", "Patient Care Attendant", "Nursing Assistant"],
        "Finance & Accounting": ["Accountant", "Finance Assistant"]
    }
    sectors = ["IT-ITeS", "IT-ITeS", "IT-ITeS", "Healthcare", "Finance & Accounting"]  # weighted

    for i in range(180):
        sector = random.choice(sectors)
        title = random.choice(job_titles[sector])
        d = random.choice(DISTRICTS)
        # Posting date: last 300 days
        delta = random.randint(0, 300)
        pdate = (today - timedelta(days=delta)).isoformat()
        # Pick 1-2 skills, weighted
        n_skills = random.choice([1, 1, 1, 2])
        picks = random.choices(skill_ids, weights=[weights.get(s,1) for s in skill_ids], k=n_skills)
        # Deduplicate but keep at least 1
        picks = list(dict.fromkeys(picks))[:n_skills]
        # Ensure at least one skill relevant to sector
        # Salary and exp plausible
        exp_min = random.choice([0, 0, 1, 2])
        exp_max = exp_min + random.choice([1, 2, 3])
        sal_min = {"IT-ITeS": 25000, "Healthcare": 18000, "Finance & Accounting": 22000}[sector] + random.randint(-3000, 5000)
        sal_max = sal_min + random.randint(5000, 15000)
        cur.execute("""INSERT INTO job_postings
          (id, job_title, sector, industry, state, district, city, posting_date, exp_min, exp_max, employment_type, salary_min, salary_max, qualification, skill_ids, source_type, source, source_url, data_date, data_type, is_synthetic)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (f"JP-SYN-{i+1:04d}", title, sector, sector, "Maharashtra", d["district"], d["district"],
           pdate, exp_min, exp_max, random.choice(["Full-time", "Full-time", "Contract"]),
           sal_min, sal_max, random.choice(["NSQF Level 3", "NSQF Level 4", "Bachelor's degree"]),
           ",".join(picks), "synthetic", "Synthetic (demo)", "synthetic://kaushora/demo", today.isoformat(), "synthetic", 1))

    # 4. Placements - for each course x district, 2 years
    for course in courses:
        for d in DISTRICTS:
            for year in [2023, 2024]:
                trained = random.randint(60, 180)
                certified = int(trained * random.uniform(0.85, 0.95))
                placed = int(certified * random.uniform(0.65, 0.88))
                rate = round(placed / trained * 100, 1)
                salary = random.randint(18000, 35000) + (5000 if course["sector"] == "IT-ITeS" else 0)
                cur.execute("""INSERT INTO placements
                  (placement_id, course_id, district_id, training_year, trained, certified, placed, placement_rate, median_salary, satisfaction, data_date, source, data_type, is_synthetic)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (f"PL-{course['id']}-{d['district_id']}-{year}", course["id"], d["district_id"], year,
                   trained, certified, placed, rate, salary, round(random.uniform(3.8, 4.6), 1),
                   f"{year}-12-31", "Synthetic (demo)", "synthetic", 1))

    # 5. Employer surveys (synthetic) - 24 records
    employers = ["TechNova Solutions", "HealthFirst Hospitals", "FinEdge Analytics", "DataCore Systems", "Nagpur Manufacturing Co", "Pune AutoTech", "Mumbai Finance Hub", "Nashik Agro Industries"]
    for i in range(24):
        emp = random.choice(employers)
        skill = random.choice(skills)
        # Weight importance and hiring demand by skill weight
        w = weights.get(skill["id"], 1)
        imp = min(5, max(3, int(random.gauss(3.5 + w*0.2, 0.8))))
        demand = max(1, int(random.gauss(3 + w, 1.2)))
        cur.execute("""INSERT INTO employer_surveys
          (employer_name, industry, state, district, job_role, skill_id, skill_name, importance, required_proficiency, hiring_demand, difficulty, source, data_type, is_synthetic)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (emp, skill["sector"], "Maharashtra", random.choice(DISTRICTS)["district"],
           random.choice(["Software Developer", "Data Entry Operator", "General Duty Assistant", "Accountant"]),
           skill["id"], skill["skill_name"], imp, random.choice(["Intermediate", "Intermediate", "Advanced"]), demand,
           random.choice(["Medium", "Hard", "Easy"]), "synthetic", "synthetic", 1))

    # Update dataset_meta to reflect synthetic addition
    cur.execute("INSERT OR REPLACE INTO dataset_meta VALUES (?,?,?,?)",
                ("synthetic_jobs", "Synthetic job postings generated deterministically to make dashboards functional. is_synthetic=1.", 180, "synthetic"))
    cur.execute("INSERT OR REPLACE INTO dataset_meta VALUES (?,?,?,?)",
                ("synthetic_districts", "Synthetic district capacity/training centres for 4 Maharashtra districts.", 4, "synthetic"))
    cur.execute("INSERT OR REPLACE INTO dataset_meta VALUES (?,?,?,?)",
                ("synthetic_placements", "Synthetic placement outcomes per course/district/year.", 24, "synthetic"))
    cur.execute("INSERT OR REPLACE INTO dataset_meta VALUES (?,?,?,?)",
                ("synthetic_employers", "Synthetic employer surveys (24) for demand signals.", 24, "synthetic"))

    conn.commit()
    conn.close()
    print("Synthetic seed done: 4 districts, 6 centres, 180 jobs, 24 placements, 24 employer surveys (all is_synthetic=1)")

if __name__ == "__main__":
    seed()
