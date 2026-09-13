#!/usr/bin/env python3
"""
Kaushora Real Data Ingestion — New Research Package
=====================================================
Integrates 12 new CSV files from Downloads into the existing Kaushora database.
Idempotent: safe to re-run. Uses UPSERT (INSERT OR REPLACE) for all records.

Datasets ingested:
  1. source_registry   -> sources (2 new, update 10 existing)
  2. skills            -> skills (7 new SKL021-027) + skill_aliases (SK001-SK007)
  3. skill_demand      -> skill_demand (7 real demand signals replacing 1 unavailable)
  4. placements        -> placements (5 PMKVY/AMBER records)
  5. district_skill_gaps -> district_skill_gaps (5 state-level sector gaps)
  6. evidence_registry -> evidence_metrics (14 citable evidence rows)
  7. labour_trends     -> trends (6 trend signals)
  8. employer_evidence -> employer_evidence (5 survey findings, NEW TABLE)
  9. nos_qp_mapping    -> qualifications (1 QP record)
  10. courses          -> courses (14 DVET/SIDH courses, merged with existing)
  11. district_registry -> districts (36 MH districts, adds historical_names)
  12. occupation       -> job_roles (1 CNC Operator from NCO 2015)

Usage:
  python scripts/ingest_new_research_data.py

Requirements:
  - database/kaushora.db must exist (run init_db.py + import_csv_data.py first)
  - Download CSVs in user Downloads folder
"""
import csv
import os
import sqlite3
import sys
from pathlib import Path

DOWNLOADS = Path(os.path.expanduser("~")) / "Downloads"
DB_PATH = Path(__file__).resolve().parent.parent / "database" / "kaushora.db"

# File mapping: (filename_fragment, description)
FILES = {
    "3c4ba7": "source_registry",
    "65fae1": "skills",
    "5b84c2": "skill_demand",
    "9a6722": "placements",
    "ea16e9": "district_skill_gaps",
    "1ae3e8": "evidence_registry",
    "6d59e4": "labour_trends",
    "53b38f": "employer_evidence",
    "54ea34": "nos_qp_mapping",
    "8e1ade": "courses",
    "e75914": "district_registry",
    "327548": "occupation",
}


def find_file(fragment):
    """Find the Download CSV file by filename fragment."""
    for f in DOWNLOADS.iterdir():
        if f.is_file() and fragment in f.name and f.suffix.lower() in (".txt", ".csv"):
            return f
    return None


def read_csv(fragment):
    """Read a CSV file and return (headers, rows)."""
    path = find_file(fragment)
    if not path:
        print(f"  ERROR: File not found for fragment '{fragment}'")
        return None, []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def safe_str(v):
    """Convert to clean string, None if empty."""
    if v is None:
        return None
    v = str(v).strip()
    return v if v else None


def safe_int(v):
    """Convert to int or None."""
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return int(float(v))
    except (ValueError, OverflowError):
        return None


def safe_float(v):
    """Convert to float or None."""
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return float(v)
    except (ValueError, OverflowError):
        return None


