PRAGMA foreign_keys = ON;

-- ============================================================
-- Kaushora Real Evidence Dataset (canonical source:
-- data/raw/kaushora_real_evidence_dataset.md — real, publicly
-- sourced records, is_synthetic=0; derived rows marked
-- data_type='derived_metric'). Empty sections stay EMPTY as
-- future-ingestion placeholders (never populated with fake data).
-- ============================================================

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
  is_synthetic INTEGER DEFAULT 0
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
  is_synthetic INTEGER DEFAULT 0
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
  is_synthetic INTEGER DEFAULT 0
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
  PRIMARY KEY (course_id, skill_id),
  FOREIGN KEY (course_id) REFERENCES courses(id),
  FOREIGN KEY (skill_id) REFERENCES skills(id)
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
  is_synthetic INTEGER DEFAULT 0
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
  is_synthetic INTEGER DEFAULT 0
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

CREATE INDEX IF NOT EXISTS idx_curriculum_course ON curriculum(course_id);
CREATE INDEX IF NOT EXISTS idx_course_skills_skill ON course_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_skills_sector ON skills(sector);
CREATE INDEX IF NOT EXISTS idx_courses_sector ON courses(sector);
CREATE INDEX IF NOT EXISTS idx_roles_sector ON job_roles(sector);
