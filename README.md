# Kaushora — Labour Market Intelligence & Skill Alignment Platform

> **Data notice:** Kaushora runs on the **Kaushora Real Evidence Dataset**
> (`data/raw/kaushora_real_evidence_dataset.md`) — real, publicly sourced
> records (NCO 2015, SSC NASSCOM / HSSC Qualification Packs, WEF Future of
> Jobs reports). Factual rows carry `is_synthetic=0` with source URLs.
> Sections without accessible public data (job demand, district capacity,
> placements, employer requirements) are intentionally **empty** — the API
> and the frontend return honest `insufficient-data` states instead of
> inventing values. This is a hackathon prototype, not an official labour-market release.

## Purpose

Evidence-based decision support that turns labour-market records into
Demand → Gap → Action intelligence for training authorities, institutes,
employers and candidates. Numbers always come from the SQLite database via
deterministic analytics — never from the frontend, never from the AI layer.

## Architecture

```
data/raw/kaushora_real_evidence_dataset.md
  -> scripts/parse_evidence_dataset.py (parse + validate: PKs, FKs, numerics, provenance)
  -> scripts/import_data.py (transactional, idempotent import -> SQLite)
  -> database/kaushora.db
  -> services/analytics_service.py + skill_gap_service.py (live deterministic calculations)
  -> Flask REST API (routes/) -> frontend / judges / tests
Kaushora AI (services/ai_service.py): DB -> analytics context -> Gemini (optional) or structured fallback.
AI never invents statistics; it only explains backend numbers.
```

## Technology Stack & Rationale

- **Frontend:** HTML/CSS/JavaScript (vanilla) — no framework overhead, instant load, full control for premium SaaS styling. Chosen for hackathon speed and auditability.
- **Visualization:** Chart.js 4.4.1 (vendored `frontend/js/vendor/chart.umd.min.js`) + SVG/CSS — Chart.js for bar/doughnut with tooltips/legends; SVG for custom skill×role matrix, gap bridges, district map. All data-driven, no static image charts.
- **Backend:** Python 3.14 + Flask 3.1 REST API — minimal, reliable, hackathon-proven. Same language as data pipeline.
- **Database:** SQLite (`database/kaushora.db`, git-ignored) — swappable to PostgreSQL via `DATABASE_PATH` env; zero-config for judges.
- **Data pipeline:** Markdown dataset → `scripts/parse_evidence_dataset.py` (validate PKs/FKs/provenance) → `scripts/import_data.py` (transactional, idempotent) → normalized SQLite → `services/` analytics → Flask.
- **AI:** `services/ai_service.py` — retrieves live analytics context → optional Gemini (`GEMINI_API_KEY`) → structured fallback (`fallback_answer`). Never source of numerical truth.
- **Version control:** Git + `.gitignore` (excludes `.env`, `*.db`, `__pycache__`).

## Setup (Windows PowerShell)

```powershell
Set-Location -LiteralPath "C:\Users\ASUS\OneDrive\Desktop\KAUSHORA(FN)"
pip install -r requirements.txt
Copy-Item .env.example .env   # once; set GEMINI_API_KEY inside for live AI
python scripts/init_db.py     # create schema (+ demo users)
python scripts/import_data.py # import canonical dataset (validated, transactional)
python scripts/seed_synthetic.py # add deterministic, labelled demo records for all interactive features
python app.py                 # start server on http://127.0.0.1:5000
```

Re-running `import_data.py` replaces dataset rows without duplicating and
never touches `users` or user-submitted employer surveys. Invalid data
aborts the import with the database untouched (tested).

## Demo login

- `demo@kaushora.in` / `demo123` (admin)
- `employer@demo.in` / `demo123` (employer)

Session-based, hackathon-grade auth only — not production security.

## API endpoints

| Method | Path | Result on current dataset |
|---|---|---|
| GET | /api/health | `{status, database, timestamp}` |
| GET | /api/data/status | record counts, entities, coverage, last ingestion run |
| GET | /api/dashboard/overview | totals, actions, meta (+ honest `insufficient` list) |
| GET | /api/dashboard/demand | skills with `demand_score: null` + reason |
| GET | /api/dashboard/trends | 3 WEF trend signals, empty time series |
| GET | /api/skills `?q=&sector=&status=` | 9 real skills, all `Insufficient Evidence` |
| GET | /api/skills/\<id\> | detail + evidence roles/courses, provenance |
| GET | /api/skills/\<id\>/demand | score/methodology (currently unavailable) |
| GET | /api/skills/\<id\>/gap | required-by roles vs taught-by courses |
| GET | /api/sectors, /api/roles | distinct sectors; 4 NCO roles |
| GET | /api/courses | 3 QPs with alignment score/action |
| GET | /api/courses/\<id\> | course record / 404 |
| GET | /api/courses/\<id\>/alignment | coverage alignment + evidence |
| GET | /api/districts | `[]` (no district records) |
| GET | /api/districts/\<id\> | 404 + reason |
| GET | /api/districts/\<id\>/skills | 404 + reason |
| GET | /api/careers/roles | 4 roles with mappable requirements |
| POST | /api/careers/analyze, /api/career/analyze | role match, missing skills, courses, pathway |
| GET | /api/employers/requirements | user submissions only (`observed`) |
| POST | /api/employers/survey | validated insert (201) / 400 |
| POST | /api/auth/login, /api/auth/logout; GET /api/auth/me | session auth |
| POST | /api/ai/chat | Gemini answer or structured fallback (`ai_available` flag) |

