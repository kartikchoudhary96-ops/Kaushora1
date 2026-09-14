"""Ingest Role Radar job postings into Kaushora DB.

Downloads 2,500 real LinkedIn job postings from HuggingFace (Apache 2.0),
maps locations to Indian states/cities, extracts skills from descriptions,
and inserts into job_postings + junction tables.

Usage:
    python scripts/ingest_job_postings.py
"""
import json, os, re, sqlite3, sys, urllib.request
from pathlib import Path

DB = os.path.join(os.path.dirname(__file__), "..", "database", "kaushora.db")
JSON_PATH = Path(os.path.expanduser("~")) / "Downloads" / "role_radar" / "scraped_jobs.json"
HF_URL = "https://huggingface.co/datasets/oksomu/role-radar-dataset/resolve/main/scraped_jobs.json"

# ── Location mapping ──────────────────────────────────────────────────────────
# Maps location substrings to (state, city) for Maharashtra and other Indian states.
LOCATION_MAP = {
    "Mumbai": ("Maharashtra", "Mumbai"),
    "Mumbai Metropolitan Region": ("Maharashtra", "Mumbai"),
    "Navi Mumbai": ("Maharashtra", "Navi Mumbai"),
    "Pune Division": ("Maharashtra", "Pune"),
    "Pune City": ("Maharashtra", "Pune"),
    "Pune District": ("Maharashtra", "Pune"),
    "Pune/Pimpri-Chinchwad": ("Maharashtra", "Pune"),
    "Pimpri Chinchwad": ("Maharashtra", "Pune"),
    "Thane": ("Maharashtra", "Thane"),
    "Kurla": ("Maharashtra", "Mumbai"),
    "Malad": ("Maharashtra", "Mumbai"),
    "Panvel": ("Maharashtra", "Navi Mumbai"),
    "Worli": ("Maharashtra", "Mumbai"),
    "Khed": ("Maharashtra", "Pune"),
    "Borivali": ("Maharashtra", "Mumbai"),
    "Bengaluru": ("Karnataka", "Bengaluru"),
    "Bengaluru East": ("Karnataka", "Bengaluru"),
    "Bangalore Urban": ("Karnataka", "Bengaluru"),
    "Hyderabad": ("Telangana", "Hyderabad"),
    "Chennai": ("Tamil Nadu", "Chennai"),
    "Ahmedabad": ("Gujarat", "Ahmedabad"),
    "Jaipur": ("Rajasthan", "Jaipur"),
    "Kolkata": ("West Bengal", "Kolkata"),
    "Greater Kolkata Area": ("West Bengal", "Kolkata"),
    "Kochi": ("Kerala", "Kochi"),
    "Noida": ("Uttar Pradesh", "Noida"),
    "Gurugram": ("Haryana", "Gurugram"),
    "Gurgaon": ("Haryana", "Gurugram"),
    "Delhi": ("Delhi", "Delhi"),
}

# ── Industry → Sector mapping ─────────────────────────────────────────────────
INDUSTRY_SECTOR = {
    "IT Services and IT Consulting": "SEC005",
    "Software Development": "SEC005",
    "Technology, Information and Internet": "SEC005",
    "Information Technology &amp; Services": "SEC005",
    "Information Technology and Engineering": "SEC005",
    "Financial Services": "SEC007",
    "Business Consulting and Services": "SEC007",
    "Professional Services": "SEC007",
    "Advertising Services": "SEC008",
    "Staffing and Recruiting": "SEC007",
    "Hospitals and Health Care": "SEC013",
    "Retail": "SEC007",
    "Transportation, Logistics, Supply Chain and Storage": "SEC006",
    "Insurance": "SEC007",
    "Pharmaceutical Manufacturing": "SEC010",
    "Real Estate": "SEC007",
    "Chemical Manufacturing": "SEC010",
    "Mechanical or Industrial Engineering": "SEC012",
    "Automotive": "SEC012",
    "Construction": "SEC004",
    "Design Services": "SEC008",
    "Media & Internet": "SEC008",
    "Telecommunications": "SEC005",
    "Mining & Metals": "SEC007",
    "Food & Beverages": "SEC007",
    "Animation & Post-production": "SEC008",
    "Consumer Goods": "SEC007",
    "Wellness and Fitness Services": "SEC003",
    "Higher Education": "SEC007",
    "Think Tanks and Non-Profits": "SEC007",
    "International Affairs": "SEC007",
    "Environmental Services": "SEC007",
    "Government Relations": "SEC007",
}

