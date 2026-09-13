# Kaushora — Labour Market Intelligence & Skill Alignment Platform

> **Data notice:** Kaushora runs on a **real public dataset** — 18 CSV files
> (`data/raw/csv/`) from PLFS/MoSPI, NSDC, PMKVY/MSDE, NCS, DGT, DVET
> Maharashtra and WEF: 36 Maharashtra districts, 32 NSDC occupations, 20
> skills, 15 ITI courses, 15 labour indicators, 10 evidence metrics.
> Every row is `is_synthetic=0, data_source='REAL'`. Where the source
> publishes nothing (per-skill demand, district demand, placements, employer
> requirements), the product shows **Insufficient data** — never estimates.
> Derived metrics are labeled **Derived by Kaushora** with formulas in
> `DATA_PIPELINE.md`. This is a hackathon prototype, not official statistics.

## 1. Kaushora overview

Kaushora is a labour-market intelligence and skill-alignment platform for
Maharashtra: it turns public records (PLFS indicators, NSDC qualification
packs, PMKVY/DVET training presence, ITI courses) into skill registries,
curriculum alignment, district intelligence, career guidance and grounded AI
answers — every figure traced to its source row.

## 2. Problem being solved

Skill-development programmes are often designed from broad or historical
categories that lag changing technologies, local demand and employer
expectations, while trainees complete courses with limited placement
potential. Kaushora provides the continuous evidence loop the problem
statement demands: Demand → Gap → Action, where each action carries an
evidence trail back to real records.

## 3. Architecture

```
Real Dataset (18 CSV: PLFS/NSDC/MSDE/DGT/DVET/WEF)
  ↓ Raw Data (data/raw/csv/, byte copies, never modified)
  ↓ Cleaning and Normalization (scripts/parse_csv_dataset.py → data/processed/csv/)
  ↓ Database (scripts/import_csv_data.py → SQLite, FK-enforced, transactional)
  ↓ Backend Analytics (services/: observed vs derived, deterministic)
  ↓ REST API (routes/: stable contracts + /api/indicators|evidence|recommendations)
  ↓ Frontend (fetch → render; no hardcoded data)
  ↓ Dynamic Charts and Infographics (Chart.js + SVG, all API-driven)
  ↓ Kaushora AI (retrieved DB context → Gemini or grounded fallback)
```

## Technology Stack & Rationale

- **Frontend:** HTML/CSS/JavaScript (vanilla) — no framework overhead, instant load, full control for premium SaaS styling. Chosen for hackathon speed and auditability.
- **Visualization:** Chart.js 4.4.1 (vendored `frontend/js/vendor/chart.umd.min.js`) + SVG/CSS — Chart.js for bar/doughnut with tooltips/legends; SVG for custom skill×role matrix, gap bridges, district map. All data-driven, no static image charts.
- **Backend:** Python 3.14 + Flask 3.1 REST API — minimal, reliable, hackathon-proven. Same language as data pipeline.
- **Database:** SQLite (`database/kaushora.db`, git-ignored) — swappable to PostgreSQL via `DATABASE_PATH` env; zero-config for judges.
- **Data pipeline:** 18 CSV files → `scripts/parse_csv_dataset.py` (validate PKs/FKs/provenance, ragged-row repair) → `scripts/import_csv_data.py` (transactional, idempotent) → normalized SQLite → `services/` analytics → Flask.
- **AI:** `services/ai_service.py` — retrieves live DB records (indicators, alignments, districts, recommendations) → optional Gemini (`GEMINI_API_KEY`) → deterministic grounded fallback. Never source of numerical truth.
- **Version control:** Git + `.gitignore` (excludes `.env`, `*.db`, `__pycache__`).

## Technology Stack & Rationale

- **Frontend:** HTML/CSS/JavaScript (vanilla) — no framework overhead, instant load, full control for premium SaaS styling. Chosen for hackathon speed and auditability.
- **Visualization:** Chart.js 4.4.1 (vendored `frontend/js/vendor/chart.umd.min.js`) + SVG/CSS — Chart.js for bar/doughnut with tooltips/legends; SVG for custom skill×role matrix, gap bridges, district map. All data-driven, no static image charts.
- **Backend:** Python 3.14 + Flask 3.1 REST API — minimal, reliable, hackathon-proven. Same language as data pipeline.
- **Database:** SQLite (`database/kaushora.db`, git-ignored) — swappable to PostgreSQL via `DATABASE_PATH` env; zero-config for judges.
- **Data pipeline:** Markdown dataset → `scripts/parse_evidence_dataset.py` (validate PKs/FKs/provenance) → `scripts/import_data.py` (transactional, idempotent) → normalized SQLite → `services/` analytics → Flask.
- **AI:** `services/ai_service.py` — retrieves live analytics context → optional Gemini (`GEMINI_API_KEY`) → structured fallback (`fallback_answer`). Never source of numerical truth.
- **Version control:** Git + `.gitignore` (excludes `.env`, `*.db`, `__pycache__`).