# ─────────────────────────────────────────────────────────────
# 1. SOURCES (source_registry -> sources)
# ─────────────────────────────────────────────────────────────
def ingest_sources(conn):
    print("\n[1/12] Ingesting source_registry -> sources ...")
    headers, rows = read_csv("3c4ba7")
    if not rows:
        return 0
    cur = conn.cursor()
    count = 0
    for r in rows:
        sid = safe_str(r.get("source_id"))
        if not sid:
            continue
        cur.execute("""INSERT OR REPLACE INTO sources
            (source_id, source_name, organization, dataset_name, source_url,
             publication_date, retrieval_date, geographic_coverage, data_type,
             license_or_usage_note, source_status, data_source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid,
             safe_str(r.get("source_name")),
             safe_str(r.get("organization")),
             safe_str(r.get("dataset_or_report")),
             safe_str(r.get("url")),
             safe_str(r.get("publication_year")),
             safe_str(r.get("retrieved_date")),
             safe_str(r.get("geography")) or safe_str(r.get("coverage")),
             safe_str(r.get("source_type")),
             safe_str(r.get("license_or_access_note")),
             "active",
             "REAL"))
        count += 1
    conn.commit()
    print(f"  -> {count} sources upserted")
    return count


# ─────────────────────────────────────────────────────────────
# 2. SKILLS (skills -> skills + skill_aliases)
# ─────────────────────────────────────────────────────────────
def ingest_skills(conn):
    print("\n[2/12] Ingesting skills -> skills + skill_aliases ...")
    headers, rows = read_csv("65fae1")
    if not rows:
        return 0
    cur = conn.cursor()
    # Find max existing SKL ID
    max_id = cur.execute("SELECT MAX(CAST(SUBSTR(id,4) AS INTEGER)) FROM skills WHERE id LIKE 'SKL%'").fetchone()[0] or 20
    count = 0
    alias_count = 0
    for r in rows:
        new_id = safe_str(r.get("skill_id"))  # SK001-SK007
        if not new_id:
            continue
        max_id += 1
        skl_id = f"SKL{max_id:03d}"
        skill_name = safe_str(r.get("skill_name"))
        sector = safe_str(r.get("sector"))
        skill_type = safe_str(r.get("skill_type"))
        source = safe_str(r.get("source"))
        source_url = safe_str(r.get("source_url"))
        source_doc = safe_str(r.get("source_document"))

        # Skip if skill name already exists
        existing = cur.execute("SELECT id FROM skills WHERE skill_name=?", (skill_name,)).fetchone()
        if existing:
            # Add alias pointing to existing
            cur.execute("INSERT OR IGNORE INTO skill_aliases (alias, skill_id) VALUES (?,?)",
                        (new_id, existing[0]))
            alias_count += 1
            continue

        cur.execute("""INSERT OR REPLACE INTO skills
            (id, skill_name, normalized_skill_name, skill_category, sector,
             source, source_url, source_title, is_synthetic, data_source)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (skl_id, skill_name, skill_name.lower(), skill_type, sector,
             source, source_url, source_doc, 0, "REAL"))
        # Add alias
        cur.execute("INSERT OR IGNORE INTO skill_aliases (alias, skill_id) VALUES (?,?)",
                    (new_id, skl_id))
        count += 1
        alias_count += 1
    conn.commit()
    print(f"  -> {count} new skills added, {alias_count} aliases created")
    return count


# ─────────────────────────────────────────────────────────────
# 3. SKILL DEMAND (skill_demand -> skill_demand)
# ─────────────────────────────────────────────────────────────
def ingest_skill_demand(conn):
    print("\n[3/12] Ingesting skill_demand -> skill_demand ...")
    headers, rows = read_csv("5b84c2")
    if not rows:
        return 0
    cur = conn.cursor()
    # Remove old unavailable row
    cur.execute("DELETE FROM skill_demand WHERE demand_status='Unavailable'")
    count = 0
    for r in rows:
        sd_id = safe_str(r.get("skill_id"))  # SD001-SD007
        skill_name = safe_str(r.get("skill_name"))
        if not sd_id or not skill_name:
            continue
        # Resolve skill_id via alias or name
        skill_row = cur.execute(
            "SELECT s.id FROM skills s LEFT JOIN skill_aliases a ON s.id=a.skill_id "
            "WHERE a.alias=? OR s.skill_name=? OR s.id=? LIMIT 1",
            (sd_id, skill_name, sd_id)).fetchone()
        skill_db_id = skill_row[0] if skill_row else None

        demand_level = safe_str(r.get("demand_level"))
        demand_signal = safe_str(r.get("demand_signal"))
        geography = safe_str(r.get("location"))
        year = safe_str(r.get("year"))
        source = safe_str(r.get("source"))
        source_url = safe_str(r.get("source_url"))
        source_doc = safe_str(r.get("source_document"))
        confidence = safe_str(r.get("confidence"))

        # Deterministic score from demand_level
        demand_score = None
        if demand_level:
            dl = demand_level.lower()
            if dl == "high":
                demand_score = 85.0
            elif dl == "medium":
                demand_score = 60.0
            elif dl == "low":
                demand_score = 30.0

        cur.execute("""INSERT OR REPLACE INTO skill_demand
            (skill_demand_id, skill_id, geography, time_period,
             employment_signal, demand_score, demand_status, calculation_method,
             source_ids, is_derived, data_source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (sd_id, skill_db_id, geography, year,
             demand_signal, demand_score,
             f"Observed: {demand_level}" if demand_level else "Insufficient data",
             "Observed demand signal from source report",
             source, 0, "REAL"))
        count += 1
    conn.commit()
    print(f"  -> {count} skill demand records imported")
    return count


# ─────────────────────────────────────────────────────────────
# 4. PLACEMENTS (placements -> placements)
# ─────────────────────────────────────────────────────────────
def ingest_placements(conn):
    print("\n[4/12] Ingesting placements -> placements ...")
    headers, rows = read_csv("9a6722")
    if not rows:
        return 0
    cur = conn.cursor()
    count = 0
    for r in rows:
        pid = safe_str(r.get("placement_id"))
        if not pid:
            continue
        programme = safe_str(r.get("programme"))
        state = safe_str(r.get("state"))
        trained = safe_int(r.get("candidates_trained"))
        placed = safe_int(r.get("candidates_placed"))
        rate = safe_float(r.get("placement_rate"))
        sector = safe_str(r.get("sector"))
        course = safe_str(r.get("course"))
        year = safe_str(r.get("year"))
        source = safe_str(r.get("source"))
        source_url = safe_str(r.get("source_url"))
        source_doc = safe_str(r.get("source_document"))
        agg = safe_str(r.get("aggregation_level"))
        notes = safe_str(r.get("notes"))

        # Map to existing schema
        # course_id: try to find matching course
        course_id = None
        if course:
            course_row = cur.execute("SELECT id FROM courses WHERE course_name LIKE ?", (f"%{course}%",)).fetchone()
            if course_row:
                course_id = course_row[0]

        # district_id: state-level -> NULL
        district_id = None

        cur.execute("""INSERT OR REPLACE INTO placements
            (placement_id, course_id, district_id, training_year,
             trained, certified, placed, placement_rate,
             median_salary, satisfaction, data_date, source, data_type,
             is_synthetic)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, course_id, district_id, None,
             trained, None, placed, rate,
             None, None, year, source, "observed", 0))
        count += 1
    conn.commit()
    print(f"  -> {count} placement records imported")
    return count


