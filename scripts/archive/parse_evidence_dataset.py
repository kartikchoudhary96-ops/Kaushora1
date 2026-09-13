"""Parse data/raw/kaushora_real_evidence_dataset.md — the canonical REAL EVIDENCE dataset.

Extracts ONLY records physically present in the file. Empty sections
("No records available") yield zero rows — never fabricated.
No random generation, no hardcoded seed lists.

Usage:
    python scripts/parse_evidence_dataset.py     # prints counts + validation report
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE / "data" / "raw" / "kaushora_real_evidence_dataset.md"

# heading -> (internal key, pk, required columns, import flag)
SECTIONS = {
    "JOB_ROLES": {"key": "job_roles", "pk": "role_id", "required": ["role_id", "job_title", "sector"], "import": True},
    "SKILLS": {"key": "skills", "pk": "skill_id", "required": ["skill_id", "skill_name"], "import": True},
    "TRAINING_COURSES": {"key": "courses", "pk": "course_id", "required": ["course_id", "course_name"], "import": True},
    "COURSE_SKILLS": {"key": "course_skills", "pk": None, "required": ["course_id", "skill_id"], "import": True},
    "CURRICULUM": {
        "key": "curriculum",
        "pk": "curriculum_id",
        "required": ["curriculum_id", "course_id", "skill_id"],
        "import": True,
    },
    "EMERGING_TRENDS": {"key": "trends", "pk": "trend_id", "required": ["trend_id"], "import": True},
}


def _split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _parse_section(body):
    """Return (tables, methodology_note, empty_reason, notes_out).

    Data-quality handling (reported, never silent): in SKILLS /
    TRAINING_COURSES / CURRICULUM the file's header row omits
    `publication_date` while every data row carries it (publisher |
    YYYY | period | type | flag — same layout as JOB_ROLES). When all
    data rows are exactly one cell wider, the missing header is restored.
    """
    lines = body.splitlines()
    note, reason = "", ""
    header_notes = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("**Methodology note**"):
            note = re.sub(r"^\*\*Methodology note\*\*:?\s*", "", s)
        if "No records available" in s:
            m = re.search(r"\*\*Reason\*\*:?(.*)", s)
            reason = (m.group(1).strip() if m else "")
            nxt = lines.index(ln) + 1
            if nxt < len(lines) and lines[nxt].strip().startswith("**Reason**"):
                reason = re.sub(r"^\*\*Reason\*\*:?\s*", "", lines[nxt].strip())
    tables = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|\s*$", lines[i + 1].strip()):
            header = _split_row(lines[i])
            raw = []
            for k in range(i + 2, len(lines)):
                s = lines[k].strip()
                if not s.startswith("|"):
                    break
                cells = _split_row(lines[k])
                if cells and cells[0].startswith("..."):
                    continue  # continuation note, not data
                raw.append(cells)
            if raw and "publication_date" not in header and "publisher" in header and all(len(c) == len(header) + 1 for c in raw):
                header.insert(header.index("publisher") + 1, "publication_date")
                header_notes.append(
                    f"header omits 'publication_date' but all {len(raw)} data rows carry it "
                    "(publisher|year|period layout, as in JOB_ROLES) — column restored"
                )
            rows = [dict(zip(header, c)) for c in raw if len(c) == len(header)]
            if len(rows) != len(raw):
                header_notes.append(f"{len(raw) - len(rows)} malformed row(s) skipped (width mismatch)")
            tables.append((header, rows))
            i = k
        i += 1
    return tables, note, reason, header_notes


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_dataset(path=None):
    path = Path(path) if path else DATASET_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Canonical dataset not found: {path}")
    text = path.read_text(encoding="utf-8")
    if "Kaushora Real Evidence Dataset" not in text:
        raise ValueError("Real Evidence Dataset header not found — refusing to import")
    parts = re.split(r"^## ", text, flags=re.M)
    tables, notes, empty, quality = {}, {}, {}, {}
    header_warnings = []
    for p in parts[1:]:
        heading = p.splitlines()[0].strip()
        if heading in SECTIONS:
            tb, note, reason, hnotes = _parse_section(p)
            header_warnings.extend(f"Table '{heading}': {n}" for n in hnotes)
            spec = SECTIONS[heading]
            if tb:
                tables[spec["key"]] = {"header": tb[0][0], "rows": tb[0][1]}
            else:
                tables[spec["key"]] = {"header": [], "rows": []}
            notes[spec["key"]] = note
            if not tables[spec["key"]]["rows"]:
                empty[spec["key"]] = reason
        elif heading == "DATA_QUALITY_REPORT":
            tb, _, _, _ = _parse_section(p)
            for header, rows in tb:
                if "Section" in header:
                    for r in rows:
                        try:
                            quality[r["Section"]] = int(float(r["Total Records"]))
                        except (ValueError, TypeError, KeyError):
                            pass
    warnings, errors = validate(tables)
    warnings = header_warnings + warnings
    # cross-check against the file's own quality report
    expected = {
        "job_roles": quality.get("JOB_ROLES"),
        "skills": quality.get("SKILLS"),
        "courses": quality.get("TRAINING_COURSES"),
        "course_skills": quality.get("COURSE_SKILLS"),
        "curriculum": quality.get("CURRICULUM"),
        "trends": quality.get("EMERGING_TRENDS"),
    }
    for k, exp in expected.items():
        got = len(tables.get(k, {}).get("rows", []))
        if exp is not None and exp != got:
            warnings.append(f"Quality-report count for {k} is {exp} but {got} rows parsed")
    counts = {spec["key"]: len(tables.get(spec["key"], {}).get("rows", [])) for spec in SECTIONS.values()}
    return {"tables": tables, "counts": counts, "warnings": warnings, "errors": errors, "empty": empty, "notes": notes, "quality": quality}


def validate(tables):
    warnings, errors = [], []
    ids = {}
    for heading, spec in SECTIONS.items():
        t = tables.get(spec["key"], {"header": [], "rows": []})
        for col in spec["required"]:
            if col not in t["header"]:
                errors.append(f"Table '{heading}': required column '{col}' missing")
        seen = set()
        for r in t["rows"]:
            if spec["pk"]:
                v = r.get(spec["pk"], "")
                if not v:
                    errors.append(f"Table '{heading}': row missing PK {spec['pk']}")
                elif v in seen:
                    errors.append(f"Table '{heading}': duplicate id {v} (skipped on import)")
                seen.add(v)
            else:
                seen.add((r.get("course_id"), r.get("skill_id")))
        ids[spec["key"]] = seen
    courses = {r["course_id"] for r in tables.get("courses", {}).get("rows", []) if r.get("course_id")}
    sk = {r["skill_id"] for r in tables.get("skills", {}).get("rows", []) if r.get("skill_id")}
    for r in tables.get("course_skills", {}).get("rows", []):
        if r.get("course_id") not in courses:
            errors.append(f"FK violation: course_skills.course_id='{r.get('course_id')}' unknown")
        if r.get("skill_id") not in sk:
            errors.append(f"FK violation: course_skills.skill_id='{r.get('skill_id')}' unknown")
    for r in tables.get("curriculum", {}).get("rows", []):
        if r.get("course_id") not in courses:
            errors.append(f"FK violation: curriculum.course_id='{r.get('course_id')}' unknown")
        if r.get("skill_id") not in sk:
            errors.append(f"FK violation: curriculum.skill_id='{r.get('skill_id')}' unknown")
        h = _num(r.get("training_hours"))
        if h is None or h <= 0:
            errors.append(f"Bad training_hours '{r.get('training_hours')}' in {r.get('curriculum_id')}")
    for r in tables.get("course_skills", {}).get("rows", []):
        h = _num(r.get("training_hours"))
        if h is None or h <= 0:
            errors.append(f"Bad training_hours '{r.get('training_hours')}' in course_skills")
    for key in ["job_roles", "skills", "courses", "curriculum", "trends"]:
        pk_col = {"job_roles": "role_id", "skills": "skill_id", "courses": "course_id", "curriculum": "curriculum_id", "trends": "trend_id"}[key]
        for r in tables.get(key, {}).get("rows", []):
            if r.get("is_synthetic") not in (None, "", "0", 0):
                errors.append(f"Non-zero is_synthetic in {key}: {r}")
            if not (r.get("source") or "").strip() or not (r.get("source_url") or "").strip():
                warnings.append(f"Missing provenance in {key} row {r.get(pk_col)}")
    return warnings, errors


if __name__ == "__main__":
    res = parse_dataset()
    print(f"Source: {DATASET_PATH}")
    for heading, spec in SECTIONS.items():
        print(f"  {spec['key']}: {res['counts'][spec['key']]} rows")
    for k, reason in res["empty"].items():
        print(f"  {k}: EMPTY — {reason[:100]}")
    for w in res["warnings"]:
        print(f"WARNING: {w}")
    for e in res["errors"]:
        print(f"ERROR: {e}")
    print(f"{len(res['errors'])} errors, {len(res['warnings'])} warnings")
