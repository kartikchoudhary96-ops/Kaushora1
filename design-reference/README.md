# Design references (Stitch-generated specifications)

> These files are **visual specifications, NOT website assets**.
> They are never served by the app (`app.py` only serves `frontend/`),
> never embedded as images, and none of their numbers are copied —
> every figure in the UI comes from the live backend instead.

| File | Page it specifies | Status |
|---|---|---|
| `01-dashboard-labour-market-intelligence.jpg` | `frontend/dashboard.html` | Implemented (layout, KPI row, demand landscape, mismatch table, trends, evidence strip) |
| `02-kaushora-ai.jpg` | `frontend/ai.html` | Implemented (presets, chat, Data Inspector, synthesis pipeline) |
| `03-skill-intelligence.jpg` | `frontend/skills.html` + `frontend/skill-detail.html` | Implemented (search, filters, profiles table, dossier) |

## Adherence notes (deliberate deviations)

The screenshots depict a fictional large-scale deployment (1,420 skills,
64,280 vacancies, 34 districts, demand scores, growth percentages). The real
dataset has 9 skills, 3 courses, 4 roles, 3 trends and **zero** demand /
district / placement records, so those widgets are rebuilt as honest
equivalents:

- Fake counters → live catalog counts with source labels.
- Demand scores / growth momentum → "Insufficient Evidence" states + methodology.
- District penetration / TVET capacity bars → empty states naming the missing tables.
- Export/PDF/proposal/share buttons → omitted (no backend support; no dead controls).
- Pagination → omitted (9-row catalog fits one honest table).

## Assets now integrated (2026-09-05)

All 6 real PNGs have been supplied, converted to true PNGs and wired:

`frontend/assets/kaushora-logo.png` (118 KB) → `shell.js` + `index.html` brand
`frontend/assets/kaushora-icon.png` (834 KB) → reserved icon/mark
`frontend/assets/favicon.png` (736 KB) → `shell.js` + `index.html` favicon (SVG kept as fallback)
`frontend/assets/hero-illustration.png` (481 KB) → `index.html` hero
`frontend/assets/feature-illustration-1.png` (550 KB) → `index.html` Demand→Gap→Action panel
`frontend/assets/district-map.png` (1.3 MB) → `districts.html` + dashboard disparity

All serve `HTTP 200`. SVG recreations remain as `onerror` fallbacks, so no
broken image is possible. `frontend/assets/brand.svg` etc. are retained as
fallbacks only.