# ─────────────────────────────────────────────────────────────
# 5. DISTRICT SKILL GAPS (district_skill_gaps -> district_skill_gaps)
# ─────────────────────────────────────────────────────────────
def ingest_district_skill_gaps(conn):
    print("\n[5/12] Ingesting district_skill_gaps -> district_skill_gaps ...")
    headers, rows = read_csv("ea16e9")
    if not rows:
        return 0
    cur = conn.cursor()
    # Remove old unavailable row
    cur.execute("DELETE FROM district_skill_gaps WHERE gap_status='Unavailable'")
    count = 0
    for r in rows:
        gap_id = safe_str(r.get("gap_id"))
        if not gap_id:
            continue
        district_name = safe_str(r.get("district_name"))
        sector = safe_str(r.get("sector"))
        gap_type = safe_str(r.get("gap_type"))
        demand_signal = safe_str(r.get("demand_signal"))
        source = safe_str(r.get("source"))
        source_url = safe_str(r.get("source_url"))
        source_doc = safe_str(r.get("source_document"))
        year = safe_str(r.get("data_year"))

        # These are STATE-level gaps (district_name = "Maharashtra")
        # No district_id or skill_id — they are sector-level observations
        cur.execute("""INSERT OR REPLACE INTO district_skill_gaps
            (gap_id, district_id, skill_id, demand_signal,
             training_supply_signal, gap_score, gap_status,
             evidence_sources, calculation_method, is_derived, data_source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (gap_id, None, None, demand_signal,
             None, None, f"Observed: {demand_signal} gap in {sector}" if demand_signal else "Insufficient data",
             f"{source}: {source_doc}" if source_doc else source,
             f"Observed sector-level gap ({year})", 0, "REAL"))
        count += 1
    conn.commit()
    print(f"  -> {count} district skill gap records imported")
    return count


# ─────────────────────────────────────────────────────────────
# 6. EVIDENCE REGISTRY (evidence_registry -> evidence_metrics)
# ─────────────────────────────────────────────────────────────
def ingest_evidence(conn):
    print("\n[6/12] Ingesting evidence_registry -> evidence_metrics ...")
    headers, rows = read_csv("1ae3e8")
    if not rows:
        return 0
    cur = conn.cursor()
    count = 0
    for r in rows:
        eid = safe_str(r.get("evidence_id"))
        if not eid:
            continue
        source_id = safe_str(r.get("source_id"))
        claim = safe_str(r.get("claim_or_measure"))
        orig_val = safe_str(r.get("original_value"))
        orig_unit = safe_str(r.get("original_unit"))
        orig_geo = safe_str(r.get("original_geography"))
        orig_year = safe_str(r.get("original_year"))
        derived = safe_str(r.get("derived_or_observed"))
        confidence = safe_str(r.get("confidence"))
        notes = safe_str(r.get("notes"))

        # Parse numeric value
        metric_numeric = None
        if orig_val:
            try:
                metric_numeric = float(orig_val)
            except (ValueError, TypeError):
                pass

        cur.execute("""INSERT OR REPLACE INTO evidence_metrics
            (evidence_id, metric_name, metric_value, metric_numeric, unit,
             geography, time_period, source_id, source_reference,
             calculation_method, is_observed, is_derived, confidence_level,
             notes, data_source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, claim, orig_val, metric_numeric, orig_unit,
             orig_geo, orig_year, source_id,
             derived,
             f"Original value from source ({derived})" if derived else None,
             1 if derived == "observed" else 0,
             1 if derived == "derived" else 0,
             confidence, notes, "REAL"))
        count += 1
    conn.commit()
    print(f"  -> {count} evidence metrics imported")
    return count


