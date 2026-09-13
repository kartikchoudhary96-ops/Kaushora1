# Kaushora Data Pipeline

```
Supplied files (Downloads/deepseek_csv_20260911_*.txt, CSV content)
  -> data/raw/csv/*.csv            (RAW layer: byte copies, renamed 01-18, NEVER modified)
  -> scripts/parse_csv_dataset.py  (parse + clean + validate -> data/processed/csv/ + quality report)
  -> scripts/import_csv_data.py    (canonical importer -> SQLite, transactional, idempotent)
  -> database/kaushora.db          (normalized, FK-enforced, is_synthetic=0, data_source=REAL)
  -> services/analytics_service.py + skill_gap_service.py + ai_service.py (derived metrics)
  -> Flask REST API (routes/)      (stable contracts + /api/indicators|evidence|recommendations)
  -> frontend/*.html               (fetch -> render; no hardcoded data)
  -> Kaushora AI                   (retrieved DB context -> Gemini or grounded fallback)
```

## Cleaning rules (`parse_csv_dataset.py`)

1. `utf-8-sig`, strip whitespace on every cell.
2. NULL tokens (`''`, `NULL`, `None`, `Not specified`, …) → `NULL`. NULL means
   "not published", never zero. Counts of NULLs per column are reported.
3. `01_sources.csv` ragged rows repaired positionally and logged:
   - SRC002 `geographic_coverage` = `All India,Rural/Urban`;
   - SRC003 `dataset_description` = 3 fragments joined;
   - SRC006 drops stray `Official Government Statistics`, keeps
     `data_type='Employment Portal Statistics'`.
4. `nsqf_level` kept as TEXT (`3.5` preserved).
5. Numerics validated (`indicator_value` float; centre/seat counts int);
   `2900+` → `2900.0` with the approximation note preserved.
6. Names/codes preserved verbatim (incl. parenthetical district aliases).
7. Duplicate PKs or bad FK references are ERRORS — import aborts, DB untouched.
8. Clean copies written to `data/processed/csv/` + `data_quality_report.json`.

## Import rules (`import_csv_data.py`)

- Full REPLACE of the legacy `.md` catalog namespace (`SK-*/NCO-*/QP-*`) with
  source identifiers (`SKL*/OCC*/CRS*/DT*`); `curriculum` cleared (CSV carries
  no module breakdown — coverage lives in `course_skills`).
- `DELETE WHERE is_synthetic=1` on `job_postings`, `placements`,
  `district_capacity`, `training_centres`, `employer_surveys` (purges demo rows;
  observed user surveys and `users` are never touched).
- WEF `trends` preserved via `scripts/restore_wef_trends.py` (real evidence,
  no CSV replacement).
- Skill `sector` derived deterministically: majority linked-occupation sector
  (tie → lowest occupation_id), fallback majority teaching-course sector,
  else NULL (9 skills honestly unmapped).
- Skill aliases rebuilt for the SKL catalog.
- Single transaction; `dataset_meta` refreshed; `ingestion_runs` appended.
- Retired: `scripts/parse_evidence_dataset.py`, `scripts/import_data.py`,
  `scripts/seed_synthetic.py` → moved to `scripts/archive/` (never run;
  the old importer would wipe the new catalog).

## Analytics formulas (all in `services/`, all deterministic)

- `alignment_score = (adequate + 0.5 × partial) / required × 100`, where
  required = explicit NOS `occupation_skills` of the best same-sector match
  (ratio desc, overlap desc, id asc); cross-sector pairings never scored.
- Industry proficiency: observed surveys (majority, ties to lower rank) →
  else importance map High→Advanced/Medium→Intermediate → else Intermediate.
- Curriculum proficiency baseline Intermediate for Full coverage (documented
  convention; no per-skill proficiency published).
- Demand: no score (source assessment NULL) → `demand_status='Insufficient data'`.
- District gap: `capacity_gap = NULL` (demand unpublished); centres/capacity
  shown as recorded.
- Match score (careers): `|have ∩ required| / |required| × 100`.