## Analytics methodology

- **Demand:** `overall = normalized_job_demand + normalized_growth_signal +
  normalized_employer_evidence` (missing components omitted, never
  zero-filled). All three inputs are currently empty → every skill reports
  **Insufficient Evidence**; WEF trends shown as qualitative sector signals.
- **Curriculum alignment (coverage):** role requirements text-matched from
  NCO `related_skills` to catalog skills vs QP-taught skills;
  `score = (adequate + 0.5·partial) / required × 100`.
  QP-JSD = 87.5% (Technical Documentation needs deepening: Basic vs
  Intermediate). Courses whose target roles are absent from the catalog
  (QP-DEO, QP-GDA) are marked **Cannot assess**, never scored 0.
- **Career matching:** token-containment skill match,
  `match_score = |have ∩ required| / |required| × 100` (deterministic).
- **Employer survey:** user submissions stored as `data_type='observed'`,
  never merged into source tables.

## Dataset entities actually present (37 rows)

4 job_roles (NCO 2015) · 9 skills (SSC NASSCOM/HSSC QPs) · 3 courses ·
9 course_skills (derived hours) · 9 curriculum modules · 3 emerging trends
(WEF). Empty by design: JOB_DEMAND, TRAINING_CAPACITY,
PLACEMENT_OUTCOMES, EMPLOYER_REQUIREMENTS, DISTRICT_SKILL_DEMAND,
SKILL_DEMAND_AGGREGATION, CURRICULUM_ALIGNMENT, DISTRICT_SKILL_GAPS,
RECOMMENDATIONS. Known file quirks (SKILLS/TRAINING_COURSES/CURRICULUM
headers omit `publication_date` while rows carry it) are handled and
reported as warnings, never silently.

## Testing

```powershell
python tests/test_analytics.py      # deterministic analytics (no server)
python tests/test_data_integrity.py # FKs, provenance, emptiness (no server)
python tests/test_data_import.py    # idempotent re-import + rollback (no server)
python tests/test_api.py            # full API/E2E incl. DB cross-checks (server must run)
```

All suites pass. Invalid-input cases verified: unknown ids → 404, empty
skills → 400, bad survey fields → 400, bad login → 401, empty search → `[]`.

## Kaushora AI Architecture

`POST /api/ai/chat` → `ai_service.ask_ai(question, dashboard_overview())` → builds slim context `{top_skills,totals,actions}` → if `GEMINI_API_KEY` set, calls `generativelanguage.googleapis.com` with prompt `Use ONLY the numbers in CONTEXT. Never invent.` → returns `{answer,ai_available:true}` else `fallback_answer()` → structured evidence summary → `{answer,ai_available:false,note}`. AI outage never breaks dashboard; all non-AI features remain functional.

## Limitations

- Small catalog (37 rows): several NCO roles have no mappable requirements;
  QP-DEO/QP-GDA target roles are absent from the role catalog.
- No district/capacity/placement/employer source evidence → those endpoints
  honestly report unavailability until real sources are ingested.
- Skill-role text matching is token-based and approximate; unmapped phrases
  are always reported in alignment responses.
- No production hardening (single SQLite file, dev server, session auth).

## Scalability Roadmap

Replace SQLite→PostgreSQL (via `DATABASE_PATH` + SQLAlchemy), swap `parse_evidence_dataset.py` for live NCS/API pipelines, add Redis cache for `dashboard_overview`, move to Gunicorn + Nginx, add JWT auth, and ingest real district/placement feeds — frontend needs no rebuild (relative `/api/...`).

## Deployment

Same-origin deployment (Flask serves `frontend/` + `/api/*`) — no CORS, no `localhost` URLs. `frontend/js/api.js` uses relative `/api/...`.

```powershell
# Local/dev (as tested)
python scripts/init_db.py; python scripts/import_data.py; python scripts/seed_synthetic.py; python app.py
# Production (example)
pip install -r requirements.txt
$env:FLASK_DEBUG="false"; $env:GEMINI_API_KEY="..."; python app.py
# or with gunicorn:
# gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

`.env` is git-ignored; `.env.example` documents required vars. No secrets in JS/HTML/README.

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
scripts/parse_evidence_dataset.py  scripts/import_data.py  scripts/init_db.py
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