# ─────────────────────────────────────────────────────────────
# 7. LABOUR TRENDS (labour_trends -> trends)
# ─────────────────────────────────────────────────────────────
def ingest_trends(conn):
    print("\n[7/12] Ingesting labour_trends -> trends ...")
    headers, rows = read_csv("6d59e4")
    if not rows:
        return 0
    cur = conn.cursor()
    count = 0
    for r in rows:
        tid = safe_str(r.get("trend_id"))
        if not tid:
            continue
        # Check if trend already exists
        existing = cur.execute("SELECT trend_id FROM trends WHERE trend_id=?", (tid,)).fetchone()
        if existing:
            # Update existing
            cur.execute("""UPDATE trends SET
                technology=?, sector=?, trend_description=?, evidence=?,
                trend_direction=?, period=?, source=?, source_url=?, source_title=?
                WHERE trend_id=?""",
                (safe_str(r.get("technology")),
                 safe_str(r.get("sector")),
                 safe_str(r.get("trend_name")),
                 f"{safe_str(r.get('india_relevance',''))}; {safe_str(r.get('maharashtra_relevance',''))}",
                 safe_str(r.get("trend_direction")),
                 safe_str(r.get("time_horizon")),
                 safe_str(r.get("source")),
                 safe_str(r.get("source_url")),
                 safe_str(r.get("source_document")),
                 tid))
        else:
            cur.execute("""INSERT INTO trends
                (trend_id, technology, sector, trend_description, evidence,
                 trend_direction, period, source, source_url, source_title,
                 data_type, is_synthetic)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid,
                 safe_str(r.get("technology")),
                 safe_str(r.get("sector")),
                 safe_str(r.get("trend_name")),
                 f"{safe_str(r.get('india_relevance',''))}; {safe_str(r.get('maharashtra_relevance',''))}",
                 safe_str(r.get("trend_direction")),
                 safe_str(r.get("time_horizon")),
                 safe_str(r.get("source")),
                 safe_str(r.get("source_url")),
                 safe_str(r.get("source_document")),
                 "official_report", 0))
        count += 1
    conn.commit()
    print(f"  -> {count} trend records imported/updated")
    return count


# ─────────────────────────────────────────────────────────────
# 8. EMPLOYER EVIDENCE (employer_evidence -> employer_evidence, NEW TABLE)
# ─────────────────────────────────────────────────────────────
def ingest_employer_evidence(conn):
    print("\n[8/12] Ingesting employer_evidence -> employer_evidence (new table) ...")
    headers, rows = read_csv("53b38f")
    if not rows:
        return 0
    cur = conn.cursor()
    # Create table if not exists
    cur.execute("""CREATE TABLE IF NOT EXISTS employer_evidence (
        survey_id TEXT PRIMARY KEY,
        sector TEXT,
        industry TEXT,
        employer_group TEXT,
        skill TEXT,
        occupation TEXT,
        finding TEXT,
        demand_signal TEXT,
        year TEXT,
        sample_size INTEGER,
        location TEXT,
        source TEXT,
        source_url TEXT,
        source_document TEXT,
        page_or_section TEXT,
        provenance TEXT DEFAULT 'observed',
        data_source TEXT DEFAULT 'REAL'
    )""")
    count = 0
    for r in rows:
        sid = safe_str(r.get("survey_id"))
        if not sid:
            continue
        cur.execute("""INSERT OR REPLACE INTO employer_evidence
            (survey_id, sector, industry, employer_group, skill, occupation,
             finding, demand_signal, year, sample_size, location,
             source, source_url, source_document, page_or_section,
             provenance, data_source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid,
             safe_str(r.get("sector")),
             safe_str(r.get("industry")),
             safe_str(r.get("employer_group")),
             safe_str(r.get("skill")),
             safe_str(r.get("occupation")),
             safe_str(r.get("finding")),
             safe_str(r.get("demand_signal")),
             safe_str(r.get("year")),
             safe_int(r.get("sample_size")),
             safe_str(r.get("location")),
             safe_str(r.get("source")),
             safe_str(r.get("source_url")),
             safe_str(r.get("source_document")),
             safe_str(r.get("page_or_section")),
             safe_str(r.get("provenance")) or "observed",
             "REAL"))
        count += 1
    conn.commit()
    print(f"  -> {count} employer evidence records imported")
    return count


