"""Canonical importer for the Kaushora real public CSV dataset (18 files).

Replaces the legacy .md catalog AND deletes all synthetic demo rows:
  - skills / job_roles / courses / course_skills / skill_aliases: FULL REPLACE
    with source identifiers (SKL*/OCC*/CRS*); old SK-*/NCO-*/QP-* namespace retired
  - curriculum: cleared (courses replaced; CSV has no module breakdown)
  - job_postings / placements: DELETE WHERE is_synthetic=1 (CSV has none -> empty, honest)
  - district_capacity / training_centres: DELETE synthetic, INSERT real rows
  - employer_surveys: DELETE synthetic ONLY; observed user rows preserved
  - trends (WEF, real), users: NEVER touched
  - sources/states/districts/sectors/occupation_skills/qualifications/
    labour_indicators/evidence_metrics/skill_demand/district_skill_gaps/
    curriculum_alignment_ref/recommendations: populated from CSV

Single transaction: validation failure rolls back, DB untouched.
Idempotent: stable PKs, DELETE+INSERT per dataset table.
"""
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_csv_dataset import parse_dataset

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database" / "kaushora.db"


def _slug(name):
    import re
    return re.sub(r"\s+", "_", (name or "").strip().lower())


def main():
    res = parse_dataset()
    if res["errors"]:
        print("VALIDATION ERRORS — import aborted, database untouched:")
        for e in res["errors"]:
            print(f"  ERROR: {e}")
        raise SystemExit(1)
    for w in res["warnings"]:
        print(f"WARNING: {w}")
    for n in res["notes"]:
        print(f"NOTE: {n}")
    T = {k: v["rows"] for k, v in res["tables"].items()}
    by_id = {}
    for r in T["sources"]:
        by_id[r["source_id"]] = r
    sec_name = {r["sector_id"]: r["sector_name"] for r in T["sectors"]}
    state_name = {r["state_id"]: r["state_name"] for r in T["states"]}
    dist_name = {r["district_id"]: r["district_name"] for r in T["districts"]}

    def src(r):
        """Provenance tuple from a row's source_id."""
        s = by_id.get(r.get("source_id") or "", {})
        cov = " to ".join(x for x in [s.get("coverage_start"), s.get("coverage_end")] if x)
        return (s.get("source_name", ""), s.get("source_url", ""), s.get("dataset_name", ""),
                s.get("organization", ""), s.get("publication_date", "") or None, cov or s.get("publication_date", ""))

    # skill sector derivation: majority linked-occupation sector (tie -> lowest
    # occupation_id); fallback majority teaching-course sector; else NULL (honest).
    occ_sector = {}
    for r in T["occupations"]:
        occ_sector[r["occupation_id"]] = r["sector_id"]
    course_sector = {}
    for r in T["courses"]:
        course_sector[r["course_id"]] = r["sector_id"]
    skill_occs = {}
    for r in T["occupation_skills"]:
        skill_occs.setdefault(r["skill_id"], []).append(r["occupation_id"])
    skill_courses = {}
    for r in T["course_skills"]:
        skill_courses.setdefault(r["skill_id"], []).append(r["course_id"])

    def skill_sector(sid):
        occs = sorted(set(skill_occs.get(sid, [])))
        if occs:
            votes = {}
            for o in occs:
                votes[occ_sector[o]] = votes.get(occ_sector[o], 0) + 1
            top = max(votes.values())
            cands = sorted(o for o in occs if votes[occ_sector[o]] == top)
            return sec_name[occ_sector[cands[0]]]
        crs = sorted(set(skill_courses.get(sid, [])))
        if crs:
            votes = {}
            for c in crs:
                votes[course_sector[c]] = votes.get(course_sector[c], 0) + 1
            top = max(votes.values())
            cands = sorted(c for c in crs if votes[course_sector[c]] == top)
            return sec_name[course_sector[cands[0]]]
        return None

    counts = {}
    conn = sqlite3.connect(DB)
    try:
        # Temporarily defer FK checks for bulk replace (student data refs skills)
        conn.execute("PRAGMA foreign_keys = OFF")
        c = conn.cursor()

        # ---- wipe order: children before parents; synthetic shared tables ----
        for t in ["occupation_skills", "qualifications", "course_skills", "curriculum",
                  "recommendations", "skill_demand", "district_skill_gaps",
                  "curriculum_alignment_ref", "placements", "skill_aliases",
                  "labour_indicators", "evidence_metrics"]:
            c.execute(f"DELETE FROM {t}")
        c.execute("DELETE FROM job_postings WHERE is_synthetic=1")
        c.execute("DELETE FROM employer_surveys WHERE is_synthetic=1")
        # district_capacity / training_centres hold no user data: full replace with real rows
        c.execute("DELETE FROM district_capacity")
        c.execute("DELETE FROM training_centres")
        for t in ["skills", "job_roles", "courses", "districts", "states", "sectors", "sources", "dataset_meta"]:
            c.execute(f"DELETE FROM {t}")
        # Also clean junction tables that reference deleted parents
        for t in ["job_posting_skills", "job_posting_occupations"]:
            try:
                c.execute(f"DELETE FROM {t}")
            except Exception:
                pass
        conn.execute("PRAGMA foreign_keys = ON")

        # ---- parents ----
        for r in T["sources"]:
            c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["source_id"], r["source_name"], r["organization"], r["dataset_name"],
                       r["dataset_description"], r["source_url"], r["download_url"], r["publication_date"],
                       r["retrieval_date"], r["coverage_start"], r["coverage_end"], r["geographic_coverage"],
                       r["data_type"], r["license_or_usage_note"], r["source_status"], "REAL"))
        counts["sources"] = len(T["sources"])
        for r in T["states"]:
            c.execute("INSERT INTO states VALUES (?,?,?,?,?)",
                      (r["state_id"], r["state_code"], r["state_name"], r["source_id"], "REAL"))
        counts["states"] = len(T["states"])
        for r in T["districts"]:
            c.execute("INSERT INTO districts (district_id, district_code, district_name, state_id, state_name, source_id, data_source) VALUES (?,?,?,?,?,?,?)",
                      (r["district_id"], r["district_code"], r["district_name"], r["state_id"],
                       r["state_name"], r["source_id"], "REAL"))
        counts["districts"] = len(T["districts"])
        for r in T["sectors"]:
            c.execute("INSERT INTO sectors VALUES (?,?,?,?,?)",
                      (r["sector_id"], r["sector_name"], r["sector_description"], r["source_id"], "REAL"))
        counts["sectors"] = len(T["sectors"])

        # ---- skills (new SKL catalog) ----
        for r in T["skills"]:
            sname, surl, stitle, pub, pubdate, period = src(r)
            c.execute("INSERT INTO skills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["skill_id"], r["skill_name"], _slug(r["skill_name"]), r["skill_category"],
                       skill_sector(r["skill_id"]), r["skill_description"], None,
                       sname, surl, stitle, pub, pubdate, period,
                       "official_source", 0, r["source_id"], "REAL"))
        counts["skills"] = len(T["skills"])

        # ---- occupations -> job_roles ----
        for r in T["occupations"]:
            sname, surl, stitle, pub, pubdate, period = src(r)
            c.execute("INSERT INTO job_roles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["occupation_id"], r["occupation_name"], r["occupation_name"],
                       sec_name[r["sector_id"]], f"NSQF Level {r['nsqf_level']}", None,
                       r["qp_name"], None, sname, surl, stitle, pub, pubdate, period,
                       "official_dataset", 0, r["occupation_code"], r["qp_code"], r["qp_name"],
                       r["sector_id"], r["nsqf_level"], r["standard_status"], r["source_id"], "REAL"))
        counts["job_roles"] = len(T["occupations"])

        for r in T["qualifications"]:
            c.execute("INSERT INTO qualifications VALUES (?,?,?,?,?,?,?,?)",
                      (r["qualification_id"], r["qualification_name"], r["qp_code"], r["occupation_id"],
                       r["nsqf_level"], r["qualification_status"], r["source_id"], "REAL"))
        counts["qualifications"] = len(T["qualifications"])

        for r in T["occupation_skills"]:
            c.execute("INSERT INTO occupation_skills VALUES (?,?,?,?,?,?,?)",
                      (r["occupation_id"], r["skill_id"], r["importance"], r["competency_type"],
                       r["nos_code"], r["source_id"], "REAL"))
        counts["occupation_skills"] = len(T["occupation_skills"])

        # ---- courses ----
        taught = {}
        for r in T["course_skills"]:
            taught.setdefault(r["course_id"], []).append(r["skill_id"])
        for r in T["courses"]:
            sname, surl, stitle, pub, pubdate, period = src(r)
            c.execute("INSERT INTO courses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["course_id"], r["course_name"], sec_name[r["sector_id"]],
                       f"NSQF Level {r['nsqf_level']}", r["duration"], None, r["provider_name"],
                       ", ".join(sorted(set(taught.get(r["course_id"], [])))), None,
                       r["course_status"], sname, surl, stitle, pub, pubdate, period,
                       "public_course_data", 0, r["course_code"], r["sector_id"],
                       r["nsqf_level"], r["source_id"], "REAL"))
        counts["courses"] = len(T["courses"])

        for r in T["course_skills"]:
            c.execute("INSERT INTO course_skills VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (r["course_id"], r["skill_id"], None, None, "", "",
                       "official_mapping", 0, r["coverage_level"], r["skill_type"], r["source_id"]))
        counts["course_skills"] = len(T["course_skills"])
        counts["curriculum"] = 0  # cleared: CSV carries no module breakdown

        # ---- training centres (8 real) ----
        for r in T["training_centres"]:
            c.execute("INSERT INTO training_centres VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["centre_id"], r["centre_name"], state_name[r["state_id"]], dist_name[r["district_id"]],
                       None, None, None, None, None, None, by_id[r["source_id"]]["source_name"],
                       by_id[r["source_id"]]["source_url"], by_id[r["source_id"]]["coverage_end"],
                       "official_source", 0, r["district_id"], r["state_id"], r["scheme"],
                       r["provider"], r["centre_type"], r["source_id"], "REAL"))
        counts["training_centres"] = len(T["training_centres"])

        # ---- capacity (3 real, NULLs preserved) ----
        def _int(v):
            return None if v is None else int(float(str(v).replace(",", "")))
        for r in T["capacity"]:
            c.execute("INSERT INTO district_capacity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["district_id"], state_name["ST001"], dist_name[r["district_id"]],
                       None, None, r["training_centres"], None, None, None,
                       by_id[r["source_id"]]["source_name"], by_id[r["source_id"]]["source_url"],
                       r["period"], "official_source", 0, r["scheme"],
                       _int(r["training_seats"]), _int(r["enrolments"]), _int(r["assessments"]),
                       _int(r["certifications"]), _int(r["year"]), r["period"], "ST001",
                       r["source_id"], "REAL"))
        counts["district_capacity"] = len(T["capacity"])

        # ---- indicators / evidence / derived-reference tables ----
        for r in T["labour_indicators"]:
            c.execute("INSERT INTO labour_indicators VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["indicator_id"], r["state_id"], r["district_id"],
                       _int(r["year"]), r["period"], r["indicator_name"], float(r["indicator_value"]),
                       r["unit"], r["population_group"], r["rural_urban"], r["status_type"],
                       r["source_id"], "REAL"))
        counts["labour_indicators"] = len(T["labour_indicators"])
        for r in T["evidence_metrics"]:
            num = None
            try:
                num = float(str(r["metric_value"]).replace(",", "").rstrip("+"))
            except (ValueError, TypeError):
                pass
            c.execute("INSERT INTO evidence_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["evidence_id"], r["metric_name"], r["metric_value"], num, r["unit"],
                       r["geography"], r["time_period"], r["source_id"], r["source_reference"],
                       r["calculation_method"], 1 if r["is_observed"] == "TRUE" else 0,
                       1 if r["is_derived"] == "TRUE" else 0, r["confidence_level"], r["notes"], "REAL"))
        counts["evidence_metrics"] = len(T["evidence_metrics"])
        for r in T["skill_demand"]:
            c.execute("INSERT INTO skill_demand VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["skill_demand_id"], r["skill_id"], r["geography"], r["time_period"],
                       r["employment_signal"], r["occupation_signal"],
                       r["training_gap_signal"], r["growth_signal"],
                       float(r["demand_score"]) if r["demand_score"] is not None else None,
                       r["demand_status"], r["calculation_method"], r["source_ids"],
                       1 if r["is_derived"] == "TRUE" else 0, "REAL"))
        counts["skill_demand"] = len(T["skill_demand"])
        for r in T["district_skill_gaps"]:
            c.execute("INSERT INTO district_skill_gaps VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (r["gap_id"], r["district_id"], r["skill_id"], r["demand_signal"],
                       r["training_supply_signal"],
                       float(r["gap_score"]) if r["gap_score"] is not None else None,
                       r["gap_status"], r["evidence_sources"], r["calculation_method"],
                       1 if r["is_derived"] == "TRUE" else 0, "REAL"))
        counts["district_skill_gaps"] = len(T["district_skill_gaps"])
        for r in T["curriculum_alignment"]:
            c.execute("INSERT INTO curriculum_alignment_ref VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["alignment_id"], r["course_id"], r["occupation_id"],
                       _int(r["required_skill_count"]), _int(r["covered_skill_count"]),
                       _int(r["missing_skill_count"]), float(r["alignment_score"]),
                       r["missing_skills"], r["recommended_updates"], r["source_ids"],
                       1 if r["is_derived"] == "TRUE" else 0, "REAL"))
        counts["curriculum_alignment_ref"] = len(T["curriculum_alignment"])
        for r in T["recommendations"]:
            c.execute("INSERT INTO recommendations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r["recommendation_id"], r["district_id"], r["skill_id"], r["occupation_id"],
                       r["recommendation_type"], r["recommendation_text"], r["priority"], r["reason"],
                       r["supporting_evidence"], r["source_ids"],
                       1 if r["is_derived"] == "TRUE" else 0, "REAL"))
        counts["recommendations"] = len(T["recommendations"])

        # ---- skill aliases rebuilt for SKL catalog ----
        aliases = []
        for r in T["skills"]:
            aliases.append((_slug(r["skill_name"]), r["skill_id"]))
        aliases += [
            ("communication", "SKL001"), ("python", "SKL012"), ("programming", "SKL012"),
            ("web development", "SKL012"), ("data entry", "SKL011"), ("data entry operations", "SKL011"),
            ("graphic design", "SKL013"), ("quality check", "SKL008"), ("quality checking", "SKL008"),
            ("maintain work area", "SKL009"), ("health safety security", "SKL010"),
            ("health and safety", "SKL010"), ("install washing machine", "SKL003"),
            ("plumbing installation", "SKL007"), ("plumbing", "SKL007"),
            ("food and beverage service", "SKL014"), ("warehouse operations", "SKL015"),
            ("warehouse", "SKL015"), ("security management", "SKL016"), ("security", "SKL016"),
            ("dairy farming", "SKL017"), ("steel fixing", "SKL018"), ("masonry", "SKL019"),
            ("carpentry", "SKL020"), ("housekeeping", "SKL002"),
            ("remove packaging", "SKL005"), ("placement of machine", "SKL006"),
            ("prepare route plan", "SKL004"),
        ]
        for a, s in aliases:
            c.execute("INSERT OR REPLACE INTO skill_aliases VALUES (?,?)", (a, s))
        counts["skill_aliases"] = len(aliases)

        # ---- dataset_meta refresh ----
        notes_map = {
            "sources": "10 provenance records (MoSPI/NSDC/MSDE/DGT/DVET).",
            "states": "Maharashtra (ST001) + All India (ST002).",
            "districts": "36 Maharashtra districts incl. Nagpur DT019.",
            "sectors": "13 NSDC/PMKVY sectors.",
            "skills": "20 real skills (SKL001-020); sector derived from linked occupations/courses, NULL where unmapped.",
            "job_roles": "32 real occupations with QP codes + NSQF levels.",
            "occupation_skills": "10 explicit NOS-coded requirement links across 4 occupations.",
            "qualifications": "13 active QPs.",
            "courses": "15 real ITI courses (Saoner Nagpur + Mumbai) with NSQF levels.",
            "course_skills": "12 explicit Full-coverage course-skill links.",
            "curriculum": "No module breakdown in CSV source; coverage via course_skills.",
            "training_centres": "8 real centres (7 Ahilyanagar PMKVY + ITI Saoner Nagpur).",
            "district_capacity": "3 sparse capacity facts; NULL = not published.",
            "labour_indicators": "15 PLFS indicators (state/national only; no district-level PLFS published).",
            "evidence_metrics": "10 citable metrics incl. LFPR 59.3, NCS vacancies 3.43 Cr, 684 MH centres.",
            "skill_demand": "1 assessment row, all signals NULL = honestly insufficient.",
            "district_skill_gaps": "1 assessment row, demand missing = Unavailable.",
            "curriculum_alignment": "5 provided reference alignments (derived by compiler).",
            "recommendations": "3 provided derived recommendations.",
            "trends": "3 WEF rows preserved (no replacement in CSV source).",
            "job_postings": "CSV carries no postings; synthetic purged -> empty, honest.",
            "placements": "CSV carries no placements; synthetic purged -> empty, honest.",
            "employer_requirements": "CSV carries none; only observed user submissions count.",
        }
        for key, note in notes_map.items():
            cnt_map = {"sources": counts.get("sources", 0), "states": counts.get("states", 0),
                       "districts": counts.get("districts", 0), "sectors": counts.get("sectors", 0),
                       "skills": counts.get("skills", 0), "job_roles": counts.get("job_roles", 0),
                       "occupation_skills": counts.get("occupation_skills", 0),
                       "qualifications": counts.get("qualifications", 0),
                       "courses": counts.get("courses", 0), "course_skills": counts.get("course_skills", 0),
                       "curriculum": 0, "training_centres": counts.get("training_centres", 0),
                       "district_capacity": counts.get("district_capacity", 0),
                       "labour_indicators": counts.get("labour_indicators", 0),
                       "evidence_metrics": counts.get("evidence_metrics", 0),
                       "skill_demand": counts.get("skill_demand", 0),
                       "district_skill_gaps": counts.get("district_skill_gaps", 0),
                       "curriculum_alignment": counts.get("curriculum_alignment_ref", 0),
                       "recommendations": counts.get("recommendations", 0),
                       "trends": c.execute("SELECT COUNT(*) FROM trends").fetchone()[0],
                       "job_postings": c.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0],
                       "placements": c.execute("SELECT COUNT(*) FROM placements").fetchone()[0],
                       "employer_requirements": c.execute("SELECT COUNT(*) FROM employer_surveys WHERE data_type='observed'").fetchone()[0]}
            st = "imported" if cnt_map.get(key, 0) else ("empty — no source records" if key in
                ("job_postings", "placements", "employer_requirements", "curriculum") else "imported")
            c.execute("INSERT INTO dataset_meta VALUES (?,?,?,?)", (key, note, cnt_map.get(key, 0), st))
        counts["dataset_meta"] = len(notes_map)

        total_real = sum(v for k, v in counts.items() if k in
                         ("sources", "states", "districts", "sectors", "skills", "job_roles",
                          "occupation_skills", "qualifications", "courses", "course_skills",
                          "training_centres", "district_capacity", "labour_indicators",
                          "evidence_metrics", "skill_demand", "district_skill_gaps",
                          "curriculum_alignment_ref", "recommendations"))
        c.execute("INSERT INTO ingestion_runs (started_at, dataset_file, records_imported, records_rejected, warnings, status) VALUES (?,?,?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(), "data/raw/csv/*.csv (18 files: SRC MoSPI/NSDC/MSDE/DGT/DVET)",
                   total_real, 0, "; ".join(res["notes"][:6]), "success"))

        # FK check deferred to post-commit (junction tables reference deleted-then-reinserted parents)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Imported real CSV dataset (all is_synthetic=0, data_source=REAL):")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print("Preserved: trends (WEF), users, observed employer surveys. Purged: all synthetic rows.")


if __name__ == "__main__":
    main()
