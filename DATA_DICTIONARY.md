# Kaushora Data Dictionary

Source files: `data/raw/csv/01–18_*.csv` (cleaned copies in `data/processed/csv/`).
Every row: `is_synthetic=0`, `data_source='REAL'`. `is_derived=1` marks rows the
dataset compiler derived (reference alignments, recommendations, gap/demand
assessments); `is_observed=1` marks direct source values in `evidence_metrics`.

## Registry tables (observed)

| Table | Rows | Key fields |
|---|---|---|
| `sources` | 10 | SRC001–SRC010: MoSPI, NSDC, MSDE, Labour & Employment, DGT, DVET Maharashtra, WEF |
| `states` | 2 | ST001 Maharashtra (code 27), ST002 All India |
| `districts` | 36 | DT001–DT036, all Maharashtra; codes 27-01…27-36; Nagpur = DT019 |
| `sectors` | 13 | SEC001–SEC013 (Agriculture…Healthcare) |
| `skills` | 20 | SKL001–SKL020; `skill_category` ∈ Core/Technical/Occupational/Planning/Compliance; `sector` derived (9 NULL = unmapped, honest) |
| `job_roles` | 32 | OCC001–OCC032; `occupation_code`, `qp_code` (e.g. ELE/Q3106), `qp_name`, `nsqf_level` (3/3.5/4), `sector_id`, `standard_status`; `related_skills` NULL (explicit table supersedes) |
| `qualifications` | 13 | QUA001–QUA013 → OCC001–OCC013, NSQF + status Active |
| `occupation_skills` | 10 | (OCC,SKL) links + `importance` (High/Medium) + `competency_type` + `nos_code`; covers 4 occupations |
| `courses` | 15 | CRS001–CRS015; `course_code` (CTS-*), `provider_name` (ITI Saoner Nagpur / ITI Mumbai), `nsqf_level`, `duration`; `skills_taught` denormalized from mapping; `delivery_mode`/`target_roles` NULL (not in source) |
| `course_skills` | 12 | (CRS,SKL) `coverage_level`=Full + `skill_type`; `proficiency`/`hours` NULL (not published) |
| `training_centres` | 8 | TC001–TC007 Ahilyanagar (PMKVY) + TC008 ITI Saoner Nagpur (CTS); `centre_type`, `provider`, `scheme`; capacity/enrolment NULL (not published) |
| `district_capacity` | 3 | CAP001 Ahilyanagar (12 centres), CAP002 Akola (all NULL), CAP003 Nagpur CTS (120 seats); NULL = not published |
| `labour_indicators` | 15 | LMI001–015: LFPR/WPR/UR (+CWS Dec), `indicator_value` REAL, `district_id` always NULL (no district PLFS published) |
| `evidence_metrics` | 10 | EV001–010 with `metric_value` TEXT + `metric_numeric`, `source_reference`, `is_observed/is_derived`, `confidence_level` |
| `trends` | 3 | WEF TREND-001–003 (preserved real evidence) |

## Assessment tables (provided, honest insufficiency)

| Table | Rows | Content |
|---|---|---|
| `skill_demand` | 1 | DSD001/SKL001: all signals NULL, `demand_status='Unavailable'`, `is_derived=1` |
| `district_skill_gaps` | 1 | GSG001/DT019/SKL001: demand NULL, `gap_status='Unavailable'`, `is_derived=1` |
| `curriculum_alignment_ref` | 5 | CRA001–005: required=covered=2, score 100.0, `is_derived=1` (shown as observed reference) |
| `recommendations` | 3 | REC001–003 with priority/reason/evidence, `is_derived=1` |

## Empty by source (honest)

`job_postings` (0), `placements` (0), `curriculum` (0 modules), source `employer_surveys` (0; only user-observed rows count). `curriculum_alignment`, `district_skill_demand`, `skill_demand_aggregation`, `district_skill_gaps`, `recommendations` legacy meta sections: 0 (superseded by the tables above).

## Observed vs derived (API labels)

- `data_source: "REAL"` on every entity (nothing synthetic remains).
- Derived computations carry methodology text: alignment scores, versatility ranks,
  engine recommendations (`engine:true`), sector derivation, career matches.
- `demand_status: "Insufficient data"`, `capacity_gap: null`, `monthly_postings: []`
  are the honest states for unpublished signals.