## 6. Setup & 8. Running locally (Windows PowerShell)

```powershell
Set-Location -LiteralPath "C:\Users\ASUS\OneDrive\Desktop\KAUSHORA(FN)"
pip install -r requirements.txt
Copy-Item .env.example .env   # once; set GEMINI_API_KEY inside for live AI
python scripts/init_db.py       # create schema (+ demo users)
python scripts/import_csv_data.py  # import canonical CSV dataset (validated, transactional)
python scripts/restore_wef_trends.py  # restore 3 real WEF trend rows (once)
python app.py                   # start server on http://127.0.0.1:5000
```

Re-running `import_csv_data.py` replaces dataset rows without duplicating and
never touches `users` or observed employer surveys. Validation failure aborts
with the database untouched (tested). Retired scripts live in
`scripts/archive/` and must not be run (the old importer would wipe the catalog).

## 7. Dataset ingestion

`parse_csv_dataset.py`: loads 18 CSVs → strips whitespace → NULL tokens to
NULL (never zero-filled) → repairs 3 ragged `01_sources` rows (logged) →
validates PK uniqueness, FK references, numerics, source refs → writes
`data/processed/csv/` + `data_quality_report.json` (0 errors).
`import_csv_data.py`: enriches provenance from the `sources` table, derives
skill sectors deterministically, rebuilds aliases, refreshes `dataset_meta`,
appends `ingestion_runs` — all in one transaction.

## 9. Environment variables

See `.env.example` (no secrets committed): `FLASK_SECRET_KEY`,
`GEMINI_API_KEY` (optional — AI falls back gracefully without it),
`GEMINI_MODEL`, `DATABASE_PATH`, `PORT`, `FLASK_DEBUG` (dev only).

## Demo login

- `demo@kaushora.in` / `demo123` (admin)
- `employer@demo.in` / `demo123` (employer)

Session-based, hackathon-grade auth only — not production security.

## 10. API overview

| Method | Path | Result on current dataset |
|---|---|---|
| GET | /api/health | `{status, database, timestamp}` |
| GET | /api/data/status | 23 tables' counts, entities, coverage, last ingestion run |
| GET | /api/dashboard/overview | totals (20/15/32/36/8), sector/district composition, actions, evidence |
| GET | /api/dashboard/demand | 20 skills, all `demand_score: null` + honest reason |
| GET | /api/dashboard/trends | 3 WEF signals, empty time series + note |
| GET | /api/indicators `?state_id=` | 15 PLFS rows (state/national; district NULL = unpublished) |
| GET | /api/evidence | 10 citable metrics with source references |
| GET | /api/recommendations | 3 provided + engine rows (`engine:true`) |
| GET | /api/skills `?q=&sector=&status=` | 20 real skills, all `Insufficient data` |
| GET | /api/skills/\<id\> | detail + explicit occupation evidence + provenance + `data_source` |
| GET | /api/skills/\<id\>/demand | null score + honest methodology |
| GET | /api/skills/\<id\>/gap | required-by vs taught-by from explicit mappings |
| GET | /api/sectors, /api/roles | 13 sectors; 32 NSDC occupations |
| GET | /api/courses | 15 ITI courses with engine alignment |
| GET | /api/courses/\<id\> | course record / 404 |
| GET | /api/courses/\<id\>/alignment | engine score + provided reference pairs |
| GET | /api/districts | 36 districts + centre counts |
| GET | /api/districts/\<id\> | centres, capacity facts, recs, gaps, state indicators |
| GET | /api/careers/roles | 32 roles (4 scorable via explicit links) |
| POST | /api/careers/analyze, /api/career/analyze | role match, missing skills, courses, pathway |
| GET | /api/employers/requirements | user submissions only (`observed`) |
| POST | /api/employers/survey | validated insert (201) / 400 |
| POST | /api/auth/login, /api/auth/logout; GET /api/auth/me | session auth |
| POST | /api/ai/chat | `{answer, evidence[], data_source, grounded, ai_available, note}` |

