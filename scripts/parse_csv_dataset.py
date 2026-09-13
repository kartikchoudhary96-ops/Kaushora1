"""Parse + clean the canonical Kaushora CSV dataset (18 files, MoSPI/NSDC/MSDE/DGT/DVET).

Raw layer (never modified):  data/raw/csv/*.csv  (byte copies of supplied files)
Clean layer (written here):  data/processed/csv/*.csv + data_quality_report.json

Cleaning rules (all reported, never silent):
- utf-8-sig, strip surrounding whitespace on every cell
- NULL tokens ('', 'NULL', 'None', 'null', 'Not specified') -> None
- 01_sources ragged rows repaired positionally and logged:
    SRC002 geographic_coverage = 'All India' + 'Rural/Urban'
    SRC003 dataset_description = 3 fragments joined with ','
    SRC006 data_type = 'Employment Portal Statistics' (stray 'Official
      Government Statistics' token dropped and logged)
- nsqf_level kept as TEXT ('3.5' preserved, never coerced to float)
- numerics validated (indicator_value float; centre/seat counts int);
  '2900+' -> 2900.0 with approximation note preserved
- state/district/occupation/skill names preserved verbatim (incl. aliases
  in parentheses); codes preserved verbatim
- duplicate PKs / bad FKs are ERRORS (import aborts); composite keys
  (course_id,skill_id) / (occupation_id,skill_id) must be unique
- 'None' strings in alignment missing_skills/recommended_updates -> None

Usage: python scripts/parse_csv_dataset.py   # prints profile + quality report
"""
import csv
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw" / "csv"
CLEAN = BASE / "data" / "processed" / "csv"

FILES = {
    "sources": "01_sources.csv",
    "states": "02_states.csv",
    "districts": "03_districts.csv",
    "sectors": "04_sectors.csv",
    "recommendations": "05_recommendations.csv",
    "district_skill_gaps": "06_district_skill_gaps.csv",
    "curriculum_alignment": "07_curriculum_alignment.csv",
    "skill_demand": "08_skill_demand.csv",
    "evidence_metrics": "09_evidence_metrics.csv",
    "capacity": "10_capacity.csv",
    "labour_indicators": "11_labour_indicators.csv",
    "training_centres": "12_training_centres.csv",
    "course_skills": "13_course_skills.csv",
    "courses": "14_courses.csv",
    "qualifications": "15_qualifications.csv",
    "occupation_skills": "16_occupation_skills.csv",
    "skills": "17_skills.csv",
    "occupations": "18_occupations.csv",
}

NULL_TOKENS = {"", "NULL", "None", "null", "Not specified", "N/A", "n/a", "-"}


def _clean_cell(v):
    if v is None:
        return None
    v = v.strip()
    return None if v in NULL_TOKENS else v


def _read_raw(name):
    """Read raw CSV with ragged-row repair for 01_sources."""
    path = RAW / FILES[name]
    if not path.is_file():
        raise FileNotFoundError(f"Raw dataset file missing: {path}")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    header, data = rows[0], rows[1:]
    header = [h.strip() for h in header]
    fixed = []
    notes = []
    for i, row in enumerate(data, start=2):
        if name == "sources" and len(row) != len(header):
            sid = row[0] if row else "?"
            if sid == "SRC002" and len(row) == len(header) + 1:
                # geographic_coverage split: 'All India' | 'Rural/Urban'
                row = row[:11] + [row[11] + "," + row[12]] + row[13:]
                notes.append(f"SRC002: merged geographic_coverage='All India,Rural/Urban'")
            elif sid == "SRC003" and len(row) == len(header) + 2:
                row = row[:4] + [",".join(c.strip() for c in row[4:7])] + row[7:]
                notes.append("SRC003: merged 3 dataset_description fragments")
            elif sid == "SRC006" and len(row) == len(header) + 1:
                # stray 'Official Government Statistics' between data_type and license
                dropped = row[13]
                row = row[:13] + row[14:]
                notes.append(f"SRC006: dropped stray token {dropped!r}; data_type='Employment Portal Statistics'")
            else:
                raise ValueError(f"01_sources.csv line {i}: unexpected width {len(row)} (id={sid})")
        if len(row) != len(header):
            raise ValueError(f"{FILES[name]} line {i}: width {len(row)} != header {len(header)}")
        fixed.append([_clean_cell(c) for c in row])
    return header, fixed, notes


def _to_float(v, field, rid, errors):
    if v is None:
        return None
    s = v.replace(",", "").rstrip("+").strip()
    try:
        return float(s)
    except ValueError:
        errors.append(f"Non-numeric {field}={v!r} in {rid}")
        return None


