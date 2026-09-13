PRAGMA foreign_keys = ON;

-- ============================================================
-- Kaushora Real Public Dataset (canonical source:
-- data/raw/csv/*.csv — 18 CSV files from MoSPI/NSDC/MSDE/DGT/DVET,
-- all rows is_synthetic=0, data_source='REAL'; dataset-provided
-- derived rows keep is_derived=1. The legacy .md catalog it replaces
-- is retained read-only at data/raw/kaushora_real_evidence_dataset.md
-- but is NO LONGER imported (see scripts/archive/).
-- Every metric is OBSERVED (source) or DERIVED (Kaushora-computed).
-- Insufficient data is reported, never fabricated.
-- ============================================================

-- Provenance registry (SRC001..SRC010)
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  organization TEXT,
  dataset_name TEXT,
  dataset_description TEXT,
  source_url TEXT,
  download_url TEXT,
  publication_date TEXT,
  retrieval_date TEXT,
  coverage_start TEXT,
  coverage_end TEXT,
  geographic_coverage TEXT,
  data_type TEXT,
  license_or_usage_note TEXT,
  source_status TEXT,
  data_source TEXT DEFAULT 'REAL'
);

CREATE TABLE IF NOT EXISTS states (
  state_id TEXT PRIMARY KEY,
  state_code TEXT,
  state_name TEXT NOT NULL,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Master district registry (36 Maharashtra districts)
CREATE TABLE IF NOT EXISTS districts (
  district_id TEXT PRIMARY KEY,
  district_code TEXT,
  district_name TEXT NOT NULL,
  state_id TEXT,
  state_name TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (state_id) REFERENCES states(state_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS sectors (
  sector_id TEXT PRIMARY KEY,
  sector_name TEXT NOT NULL,
  sector_description TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS job_roles (
  role_id TEXT PRIMARY KEY,
  job_title TEXT NOT NULL,
  normalized_role TEXT,
  sector TEXT,
  qualification_level TEXT,
  typical_experience TEXT,
  description TEXT,
  related_skills TEXT,
  source TEXT,
  source_url TEXT,
  source_title TEXT,
  publisher TEXT,
  publication_date TEXT,
  data_period TEXT,
  data_type TEXT DEFAULT 'official_dataset',
  is_synthetic INTEGER DEFAULT 0,
  occupation_code TEXT,
  qp_code TEXT,
  qp_name TEXT,
  sector_id TEXT,
  nsqf_level TEXT,
  standard_status TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (sector_id) REFERENCES sectors(sector_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS skills (
  id TEXT PRIMARY KEY,
  skill_name TEXT NOT NULL,
  normalized_skill_name TEXT,
  skill_category TEXT,
  sector TEXT,
  description TEXT,
  technology_status TEXT,
  source TEXT,
  source_url TEXT,
  source_title TEXT,
  publisher TEXT,
  publication_date TEXT,
  data_period TEXT,
  data_type TEXT DEFAULT 'official_report',
  is_synthetic INTEGER DEFAULT 0,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS courses (
  id TEXT PRIMARY KEY,
  course_name TEXT NOT NULL,
  sector TEXT,
  qualification_level TEXT,
  duration TEXT,
  delivery_mode TEXT,
  provider TEXT,
  skills_taught TEXT,
  target_roles TEXT,
  course_status TEXT DEFAULT 'Active',
  source TEXT,
  source_url TEXT,
  source_title TEXT,
  publisher TEXT,
  publication_date TEXT,
  data_period TEXT,
  data_type TEXT DEFAULT 'public_course_data',
  is_synthetic INTEGER DEFAULT 0,
  course_code TEXT,
  sector_id TEXT,
  nsqf_level TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (sector_id) REFERENCES sectors(sector_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS course_skills (
  course_id TEXT,
  skill_id TEXT,
  proficiency TEXT,
  hours INTEGER,
  source TEXT,
  source_url TEXT,
  data_type TEXT DEFAULT 'derived_metric',
  is_synthetic INTEGER DEFAULT 0,
  coverage_level TEXT,
  skill_type TEXT,
  source_id TEXT,
  PRIMARY KEY (course_id, skill_id),
  FOREIGN KEY (course_id) REFERENCES courses(id),
  FOREIGN KEY (skill_id) REFERENCES skills(id)
);

-- Explicit occupation -> skill requirement mapping (observed, NOS-coded)
CREATE TABLE IF NOT EXISTS occupation_skills (
  occupation_id TEXT,
  skill_id TEXT,
  importance TEXT,
  competency_type TEXT,
  nos_code TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  PRIMARY KEY (occupation_id, skill_id),
  FOREIGN KEY (occupation_id) REFERENCES job_roles(role_id),
  FOREIGN KEY (skill_id) REFERENCES skills(id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- QP registry (qualification packs per occupation)
CREATE TABLE IF NOT EXISTS qualifications (
  qualification_id TEXT PRIMARY KEY,
  qualification_name TEXT NOT NULL,
  qp_code TEXT,
  occupation_id TEXT,
  nsqf_level TEXT,
  qualification_status TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (occupation_id) REFERENCES job_roles(role_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS curriculum (
  curriculum_id TEXT PRIMARY KEY,
  course_id TEXT,
  module_name TEXT,
  skill_id TEXT,
  proficiency_level TEXT,
  training_hours INTEGER,
  module_status TEXT DEFAULT 'Active',
  source TEXT,
  source_url TEXT,
  source_title TEXT,
  publisher TEXT,
  publication_date TEXT,
  data_period TEXT,
  data_type TEXT DEFAULT 'official_report',
  is_synthetic INTEGER DEFAULT 0,
  FOREIGN KEY (course_id) REFERENCES courses(id),
  FOREIGN KEY (skill_id) REFERENCES skills(id)
);

CREATE TABLE IF NOT EXISTS trends (
  trend_id TEXT PRIMARY KEY,
  technology TEXT,
  sector TEXT,
  trend_description TEXT,
  evidence TEXT,
  trend_direction TEXT,
  period TEXT,
  source TEXT,
  source_url TEXT,
  source_title TEXT,
  publisher TEXT,
  data_type TEXT DEFAULT 'official_report',
  is_synthetic INTEGER DEFAULT 0
);

-- Dataset-level methodology notes + limitations (one row per section).
CREATE TABLE IF NOT EXISTS dataset_meta (
  section TEXT PRIMARY KEY,
  methodology_note TEXT,
  record_count INTEGER,
  status TEXT
);

CREATE TABLE IF NOT EXISTS skill_aliases (
  alias TEXT PRIMARY KEY,
  skill_id TEXT NOT NULL,
  FOREIGN KEY (skill_id) REFERENCES skills(id)
);

-- Ingestion audit: one row per import run.
CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT DEFAULT (datetime('now')),
  dataset_file TEXT,
  records_imported INTEGER,
  records_rejected INTEGER,
  warnings TEXT,
  status TEXT
);

-- Empty placeholders for future real-data ingestion (NOT populated
-- by the current dataset, which intentionally leaves them empty).
CREATE TABLE IF NOT EXISTS job_postings (
  id TEXT PRIMARY KEY,
  job_title TEXT NOT NULL,
  sector TEXT,
  industry TEXT,
  state TEXT,
  district TEXT,
  city TEXT,
  posting_date TEXT,
  exp_min REAL,
  exp_max REAL,
  employment_type TEXT,
  salary_min REAL,
  salary_max REAL,
  qualification TEXT,
  skill_ids TEXT,
  source_type TEXT,
  source TEXT,
  source_url TEXT,
  data_date TEXT,
  data_type TEXT,
  is_synthetic INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS placements (
  placement_id TEXT PRIMARY KEY,
  course_id TEXT,
  district_id TEXT,
  training_year INTEGER,
  trained INTEGER,
  certified INTEGER,
  placed INTEGER,
  placement_rate REAL,
  median_salary REAL,
  satisfaction REAL,
  data_date TEXT,
  source TEXT,
  data_type TEXT,
  is_synthetic INTEGER DEFAULT 0,
  FOREIGN KEY (course_id) REFERENCES courses(id)
);

-- Real capacity facts (sparse: only districts with published figures).
-- training_seats/enrolments/etc. are NULL where the source does not publish
-- them — NULL means "not published", never zero.
CREATE TABLE IF NOT EXISTS district_capacity (
  district_id TEXT PRIMARY KEY,
  state TEXT,
  district TEXT,
  population_category TEXT,
  major_sectors TEXT,
  training_centres TEXT,
  annual_training_capacity INTEGER,
  estimated_training_demand INTEGER,
  priority_level TEXT,
  source TEXT,
  source_url TEXT,
  data_date TEXT,
  data_type TEXT,
  is_synthetic INTEGER DEFAULT 0,
  scheme TEXT,
  training_seats INTEGER,
  enrolments INTEGER,
  assessments INTEGER,
  certifications INTEGER,
  year INTEGER,
  period TEXT,
  state_id TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (district_id) REFERENCES districts(district_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS training_centres (
  centre_id TEXT PRIMARY KEY,
  centre_name TEXT,
  state TEXT,
  district TEXT,
  city TEXT,
  course_ids TEXT,
  annual_capacity INTEGER,
  current_enrollment INTEGER,
  trainer_count INTEGER,
  equipment_status TEXT,
  source TEXT,
  source_url TEXT,
  data_date TEXT,
  data_type TEXT,
  is_synthetic INTEGER DEFAULT 0,
  district_id TEXT,
  state_id TEXT,
  scheme TEXT,
  provider TEXT,
  centre_type TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (district_id) REFERENCES districts(district_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- PLFS labour-market indicators (state/national level; district_id NULL =
-- not published at district level — never downscaled/invented).
CREATE TABLE IF NOT EXISTS labour_indicators (
  indicator_id TEXT PRIMARY KEY,
  state_id TEXT,
  district_id TEXT,
  year INTEGER,
  period TEXT,
  indicator_name TEXT NOT NULL,
  indicator_value REAL,
  unit TEXT,
  population_group TEXT,
  rural_urban TEXT,
  status_type TEXT,
  source_id TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (state_id) REFERENCES states(state_id),
  FOREIGN KEY (district_id) REFERENCES districts(district_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Citable evidence metrics (observed values with source references).
CREATE TABLE IF NOT EXISTS evidence_metrics (
  evidence_id TEXT PRIMARY KEY,
  metric_name TEXT NOT NULL,
  metric_value TEXT NOT NULL,
  metric_numeric REAL,
  unit TEXT,
  geography TEXT,
  time_period TEXT,
  source_id TEXT,
  source_reference TEXT,
  calculation_method TEXT,
  is_observed INTEGER DEFAULT 1,
  is_derived INTEGER DEFAULT 0,
  confidence_level TEXT,
  notes TEXT,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Skill-demand assessment rows as provided (all signals NULL = honestly
-- insufficient; stored so the insufficiency itself is queryable evidence).
CREATE TABLE IF NOT EXISTS skill_demand (
  skill_demand_id TEXT PRIMARY KEY,
  skill_id TEXT,
  geography TEXT,
  time_period TEXT,
  employment_signal TEXT,
  occupation_signal TEXT,
  training_gap_signal TEXT,
  growth_signal TEXT,
  demand_score REAL,
  demand_status TEXT,
  calculation_method TEXT,
  source_ids TEXT,
  is_derived INTEGER DEFAULT 1,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (skill_id) REFERENCES skills(id)
);

-- District skill-gap assessments as provided (demand missing = Unavailable).
CREATE TABLE IF NOT EXISTS district_skill_gaps (
  gap_id TEXT PRIMARY KEY,
  district_id TEXT,
  skill_id TEXT,
  demand_signal TEXT,
  training_supply_signal TEXT,
  gap_score REAL,
  gap_status TEXT,
  evidence_sources TEXT,
  calculation_method TEXT,
  is_derived INTEGER DEFAULT 1,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (district_id) REFERENCES districts(district_id),
  FOREIGN KEY (skill_id) REFERENCES skills(id)
);

-- Provided reference alignments (is_derived=1 per source file; Kaushora's
-- engine independently recomputes alignment from explicit mappings).
CREATE TABLE IF NOT EXISTS curriculum_alignment_ref (
  alignment_id TEXT PRIMARY KEY,
  course_id TEXT,
  occupation_id TEXT,
  required_skill_count INTEGER,
  covered_skill_count INTEGER,
  missing_skill_count INTEGER,
  alignment_score REAL,
  missing_skills TEXT,
  recommended_updates TEXT,
  source_ids TEXT,
  is_derived INTEGER DEFAULT 1,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (course_id) REFERENCES courses(id),
  FOREIGN KEY (occupation_id) REFERENCES job_roles(role_id)
);

-- Provided recommendations (derived by dataset compiler) + engine rows.
CREATE TABLE IF NOT EXISTS recommendations (
  recommendation_id TEXT PRIMARY KEY,
  district_id TEXT,
  skill_id TEXT,
  occupation_id TEXT,
  recommendation_type TEXT,
  recommendation_text TEXT,
  priority TEXT,
  reason TEXT,
  supporting_evidence TEXT,
  source_ids TEXT,
  is_derived INTEGER DEFAULT 1,
  data_source TEXT DEFAULT 'REAL',
  FOREIGN KEY (district_id) REFERENCES districts(district_id),
  FOREIGN KEY (skill_id) REFERENCES skills(id),
  FOREIGN KEY (occupation_id) REFERENCES job_roles(role_id)
);

-- Genuine user submissions via POST /api/employers/survey (observed).
CREATE TABLE IF NOT EXISTS employer_surveys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employer_name TEXT NOT NULL,
  industry TEXT,
  state TEXT,
  district TEXT,
  job_role TEXT,
  skill_id TEXT,
  skill_name TEXT,
  importance INTEGER,
  required_proficiency TEXT,
  hiring_demand INTEGER,
  difficulty TEXT,
  source TEXT DEFAULT 'user-submission',
  data_type TEXT DEFAULT 'observed',
  is_synthetic INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'viewer'
);

-- Student profiles (normalized; never a single JSON blob).
-- status ∈ School Student, College Student, ITI/Vocational Student,
--          Working, Looking for a Job, Exploring Careers
CREATE TABLE IF NOT EXISTS student_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  status TEXT NOT NULL,
  state_id TEXT,
  district_id TEXT,
  location_text TEXT,
  education_level TEXT,
  course_program TEXT,
  specialization TEXT,
  year_semester TEXT,
  qualification TEXT,
  nsqf_level TEXT,
  goal TEXT,
  FOREIGN KEY (state_id) REFERENCES states(state_id),
  FOREIGN KEY (district_id) REFERENCES districts(district_id)
);

-- Proficiency labels shown to students: Just Started→Basic,
-- Comfortable→Intermediate, Can Apply→Intermediate, Highly Comfortable→Advanced.
CREATE TABLE IF NOT EXISTS student_profile_skills (
  profile_id INTEGER NOT NULL,
  skill_id TEXT NOT NULL,
  proficiency_label TEXT DEFAULT 'Comfortable',
  proficiency_rank TEXT DEFAULT 'Intermediate',
  PRIMARY KEY (profile_id, skill_id),
  FOREIGN KEY (profile_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (skill_id) REFERENCES skills(id)
);

CREATE TABLE IF NOT EXISTS student_profile_interests (
  profile_id INTEGER NOT NULL,
  interest TEXT NOT NULL,
  PRIMARY KEY (profile_id, interest),
  FOREIGN KEY (profile_id) REFERENCES student_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_profile_preferences (
  profile_id INTEGER NOT NULL,
  preference TEXT NOT NULL,
  PRIMARY KEY (profile_id, preference),
  FOREIGN KEY (profile_id) REFERENCES student_profiles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_curriculum_course ON curriculum(course_id);
CREATE INDEX IF NOT EXISTS idx_course_skills_skill ON course_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_skills_sector ON skills(sector);
CREATE INDEX IF NOT EXISTS idx_courses_sector ON courses(sector);
CREATE INDEX IF NOT EXISTS idx_roles_sector ON job_roles(sector);
CREATE INDEX IF NOT EXISTS idx_occ_skills_occ ON occupation_skills(occupation_id);
CREATE INDEX IF NOT EXISTS idx_occ_skills_skill ON occupation_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_indicators_state ON labour_indicators(state_id);
CREATE INDEX IF NOT EXISTS idx_indicators_name ON labour_indicators(indicator_name);
CREATE INDEX IF NOT EXISTS idx_centres_district ON training_centres(district_id);
CREATE INDEX IF NOT EXISTS idx_postings_district ON job_postings(district);
CREATE INDEX IF NOT EXISTS idx_districts_state ON districts(state_id);
CREATE INDEX IF NOT EXISTS idx_courses_nsqf ON courses(nsqf_level);