## 11. Analytics methodology (observed vs derived)

- **Demand (INSUFFICIENT):** source `skill_demand` row is NULL for every
  signal → `demand_score=null`, `demand_status='Insufficient data'`. Macro
  aggregates are evidence only, never converted to skill scores.
- **Curriculum alignment (DERIVED):** required = explicit NOS
  `occupation_skills` of the best same-sector match (ratio, overlap, id);
  `score = (adequate + 0.5·partial) / required × 100`. E.g. CRS001 vs
  OCC013 = 8.3%; provided CRA reference pairs shown alongside. Cross-sector
  pairings never scored; unmappable courses → `Cannot assess`.
- **Proficiency:** observed surveys (deterministic majority, ties to lower
  rank), else importance High→Advanced/Medium→Intermediate; curriculum
  baseline Intermediate for Full coverage (documented convention).
- **Career matching (DERIVED):** `match_score = |have ∩ required| /
  |required| × 100`, deterministic; unmapped roles listed as unscored.
- **District gaps (INSUFFICIENT):** demand unpublished → `capacity_gap=null`;
  recorded centres/capacity shown as-is.
- **Employer survey:** user submissions stored as `data_type='observed'`,
  never merged into source tables.
- **Recommendations:** 3 provided derivations + deterministic engine rows
  (`Collect data` for NULL-seat districts, `Map requirements` for unmapped
  occupations), all `data_source=REAL`, engine rows flagged.

## 4. Folder structure (relevant parts)

`data/raw/csv/` (raw, never modified) · `data/processed/csv/` (cleaned +
`data_quality_report.json`) · `scripts/{parse_csv_dataset,import_csv_data,init_db,restore_wef_trends}.py`
(+ `archive/` retired) · `database/schema.sql` · `services/` · `routes/` ·
`frontend/` · `tests/` · `DATA_{PIPELINE,DICTIONARY,SOURCES}.md`

## Testing

```powershell
python tests/test_analytics.py      # deterministic analytics (no server)
python tests/test_data_integrity.py # FKs, provenance, emptiness (no server)
python tests/test_data_import.py    # idempotent re-import + rollback (no server)
python tests/test_api.py            # full API/E2E incl. DB cross-checks (server must run)
```

All suites pass. Invalid-input cases verified: unknown ids → 404, empty
skills → 400, bad survey fields → 400, bad login → 401, empty search → `[]`.

## 12. Kaushora AI architecture