def _to_int(v, field, rid, errors):
    f = _to_float(v, field, rid, errors)
    if f is None:
        return None
    if f != int(f):
        errors.append(f"Non-integer {field}={v!r} in {rid}")
        return None
    return int(f)


def parse_dataset():
    errors, warnings, notes = [], [], []
    T = {}
    for name in FILES:
        header, rows, n = _read_raw(name)
        notes.extend(f"{FILES[name]}: {x}" for x in n)
        T[name] = {"header": header, "rows": [dict(zip(header, r)) for r in rows]}

    # duplicate PKs (single-col tables) + composite uniqueness
    for name, pk in [("sources", "source_id"), ("states", "state_id"), ("districts", "district_id"),
                     ("sectors", "sector_id"), ("recommendations", "recommendation_id"),
                     ("district_skill_gaps", "gap_id"), ("curriculum_alignment", "alignment_id"),
                     ("skill_demand", "skill_demand_id"), ("evidence_metrics", "evidence_id"),
                     ("labour_indicators", "indicator_id"), ("training_centres", "centre_id"),
                     ("courses", "course_id"), ("qualifications", "qualification_id"),
                     ("skills", "skill_id"), ("occupations", "occupation_id")]:
        vals = [r[pk] for r in T[name]["rows"]]
        if any(v is None or v == "" for v in vals):
            errors.append(f"{name}: empty PK {pk}")
        dupes = sorted({v for v in vals if vals.count(v) > 1})
        if dupes:
            errors.append(f"{name}: duplicate {pk}: {dupes}")
    for name, cols in [("course_skills", ("course_id", "skill_id")), ("occupation_skills", ("occupation_id", "skill_id")),
                       ("capacity", ("capacity_id",))]:
        seen, d = set(), []
        for r in T["capacity"]["rows"] if name == "capacity" else T[name]["rows"]:
            key = tuple(r[c] for c in cols)
            if None in key:
                errors.append(f"{name}: NULL in key {key}")
            if key in seen:
                d.append(key)
            seen.add(key)
        if d:
            errors.append(f"{name}: duplicate keys {d}")

    # FK validity against real ID sets
    S = {r["skill_id"] for r in T["skills"]["rows"]}
    O = {r["occupation_id"] for r in T["occupations"]["rows"]}
    C = {r["course_id"] for r in T["courses"]["rows"]}
    D = {r["district_id"] for r in T["districts"]["rows"]}
    ST = {r["state_id"] for r in T["states"]["rows"]}
    SEC = {r["sector_id"] for r in T["sectors"]["rows"]}
    SRC = {r["source_id"] for r in T["sources"]["rows"]}
    EV = {r["evidence_id"] for r in T["evidence_metrics"]["rows"]}

    def fk(name, rows, col, valid, label):
        bad = sorted({r[col] for r in rows if r[col] is not None} - valid)
        if bad:
            errors.append(f"FK violation {name}.{col} -> {label}: {bad}")

    fk("course_skills", T["course_skills"]["rows"], "skill_id", S, "skills")
    fk("course_skills", T["course_skills"]["rows"], "course_id", C, "courses")
    fk("occupation_skills", T["occupation_skills"]["rows"], "occupation_id", O, "occupations")
    fk("occupation_skills", T["occupation_skills"]["rows"], "skill_id", S, "skills")
    fk("qualifications", T["qualifications"]["rows"], "occupation_id", O, "occupations")
    fk("courses", T["courses"]["rows"], "sector_id", SEC, "sectors")
    fk("occupations", T["occupations"]["rows"], "sector_id", SEC, "sectors")
    fk("training_centres", T["training_centres"]["rows"], "district_id", D, "districts")
    fk("training_centres", T["training_centres"]["rows"], "state_id", ST, "states")
    fk("capacity", T["capacity"]["rows"], "district_id", D, "districts")
    fk("labour_indicators", T["labour_indicators"]["rows"], "state_id", ST, "states")
    fk("recommendations", T["recommendations"]["rows"], "district_id", D, "districts")
    fk("recommendations", T["recommendations"]["rows"], "skill_id", S, "skills")
    fk("recommendations", T["recommendations"]["rows"], "occupation_id", O, "occupations")
    fk("recommendations", T["recommendations"]["rows"], "supporting_evidence", EV, "evidence")
    fk("curriculum_alignment", T["curriculum_alignment"]["rows"], "course_id", C, "courses")
    fk("curriculum_alignment", T["curriculum_alignment"]["rows"], "occupation_id", O, "occupations")
    fk("districts", T["districts"]["rows"], "state_id", ST, "states")
    for name in ["states", "districts", "sectors", "skills", "occupations", "courses", "qualifications",
                 "occupation_skills", "course_skills", "training_centres", "capacity", "labour_indicators",
                 "evidence_metrics", "skill_demand", "district_skill_gaps", "curriculum_alignment", "recommendations"]:
        col = "source_id" if "source_id" in T[name]["header"] else ("source_ids" if "source_ids" in T[name]["header"] else None)
        if col:
            vals = set()
            for r in T[name]["rows"]:
                v = r[col]
                if v is None:
                    continue
                vals.update(x.strip() for x in v.split(","))
            bad = sorted(vals - SRC)
            if bad:
                errors.append(f"Unknown source ref {name}.{col}: {bad}")

    # numeric validation (NULL = not published, legitimate)
    for r in T["labour_indicators"]["rows"]:
        _to_float(r["indicator_value"], "indicator_value", r["indicator_id"], errors)
        if r["year"] is not None and not re.fullmatch(r"\d{4}", r["year"]):
            errors.append(f"Bad year {r['year']!r} in {r['indicator_id']}")
    for r in T["capacity"]["rows"]:
        for col in ("training_centres", "training_seats", "enrolments", "assessments", "certifications", "year"):
            _to_int(r[col], col, r["capacity_id"], errors)
    for r in T["curriculum_alignment"]["rows"]:
        for col in ("required_skill_count", "covered_skill_count", "missing_skill_count"):
            _to_int(r[col], col, r["alignment_id"], errors)
        _to_float(r["alignment_score"], "alignment_score", r["alignment_id"], errors)
    for r in T["evidence_metrics"]["rows"]:
        _to_float(r["metric_value"], "metric_value", r["evidence_id"], errors)

    # coverage summary
    coverage = {
        "sources": len(T["sources"]["rows"]),
        "states": [(r["state_id"], r["state_name"]) for r in T["states"]["rows"]],
        "districts_maharashtra": len(T["districts"]["rows"]),
        "sectors": len(T["sectors"]["rows"]),
        "skills": len(T["skills"]["rows"]),
        "occupations": len(T["occupations"]["rows"]),
        "occupation_skill_links": len(T["occupation_skills"]["rows"]),
        "occupations_with_mapped_skills": len({r["occupation_id"] for r in T["occupation_skills"]["rows"]}),
        "courses": len(T["courses"]["rows"]),
        "course_skill_links": len(T["course_skills"]["rows"]),
        "training_centres": {r["district_id"]: 0 for r in T["districts"]["rows"]} | {
            d: sum(1 for r in T["training_centres"]["rows"] if r["district_id"] == d)
            for d in {r["district_id"] for r in T["training_centres"]["rows"]}},
        "labour_indicators": len(T["labour_indicators"]["rows"]),
        "indicators_district_level": sum(1 for r in T["labour_indicators"]["rows"] if r["district_id"]),
        "evidence_metrics": len(T["evidence_metrics"]["rows"]),
        "capacity_rows": len(T["capacity"]["rows"]),
        "recommendations": len(T["recommendations"]["rows"]),
        "reference_alignments": len(T["curriculum_alignment"]["rows"]),
    }
    return {"tables": T, "errors": errors, "warnings": warnings, "notes": notes, "coverage": coverage}


def write_cleaned(parsed):
    CLEAN.mkdir(parents=True, exist_ok=True)
    for name, fname in FILES.items():
        t = parsed["tables"][name]
        with open(CLEAN / fname, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=t["header"], extrasaction="ignore")
            w.writeheader()
            for r in t["rows"]:
                w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    report = {"errors": parsed["errors"], "warnings": parsed["warnings"],
              "notes": parsed["notes"], "coverage": parsed["coverage"],
              "counts": {k: len(v["rows"]) for k, v in parsed["tables"].items()}}
    (CLEAN / "data_quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    import json
    res = parse_dataset()
    rep = write_cleaned(res)
    print(f"Raw: {RAW}  ->  Clean: {CLEAN}")
    for k, v in rep["counts"].items():
        print(f"  {k}: {v}")
    print("Coverage:", json.dumps(rep["coverage"], indent=1)[:1200])
    for n in rep["notes"]:
        print("NOTE:", n)
    for w in rep["warnings"]:
        print("WARNING:", w)
    for e in rep["errors"]:
        print("ERROR:", e)
    print(f"{len(rep['errors'])} errors, {len(rep['warnings'])} warnings")