# ── Skill extraction from descriptions ────────────────────────────────────────
# Maps text patterns to skill IDs. Order matters: longer patterns first.
SKILL_PATTERNS = [
    (r"\bmachine\s+learning\b", "SKL022"),
    (r"\bdata\s+analytic", "SKL026"),
    (r"\bdata\s+science\b", "SKL026"),
    (r"\bbig\s+data\b", "SKL023"),
    (r"\bsecurity\s+manage", "SKL016"),
    (r"\bweb\s+develop", "SKL012"),
    (r"\bgraphic\s+design", "SKL013"),
    (r"\bquality\s+check", "SKL008"),
    (r"\bwarehouse\s+operat", "SKL015"),
    (r"\bdata\s+entry", "SKL011"),
    (r"\bpython\b", "SKL012"),
    (r"\bjava\b(?!script)", "SKL012"),
    (r"\bjavascript\b", "SKL012"),
    (r"\breact\b", "SKL012"),
    (r"\bangular\b", "SKL012"),
    (r"\bnode\.?js\b", "SKL012"),
    (r"\bdjango\b", "SKL012"),
    (r"\bflask\b", "SKL012"),
    (r"\bsql\b", "SKL026"),
    (r"\bexcel\b", "SKL011"),
    (r"\baws\b", "SKL022"),
    (r"\bdocker\b", "SKL012"),
    (r"\bkubernetes\b", "SKL012"),
    (r"\bhtml\b", "SKL012"),
    (r"\bcss\b", "SKL012"),
    (r"\bgit\b", "SKL012"),
    (r"\blinux\b", "SKL012"),
    (r"\bc\+\+\b", "SKL012"),
    (r"\bc#\b", "SKL012"),
    (r"\bruby\b", "SKL012"),
    (r"\bphp\b", "SKL012"),
    (r"\bswift\b", "SKL012"),
    (r"\btableau\b", "SKL026"),
    (r"\bpower\s*bi\b", "SKL026"),
    (r"\btensorflow\b", "SKL022"),
    (r"\bpytorch\b", "SKL022"),
    (r"\bspark\b", "SKL023"),
    (r"\bhadoop\b", "SKL023"),
    (r"\bcommunication\b", "SKL001"),
    (r"\bleadership\b", "SKL021"),
    (r"\banalytical\b", "SKL021"),
    (r"\bcritical\s+think", "SKL025"),
    (r"\bproject\s+manage", "SKL021"),
    (r"\bagile\b", "SKL021"),
    (r"\bscrum\b", "SKL021"),
    (r"\bsales\b", "SKL001"),
    (r"\bmarketing\b", "SKL001"),
    (r"\brecruitment\b", "SKL001"),
    (r"\bcustomer\s+service\b", "SKL001"),
    (r"\bteam\s+manage", "SKL021"),
    (r"\bproblem\s+solv", "SKL021"),
]


