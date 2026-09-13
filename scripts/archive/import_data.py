"""Import the canonical REAL EVIDENCE dataset into SQLite.

Data flow:
    data/raw/kaushora_real_evidence_dataset.md
    -> scripts/parse_evidence_dataset.py (validated parsed data)
    -> SQLite -> analytics services -> Flask APIs -> frontend

Only records physically present in the file are imported. Sections marked
"No records available" stay empty — never fabricated.
Single transaction: validation failure rolls back, no partial imports.
Re-running replaces dataset rows (DELETE + INSERT by stable PKs) without
duplicating; users and user-submitted employer surveys are never touched.
"""
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_evidence_dataset import parse_dataset

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database" / "kaushora.db"

DATASET_TABLES = ["course_skills", "curriculum", "skill_aliases", "job_roles", "skills", "courses", "trends", "dataset_meta"]

ALIASES = [
    ("programming_fundamentals", "SK-JSD-01"),
    ("programming", "SK-JSD-01"),
    ("python", "SK-JSD-01"),
    ("java", "SK-JSD-01"),
    ("database_management", "SK-JSD-02"),
    ("database management", "SK-JSD-02"),
    ("sql", "SK-JSD-02"),
    ("databases", "SK-JSD-02"),
    ("software_testing", "SK-JSD-03"),
    ("software testing", "SK-JSD-03"),
    ("testing", "SK-JSD-03"),
    ("technical_documentation", "SK-JSD-04"),
    ("technical documentation", "SK-JSD-04"),
    ("documentation", "SK-JSD-04"),
    ("data_entry_operations", "SK-DEO-01"),
    ("data entry operations", "SK-DEO-01"),
    ("data entry", "SK-DEO-01"),
    ("quality_checking", "SK-DEO-02"),
    ("quality checking", "SK-DEO-02"),
    ("patient_care_assistance", "SK-GDA-01"),
    ("patient care assistance", "SK-GDA-01"),
    ("patient care", "SK-GDA-01"),
    ("sanitation_and_hygiene", "SK-GDA-02"),
    ("sanitation and hygiene", "SK-GDA-02"),
    ("sanitation", "SK-GDA-02"),
    ("hygiene", "SK-GDA-02"),
    ("communication_interpersonal", "SK-GDA-03"),
    ("communication and interpersonal skills", "SK-GDA-03"),
    ("communication", "SK-GDA-03"),
]


def _int(v, field, rid):
    try:
        n = int(float(str(v).replace(",", "")))
    except (ValueError, TypeError):
        raise ValueError(f"Non-integer {field}='{v}' in {rid}")
    if n <= 0:
        raise ValueError(f"Non-positive {field}='{v}' in {rid}")
    return n


