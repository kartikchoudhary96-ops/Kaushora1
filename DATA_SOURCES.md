# Kaushora Data Sources

All sources registered in the `sources` table (SRC001–SRC010) with URLs,
coverage periods and retrieval date 2026-09-11.

| ID | Source | Publisher | Coverage | Records used |
|---|---|---|---|---|
| SRC001 | PLFS Annual Report 2025 | MoSPI | All India + States, 2025 | 10 annual indicators (LFPR/WPR/UR), 5 evidence metrics |
| SRC002 | PLFS Monthly Bulletin Dec 2025 | MoSPI | All India + Rural/Urban, Dec 2025 | 5 CWS indicators |
| SRC003 | NSDC Qualification Packs (PMKVY FY18-20) | NSDC | All India, 2018–20 | 13 occupations, 12 QPs, 10 occupation-skill links (OCC001–003) |
| SRC004 | QP Field Technician – Washing Machine | NSDC | All India | OCC013 + 6 NOS skill links |
| SRC005 | PMKVY 4.0 Maharashtra Training Centres | MSDE | Maharashtra, 31.12.2025 | 36 districts, sectors, 7 centres, capacity row, 684-centre evidence |
| SRC006 | NCS Portal Statistics | Labour & Employment | All India, FY25-26 | 2 evidence metrics (78.86L seekers, 3.43Cr vacancies) |
| SRC007 | PLFS State/District Codes | MoSPI/OpenCity | All India, 2024 | State + district code registry |
| SRC008 | DGT ITI Course Data | DGT | All India | 5 Mumbai ITI courses |
| SRC009 | Maharashtra DVET ITI Data | DVET Maharashtra | Maharashtra, 2024–25 | 10 Saoner ITI courses, 12 course-skill links, ITI Saoner centre, 120-seat capacity, 5 reference alignments, 3 recommendations |
| SRC010 | Skill India Digital Hub | MSDE | All India, 2023–26 | 2900+ courses evidence metric |

## Geographic coverage

- **Maharashtra: 36/36 districts** in registry (DT001 Ahilyanagar … DT036 Palghar).
- **Training presence recorded:** Ahilyanagar (7 PMKVY centres), Nagpur (ITI Saoner + 120 CTS seats).
- **Nagpur (DT019) focus:** best-documented district — ITI Saoner (TC008), CTS capacity (CAP003), 2 recommendations (REC001, REC003), 1 gap assessment (GSG001).
- **34 districts** have registry records but no recorded centres — shown honestly as absence of records.
- Labour indicators are state/national only; **no district-level PLFS exists** in the source and none is downscaled.

## Time coverage

QP/occupation standards 2018–2020 · ITI courses 2024–2026 · PLFS annual 2025 + Dec 2025 monthly · PMKVY snapshot 31.12.2025 · WEF trends 2020–2027 · retrieval 2026-09-11.

## Limitations (carried into the product)

1. No vacancy/job-posting microdata → no per-skill demand scores.
2. No district-level demand or PLFS → no district gaps or disparity index values.
3. No placement/enrolment outcomes → no placement analytics.
4. No source employer requirements → only user-observed submissions.
5. Explicit occupation-skill links for 9/33 occupations (15 links) + QP/NOS evidence (DSRC_* sources, 64 NOS rows, 63 competencies) for 32/33 → improved but partial gap/career coverage; 25 researched skills await taxonomy review.
6. Sparse capacity facts (3 rows, mostly NULL) → capacity shown as recorded, gaps unavailable.
7. No module-level curriculum → coverage via course-skill links only.