`POST /api/ai/chat` → `ai_service.build_context()` retrieves live records
(totals, weakest alignments, districts with centres, PLFS indicators,
evidence metrics, recommendations, skill catalog, trends) → if
`GEMINI_API_KEY` set, calls `generativelanguage.googleapis.com` with the
system prompt *"Use only the provided Kaushora context… Do not invent…
If insufficient, state so"* → `{answer, evidence[], data_source:REAL,
grounded:true, ai_available:true}`; else deterministic `fallback_answer()`
keyword-routed to the same live context → `{…, ai_available:false}`. AI
outage never breaks dashboard; all non-AI features remain functional. The
model never sees raw user data beyond the question and never fabricates —
fallback cites NULL signals explicitly.

## 13. Limitations

- Per-skill demand, district demand, placements, employer requirements:
  unpublished in source → honest insufficient states (no estimates).
- Explicit occupation-skill links cover 4/32 occupations → partial gap and
  career coverage (28 roles unscored, stated).
- Sparse capacity facts (3 rows, mostly NULL) → recorded as-is, gaps unavailable.
- Skill sectors derived for 11/20 skills; 9 honestly unmapped.
- No production hardening (single SQLite file, dev server, session auth).

## 14. Scalability roadmap

Replace SQLite→PostgreSQL (via `DATABASE_PATH` + SQLAlchemy), add live
PLFS/NCS/API pipelines beside the CSV importer, Redis cache for
`dashboard_overview`, Gunicorn + Nginx, JWT auth, district/placement feeds
as published — frontend needs no rebuild (relative `/api/...`).

## 15. Deployment instructions

Same-origin deployment (Flask serves `frontend/` + `/api/*`) — no CORS, no
`localhost` URLs. `frontend/js/api.js` uses relative `/api/...`.

```powershell
# Local/dev (as tested)
python scripts/init_db.py; python scripts/import_csv_data.py; python scripts/restore_wef_trends.py; python app.py
# Production (example)
pip install -r requirements.txt
$env:FLASK_DEBUG="false"; $env:GEMINI_API_KEY="..."; python app.py
# or with gunicorn:
# gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

`.env` is git-ignored; `.env.example` documents required vars. No secrets in JS/HTML/README.
Remaining deployment step: choose a host (Render/Railway/VM), set env vars,
run the four commands above — nothing else is provider-specific.

## Frontend (Part 2) — premium UI, zero fake data

Twelve working pages in `frontend/`, styled from the Stitch design
references (cream canvas, pistachio accent, charcoal ink, sidebar +
topbar shell). Every metric, chart, table and recommendation is fetched
through the shared client `frontend/js/api.js` — grep-verified free of
hardcoded numbers, `Math.random`, mock arrays and placeholder records.

| Page | File | Live data source |
|---|---|---|
| Landing | `index.html` | `data/status`, `dashboard/overview` (hero stats, snapshot) |
| Dashboard | `dashboard.html` | `overview`, `courses`, `careers/roles`, `skills`, `trends`, `data/status` + Chart.js sector/coverage charts + SVG skill×role matrix |
| Skills | `skills.html` | `skills`, `sectors` (working search + filters) |
| Skill detail | `skill-detail.html?id=` | `skills/<id>`, `/demand`, `/gap` + gap-bridge chart + provenance |
| Courses | `courses.html` | `courses` (sector + alignment-band filters) |
| Course detail | `course-detail.html?id=` | `courses/<id>/alignment` + coverage doughnut, ADD/UPDATE lists |
| Districts | `districts.html` | `districts` → honest empty state + schematic map |
| District detail | `district-detail.html?id=` | `districts/<id>` → honest 404 state |
| Careers | `careers.html` | `sectors` + `POST careers/analyze` (meters, pathway, unscored-roles log) |
| Employers | `employers.html` | `POST employers/survey` (validated) + `employers/requirements` |
| Kaushora AI | `ai.html` | `POST ai/chat` + live Data Inspector from `data/status` |
| Login | `login.html` | `auth/login|logout|me` (prototype session auth) |

Shared: `css/design.css` (design system), `js/api.js` (central client),
`js/icons.js` (inline-SVG icon set), `js/shell.js` (sidebar/topbar/active
nav/session chip/skeletons/empty+error states), `js/vendor/chart.umd.min.js`
(Chart.js 4.4.1 vendored — works offline). The Stitch layout specs live in
`design-reference/` (see its README for the page mapping and the deliberate
deviations where the screenshots show data the dataset does not have).
Brand visuals in `frontend/assets/` are now **real PNGs** (`kaushora-logo.png`,
`kaushora-icon.png`, `favicon.png`, `hero-illustration.png`,
`feature-illustration-1.png`, `district-map.png`) converted to true PNGs and
verified `HTTP 200`; SVG recreations (`brand.svg`, `icon.svg`, `favicon.svg`,
`hero.svg`, `feature-gap.svg`, `district-map.svg`) remain as `onerror`
fallbacks so no image can break.

Run the complete application:

```powershell
Set-Location -LiteralPath "C:\Users\ASUS\OneDrive\Desktop\KAUSHORA(FN)"
pip install -r requirements.txt
python scripts/init_db.py; python scripts/import_data.py; python scripts/seed_synthetic.py
python app.py   # open http://127.0.0.1:5000
```

## Project layout

```
app.py  requirements.txt  .env.example  README.md
data/raw/kaushora_real_evidence_dataset.md
database/schema.sql  database/kaushora.db (generated, git-ignored)
scripts/{parse_csv_dataset,import_csv_data,init_db,restore_wef_trends}.py  (+ archive/ retired)
services/db.py  services/data_service.py  services/analytics_service.py
services/skill_gap_service.py  services/curriculum_service.py  services/ai_service.py
routes/*_routes.py (health, data, skill, course, district, career, employer, ai)
tests/test_analytics.py  tests/test_data_import.py  tests/test_data_integrity.py  tests/test_api.py
frontend/index.html  frontend/dashboard.html  frontend/skills.html  frontend/skill-detail.html
frontend/courses.html  frontend/course-detail.html  frontend/districts.html  frontend/district-detail.html
frontend/careers.html  frontend/employers.html  frontend/ai.html  frontend/login.html
frontend/css/design.css  frontend/js/{api,icons,shell}.js  frontend/js/vendor/chart.umd.min.js
frontend/assets/*.png (kaushora-logo, kaushora-icon, favicon, hero-illustration, feature-illustration-1, district-map) + *.svg fallbacks
design-reference/*.jpg (Stitch specs, not served)
```