def ensure_json():
    """Download Role Radar JSON if not cached locally."""
    if JSON_PATH.exists():
        print(f"Using cached: {JSON_PATH}")
    else:
        print(f"Downloading from {HF_URL} ...")
        req = urllib.request.Request(HF_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        JSON_PATH.write_bytes(data)
        print(f"Saved {len(data)} bytes to {JSON_PATH}")


def parse_location(loc_str):
    """Extract state, city from a LinkedIn location string."""
    if not loc_str:
        return "Unknown", "Unknown", "Unknown"
    # Try known mappings first
    for key, (state, city) in LOCATION_MAP.items():
        if key.lower() in loc_str.lower():
            return state, city, state
    # Fallback: split by comma
    parts = [p.strip() for p in loc_str.split(",")]
    if len(parts) >= 2:
        city = parts[0]
        state = parts[1]
        return state, city, state
    elif len(parts) == 1:
        return "Unknown", parts[0], "Unknown"
    return "Unknown", "Unknown", "Unknown"


def extract_skills(text):
    """Extract skill IDs from text using regex patterns."""
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for pattern, skill_id in SKILL_PATTERNS:
        if re.search(pattern, text_lower):
            found.add(skill_id)
    return sorted(found)


def map_employment_type(et):
    """Map LinkedIn employment_type to our schema."""
    if not et:
        return None
    mapping = {
        "Full-time": "Full-time",
        "Part-time": "Part-time",
        "Contract": "Contract",
        "Internship": "Internship",
        "Temporary": "Contract",
        "Volunteer": "Other",
        "Other": "Other",
    }
    return mapping.get(et, et)


def parse_date(date_str):
    """Parse scraped_at date string."""
    if not date_str or date_str == "None":
        return None
    return date_str[:10]  # YYYY-MM-DD


def ingest():
    ensure_json()

    with open(JSON_PATH, encoding="utf-8") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} records from Role Radar")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Get existing skill IDs for validation
    existing_skills = {r[0] for r in c.execute("SELECT id FROM skills").fetchall()}
    existing_roles = {r[0] for r in c.execute("SELECT role_id FROM job_roles").fetchall()}

    inserted = 0
    skipped = 0
    skill_links = 0
    occupation_links = 0
    skills_extracted = Counter()
    states_found = Counter()
    industries_found = Counter()

    for rec in records:
        job_id = rec.get("id", "")
        if not job_id:
            skipped += 1
            continue

        title = rec.get("title", "")
        company = rec.get("company", "")
        loc = rec.get("location") or ""
        desc = rec.get("description") or ""
        seniority = rec.get("seniority_level") or ""
        emp_type = rec.get("employment_type") or ""
        job_func = rec.get("job_function") or ""
        industry = rec.get("industry") or ""
        url = rec.get("url") or ""
        scraped = rec.get("scraped_at") or ""
        role_hint = rec.get("role_family_hint") or ""
        remote = 1 if rec.get("remote_hint") else 0

        # Parse location
        state, city, district = parse_location(loc)

        # Map industry → sector
        sector = INDUSTRY_SECTOR.get(industry, "SEC007")  # default to Management

        # Extract skills from description + title
        combined_text = f"{title} {desc}"
        skill_ids = extract_skills(combined_text)
        skill_ids_str = ",".join(skill_ids) if skill_ids else None

        # Map employment type
        emp_typeMapped = map_employment_type(emp_type)

        # Parse date
        data_date = parse_date(scraped)

        try:
            c.execute("""INSERT OR IGNORE INTO job_postings
                (id, job_title, sector, industry, state, district, city,
                 posting_date, exp_min, exp_max, employment_type,
                 salary_min, salary_max, qualification, skill_ids,
                 source_type, source, source_url, data_date, data_type,
                 is_synthetic, employer_name, occupation, remote_flag,
                 scraped_at, publication_year, data_period, geography_level,
                 observed_or_derived, confidence, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (job_id, title, sector, industry, state, district, city,
                 None, None, None, emp_typeMapped,
                 None, None, None, skill_ids_str,
                 "linkedin", "Role Radar (HuggingFace)", url,
                 data_date, "observed",
                 0, company, role_hint, remote,
                 data_date, 2026, "2026-05", "city",
                 "observed", "high",
                 f"Seniority: {seniority}. Job function: {job_func}"))

            if c.rowcount > 0:
                inserted += 1
                states_found[state] += 1
                industries_found[industry] += 1

                # Insert skill links into junction table
                for sid in skill_ids:
                    if sid in existing_skills:
                        try:
                            c.execute("INSERT OR IGNORE INTO job_posting_skills (job_id, skill_id, confidence) VALUES (?,?,?)",
                                      (job_id, sid, "extracted"))
                            skill_links += 1
                        except sqlite3.IntegrityError:
                            pass
                        skills_extracted[sid] += 1

                # Try to match occupation from role_family_hint
                role_matches = {
                    "fullstack": "OCC015",
                    "backend": "OCC015",
                    "frontend": "OCC015",
                    "mobile": "OCC015",
                    "data": "OCC014",
                    "hr": "OCC020",
                    "sales": "OCC017",
                    "marketing": "OCC016",
                    "finance": "OCC014",
                    "operations": "OCC019",
                    "product": "OCC015",
                    "devops": "OCC015",
                    "customer_success": "OCC017",
                    "legal": "OCC020",
                    "non-tech": "OCC020",
                }
                occ_id = role_matches.get(role_hint)
                if occ_id and occ_id in existing_roles:
                    try:
                        c.execute("INSERT OR IGNORE INTO job_posting_occupations (job_id, occupation_id) VALUES (?,?)",
                                  (job_id, occ_id))
                        occupation_links += 1
                    except sqlite3.IntegrityError:
                        pass
            else:
                skipped += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\n=== Ingestion Complete ===")
    print(f"Inserted: {inserted}")
    print(f"Skipped (duplicates/errors): {skipped}")
    print(f"Skill junction links: {skill_links}")
    print(f"Occupation junction links: {occupation_links}")
    print(f"\nTop skills extracted:")
    for sid, cnt in skills_extracted.most_common(10):
        print(f"  {sid}: {cnt}")
    print(f"\nTop states:")
    for st, cnt in states_found.most_common(10):
        print(f"  {st}: {cnt}")
    print(f"\nTop industries:")
    for ind, cnt in industries_found.most_common(10):
        print(f"  {ind}: {cnt}")


from collections import Counter

if __name__ == "__main__":
    ingest()