def main():
    res = parse_dataset()
    if res["errors"]:
        print("VALIDATION ERRORS — import aborted, database untouched:")
        for e in res["errors"]:
            print(f"  ERROR: {e}")
        raise SystemExit(1)
    for w in res["warnings"]:
        print(f"WARNING: {w}")
    T = {k: v["rows"] for k, v in res["tables"].items()}
    counts = {}
    rejected = 0

    conn = sqlite3.connect(DB)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        # Synthetic demo rows reference the canonical catalog through foreign
        # keys. Remove only those regenerable rows before replacing catalog
        # records; observed employer submissions remain intact.
        for t in ["job_postings", "placements", "district_capacity", "training_centres", "employer_surveys"]:
            c.execute(f"DELETE FROM {t} WHERE is_synthetic=1")
        for t in DATASET_TABLES:
            c.execute(f"DELETE FROM {t}")

        for r in T["job_roles"]:
            c.execute(
                "INSERT INTO job_roles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["role_id"],
                    r["job_title"],
                    r.get("normalized_role", ""),
                    r.get("sector", ""),
                    r.get("qualification_level", ""),
                    r.get("typical_experience", ""),
                    r.get("description", ""),
                    r.get("related_skills", ""),
                    r.get("source", ""),
                    r.get("source_url", ""),
                    r.get("source_title", ""),
                    r.get("publisher", ""),
                    r.get("publication_date", ""),
                    r.get("data_period", ""),
                    r.get("data_type", "official_dataset"),
                    int(r.get("is_synthetic") or 0),
                ),
            )
        counts["job_roles"] = len(T["job_roles"])

        for r in T["skills"]:
            c.execute(
                "INSERT INTO skills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["skill_id"],
                    r["skill_name"],
                    r.get("normalized_skill_name", ""),
                    r.get("skill_category", ""),
                    r.get("sector", ""),
                    r.get("description", ""),
                    r.get("technology_status", ""),
                    r.get("source", ""),
                    r.get("source_url", ""),
                    r.get("source_title", ""),
                    r.get("publisher", ""),
                    r.get("publication_date", "") or None,
                    r.get("data_period", ""),
                    r.get("data_type", "official_report"),
                    int(r.get("is_synthetic") or 0),
                ),
            )
        counts["skills"] = len(T["skills"])

        for r in T["courses"]:
            c.execute(
                "INSERT INTO courses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["course_id"],
                    r["course_name"],
                    r.get("sector", ""),
                    r.get("qualification_level", ""),
                    r.get("duration", ""),
                    r.get("delivery_mode", ""),
                    r.get("provider", ""),
                    r.get("skills_taught", ""),
                    r.get("target_roles", ""),
                    r.get("course_status", "Active"),
                    r.get("source", ""),
                    r.get("source_url", ""),
                    r.get("source_title", ""),
                    r.get("publisher", ""),
                    r.get("publication_date", "") or None,
                    r.get("data_period", ""),
                    r.get("data_type", "public_course_data"),
                    int(r.get("is_synthetic") or 0),
                ),
            )
        counts["courses"] = len(T["courses"])

        for r in T["course_skills"]:
            c.execute(
                "INSERT INTO course_skills VALUES (?,?,?,?,?,?,?,?)",
                (
                    r["course_id"],
                    r["skill_id"],
                    r.get("proficiency_level", "Intermediate"),
                    _int(r.get("training_hours"), "training_hours", r["course_id"] + "/" + r["skill_id"]),
                    r.get("source", ""),
                    r.get("source_url", ""),
                    r.get("data_type", "derived_metric"),
                    int(r.get("is_synthetic") or 0),
                ),
            )
        counts["course_skills"] = len(T["course_skills"])

        for r in T["curriculum"]:
            c.execute(
                "INSERT INTO curriculum VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["curriculum_id"],
                    r["course_id"],
                    r.get("module_name", ""),
                    r["skill_id"],
                    r.get("proficiency_level", "Intermediate"),
                    _int(r.get("training_hours"), "training_hours", r["curriculum_id"]),
                    r.get("module_status", "Active"),
                    r.get("source", ""),
                    r.get("source_url", ""),
                    r.get("source_title", ""),
                    r.get("publisher", ""),
                    r.get("publication_date", "") or None,
                    r.get("data_period", ""),
                    r.get("data_type", "official_report"),
                    int(r.get("is_synthetic") or 0),
                ),
            )
        counts["curriculum"] = len(T["curriculum"])

        for r in T["trends"]:
            c.execute(
                "INSERT INTO trends VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["trend_id"],
                    r.get("technology_or_skill", ""),
                    r.get("sector", ""),
                    r.get("trend_description", ""),
                    r.get("evidence", ""),
                    r.get("trend_direction", ""),
                    r.get("period", ""),
                    r.get("source", ""),
                    r.get("source_url", ""),
                    r.get("source_title", ""),
                    r.get("publisher", ""),
                    r.get("data_type", "official_report"),
                    int(r.get("is_synthetic") or 0),
                ),
            )
        counts["trends"] = len(T["trends"])

        for a, s in ALIASES:
            c.execute("INSERT OR REPLACE INTO skill_aliases VALUES (?,?)", (a, s))
        counts["skill_aliases"] = len(ALIASES)

        for key, note in res["notes"].items():
            c.execute("INSERT INTO dataset_meta VALUES (?,?,?,?)", (key, note, res["counts"].get(key, 0), "imported"))
        for sec in [
            "job_demand",
            "training_capacity",
            "placement_outcomes",
            "employer_requirements",
            "district_skill_demand",
            "skill_demand_aggregation",
            "curriculum_alignment",
            "district_skill_gaps",
            "recommendations",
        ]:
            c.execute(
                "INSERT INTO dataset_meta VALUES (?,?,?,?)",
                (sec, "No source records in the canonical dataset file; left empty by design (see file).", 0, "empty — no source records"),
            )
        counts["dataset_meta"] = 6 + 9

        total_imported = sum(v for k, v in counts.items() if k in ("job_roles", "skills", "courses", "course_skills", "curriculum", "trends"))
        c.execute(
            "INSERT INTO ingestion_runs (started_at, dataset_file, records_imported, records_rejected, warnings, status) VALUES (?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(),
                "data/raw/kaushora_real_evidence_dataset.md",
                total_imported,
                rejected,
                "; ".join(res["warnings"][:10]),
                "success",
            ),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Imported Real Evidence Dataset (real public sources; is_synthetic=0):")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print("Untouched: users, employer_surveys (user submissions), empty future-schema tables.")
    print("Run python scripts/seed_synthetic.py to populate the clearly labelled demo data used by the interactive views.")


if __name__ == "__main__":
    main()