# ─────────────────────────────────────────────────────────────
# 9. NOS-QP MAPPING (nos_qp_mapping -> qualifications)
# ─────────────────────────────────────────────────────────────
def ingest_nos_qp(conn):
    print("\n[9/12] Ingesting nos_qp_mapping -> qualifications ...")
    headers, rows = read_csv("54ea34")
    if not rows:
        return 0
    cur = conn.cursor()
    count = 0
    for r in rows:
        qp_code = safe_str(r.get("qp_code"))
        if not qp_code:
            continue
        # Check if qualification already exists
        existing = cur.execute("SELECT qualification_id FROM qualifications WHERE qp_code=?", (qp_code,)).fetchone()
        if existing:
            continue
        qp_name = safe_str(r.get("qp_name"))
        nos_code = safe_str(r.get("nos_code"))
        sector = safe_str(r.get("sector"))
        nsqf = safe_str(r.get("nsqf_level"))
        source = safe_str(r.get("source"))
        source_url = safe_str(r.get("source_url"))

        # Generate qualification ID
        qid = f"QPL{count+1:03d}"
        cur.execute("""INSERT OR REPLACE INTO qualifications
            (qualification_id, qualification_name, qp_code, occupation_id,
             nsqf_level, qualification_status, source_id, data_source)
            VALUES (?,?,?,?,?,?,?,?)""",
            (qid, qp_name, qp_code, None,
             nsqf, "Active", source, "REAL"))
        count += 1
    conn.commit()
    print(f"  -> {count} qualification records imported")
    return count


# ─────────────────────────────────────────────────────────────
# 10. COURSES (courses -> courses, merge with existing)
# ─────────────────────────────────────────────────────────────
def ingest_courses(conn):
    print("\n[10/12] Ingesting courses -> courses (merge) ...")
    headers, rows = read_csv("8e1ade")
    if not rows:
        return 0
    cur = conn.cursor()
    count = 0
    updated = 0
    for r in rows:
        cid = safe_str(r.get("course_id"))
        if not cid:
            continue
        course_name = safe_str(r.get("course_name"))
        if not course_name:
            continue
        sector = safe_str(r.get("sector"))
        nsqf = safe_str(r.get("nsqf_level"))
        duration = safe_str(r.get("duration"))
        delivery = safe_str(r.get("delivery_mode"))
        source = safe_str(r.get("source"))
        source_url = safe_str(r.get("source_url"))
        source_doc = safe_str(r.get("source_document"))
        year = safe_str(r.get("data_year"))
        qualification_code = safe_str(r.get("qualification_code"))
        qp_code = safe_str(r.get("qp_code"))
        skill_id = safe_str(r.get("skill_id"))
        skill_name = safe_str(r.get("skill_name"))
        nos_code = safe_str(r.get("nos_code"))

        # Check if course already exists
        existing = cur.execute("SELECT id FROM courses WHERE course_name=?", (course_name,)).fetchone()
        if existing:
            # Update existing with richer data if available
            cur.execute("""UPDATE courses SET
                sector=COALESCE(?,sector), nsqf_level=COALESCE(?,nsqf_level),
                duration=COALESCE(?,duration), delivery_mode=COALESCE(?,delivery_mode),
                source=COALESCE(?,source), source_url=COALESCE(?,source_url),
                source_title=COALESCE(?,source_title)
                WHERE id=?""",
                (sector, nsqf, duration, delivery, source, source_url, source_doc, existing[0]))
            updated += 1
            # Store skill mapping if available
            if skill_id and skill_name:
                # Resolve skill via alias
                sk = cur.execute(
                    "SELECT s.id FROM skills s LEFT JOIN skill_aliases a ON s.id=a.skill_id "
                    "WHERE a.alias=? OR s.skill_name=? OR s.id=? LIMIT 1",
                    (skill_id, skill_name, skill_id)).fetchone()
                if sk:
                    cur.execute("INSERT OR IGNORE INTO course_skills (course_id, skill_id, source, data_type, is_synthetic) VALUES (?,?,?,?)",
                                (existing[0], sk[0], source, "observed", 0))
            continue

        # Insert new course
        cur.execute("""INSERT OR REPLACE INTO courses
            (id, course_name, sector, qualification_level, duration,
             delivery_mode, provider, source, source_url, source_title,
             publication_date, is_synthetic, course_code, sector_id,
             nsqf_level, source_id, data_source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, course_name, sector, None, duration,
             delivery, source, source, source_url, source_doc,
             year, 0, qp_code or qualification_code, None,
             nsqf, None, "REAL"))
        count += 1

        # Store skill mapping if available
        if skill_id and skill_name:
            sk = cur.execute(
                "SELECT s.id FROM skills s LEFT JOIN skill_aliases a ON s.id=a.skill_id "
                "WHERE a.alias=? OR s.skill_name=? OR s.id=? LIMIT 1",
                (skill_id, skill_name, skill_id)).fetchone()
            if sk:
                cur.execute("INSERT OR IGNORE INTO course_skills (course_id, skill_id, source, data_type, is_synthetic) VALUES (?,?,?,?,?)",
                            (cid, sk[0], source, "observed", 0))

    conn.commit()
    print(f"  -> {count} new courses added, {updated} existing courses updated")
    return count


# ─────────────────────────────────────────────────────────────
# 11. DISTRICT REGISTRY (district_registry -> districts)
# ─────────────────────────────────────────────────────────────
def ingest_districts(conn):
    print("\n[11/12] Ingesting district_registry -> districts (enrich historical_names) ...")
    headers, rows = read_csv("e75914")
    if not rows:
        return 0
    cur = conn.cursor()

    # Add historical_names column if not exists
    try:
        cur.execute("ALTER TABLE districts ADD COLUMN historical_names TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    count = 0
    matched = 0
    for r in rows:
        district_name = safe_str(r.get("district_name"))
        historical = safe_str(r.get("historical_names"))
        if not district_name:
            continue

        # Try to match by name (fuzzy: with/without parentheses)
        clean_name = district_name.replace(" (", " (").replace(") ", ")")
        existing = cur.execute(
            "SELECT district_id FROM districts WHERE district_name LIKE ?",
            (f"%{district_name}%",)).fetchone()

        if not existing:
            # Try historical name
            if historical:
                existing = cur.execute(
                    "SELECT district_id FROM districts WHERE district_name LIKE ? OR historical_names LIKE ?",
                    (f"%{historical}%", f"%{historical}%")).fetchone()

        if existing:
            cur.execute("UPDATE districts SET historical_names=? WHERE district_id=?",
                        (historical, existing[0]))
            matched += 1
        else:
            # Insert new district record
            code = safe_str(r.get("district_code"))
            cur.execute("""INSERT OR REPLACE INTO districts
                (district_id, district_code, district_name, state_id, state_name,
                 source_id, data_source, historical_names)
                VALUES (?,?,?,?,?,?,?,?)""",
                (code or f"DT{count+1:03d}", code, district_name, "ST001", "Maharashtra",
                 None, "REAL", historical))
        count += 1
    conn.commit()
    print(f"  -> {count} districts processed, {matched} enriched with historical names")
    return count


# ─────────────────────────────────────────────────────────────
# 12. OCCUPATION (occupation -> job_roles)
# ─────────────────────────────────────────────────────────────
def ingest_occupation(conn):
    print("\n[12/12] Ingesting occupation -> job_roles ...")
    headers, rows = read_csv("327548")
    if not rows:
        return 0
    cur = conn.cursor()
    count = 0
    for r in rows:
        occ_code = safe_str(r.get("occupation_code"))
        if not occ_code:
            continue
        occ_name = safe_str(r.get("occupation_name"))
        if not occ_name:
            continue
        sector = safe_str(r.get("sector"))
        source = safe_str(r.get("source"))
        source_url = safe_str(r.get("source_url"))
        source_doc = safe_str(r.get("source_document"))

        # Check if already exists
        existing = cur.execute("SELECT role_id FROM job_roles WHERE occupation_code=?", (occ_code,)).fetchone()
        if existing:
            continue

        # Find max role_id
        max_id = cur.execute("SELECT MAX(CAST(SUBSTR(role_id,4) AS INTEGER)) FROM job_roles WHERE role_id LIKE 'OCC%'").fetchone()[0] or 32
        new_id = f"OCC{max_id+1:03d}"

        cur.execute("""INSERT OR REPLACE INTO job_roles
            (role_id, job_title, normalized_role, sector, occupation_code,
             source, source_url, source_title, is_synthetic, data_source)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (new_id, occ_name, occ_name.lower(), sector, occ_code,
             source, source_url, source_doc, 0, "REAL"))
        count += 1
    conn.commit()
    print(f"  -> {count} new occupations added")
    return count


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("KAUSHORA REAL DATA INGESTION — New Research Package")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Downloads: {DOWNLOADS}")

    if not DB_PATH.exists():
        print(f"\nERROR: Database not found at {DB_PATH}")
        print("Run: python scripts/init_db.py && python scripts/import_csv_data.py")
        sys.exit(1)

    # Verify all files exist
    missing = []
    for frag, desc in FILES.items():
        if not find_file(frag):
            missing.append(f"{desc} ({frag})")
    if missing:
        print(f"\nERROR: Missing files: {', '.join(missing)}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = OFF")  # Temporarily disable for bulk import

    try:
        total = 0
        total += ingest_sources(conn)
        total += ingest_skills(conn)
        total += ingest_skill_demand(conn)
        total += ingest_placements(conn)
        total += ingest_district_skill_gaps(conn)
        total += ingest_evidence(conn)
        total += ingest_trends(conn)
        total += ingest_employer_evidence(conn)
        total += ingest_nos_qp(conn)
        total += ingest_courses(conn)
        total += ingest_districts(conn)
        total += ingest_occupation(conn)

        print("\n" + "=" * 60)
        print(f"INGESTION COMPLETE — {total} total records imported/updated")
        print("=" * 60)

        # Print summary
        cur = conn.cursor()
        tables = [
            ("sources", "SELECT COUNT(*) FROM sources"),
            ("skills", "SELECT COUNT(*) FROM skills"),
            ("skill_aliases", "SELECT COUNT(*) FROM skill_aliases"),
            ("skill_demand", "SELECT COUNT(*) FROM skill_demand"),
            ("placements", "SELECT COUNT(*) FROM placements"),
            ("district_skill_gaps", "SELECT COUNT(*) FROM district_skill_gaps"),
            ("evidence_metrics", "SELECT COUNT(*) FROM evidence_metrics"),
            ("trends", "SELECT COUNT(*) FROM trends"),
            ("employer_evidence", "SELECT COUNT(*) FROM employer_evidence"),
            ("qualifications", "SELECT COUNT(*) FROM qualifications"),
            ("courses", "SELECT COUNT(*) FROM courses"),
            ("course_skills", "SELECT COUNT(*) FROM course_skills"),
            ("districts", "SELECT COUNT(*) FROM districts"),
            ("job_roles", "SELECT COUNT(*) FROM job_roles"),
        ]
        print("\nPost-ingestion table counts:")
        for name, sql in tables:
            try:
                cnt = cur.execute(sql).fetchone()[0]
                print(f"  {name:30s} {cnt:>5d}")
            except Exception as e:
                print(f"  {name:30s} ERROR: {e}")

    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


if __name__ == "__main__":
    main()
