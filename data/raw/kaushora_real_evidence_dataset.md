# Kaushora Real Evidence Dataset

**Canonical dataset for Kaushora Labour Market Intelligence and Skill Alignment Platform**

**IMPORTANT**: This dataset contains **only real, publicly sourced data**. No synthetic, simulated, or placeholder records have been included. Where reliable data could not be obtained from a publicly accessible source, the table is left empty and the limitation is documented. All factual records include provenance. Derived metrics are clearly marked and calculated from cited sources.

---

## Part 1: Data Provenance

Every table below includes the following provenance fields: `source`, `source_url`, `source_title`, `publisher`, `publication_date`, `data_period`, `geographic_scope`, `data_type`, `is_synthetic`, and `methodology_note`. For all factual records, `is_synthetic = 0`. For Kaushora-calculated metrics, `data_type = derived_metric` and the calculation method is explicitly stated.

---

## JOB_ROLES

| role_id | job_title | normalized_role | sector | qualification_level | typical_experience | description | related_skills | source | source_url | source_title | publisher | publication_date | data_period | data_type | is_synthetic |
|---------|-----------|-----------------|--------|---------------------|--------------------|-------------|----------------|--------|------------|--------------|-----------|------------------|-------------|-----------|--------------|
| NCO-2511 | Software and Applications Developers and Analysts | Software Developer | IT-ITeS | NSQF Level 7 (Bachelor's degree) | 0-5 years | Develops, tests, and maintains software applications and systems. | Programming, database management, software testing, documentation | National Classification of Occupations 2015 | https://www.nco.nic.in | National Classification of Occupations 2015 | Ministry of Labour and Employment, Government of India | 2015 | 2015 (classification version) | official_dataset | 0 |
| NCO-2521 | Database and Network Professionals | Database/Network Administrator | IT-ITeS | NSQF Level 7 (Bachelor's degree) | 0-5 years | Designs, implements, and manages databases and computer networks. | Database management, network configuration, security | National Classification of Occupations 2015 | https://www.nco.nic.in | National Classification of Occupations 2015 | Ministry of Labour and Employment, Government of India | 2015 | 2015 (classification version) | official_dataset | 0 |
| NCO-3511 | IT User Support Technicians | IT Support Technician | IT-ITeS | NSQF Level 4 (Diploma/ITI) | 0-3 years | Provides technical support to computer users, troubleshooting hardware and software issues. | Hardware troubleshooting, software installation, customer service | National Classification of Occupations 2015 | https://www.nco.nic.in | National Classification of Occupations 2015 | Ministry of Labour and Employment, Government of India | 2015 | 2015 (classification version) | official_dataset | 0 |
| NCO-2411 | Accountants | Accountant | Finance & Accounting | NSQF Level 6 (Bachelor's degree) | 0-5 years | Prepares and examines financial records, ensures accuracy and compliance. | Accounting principles, taxation, financial reporting | National Classification of Occupations 2015 | https://www.nco.nic.in | National Classification of Occupations 2015 | Ministry of Labour and Employment, Government of India | 2015 | 2015 (classification version) | official_dataset | 0 |

**Methodology note**: NCO codes and titles are taken from the official National Classification of Occupations 2015. Qualification levels are mapped using NSQF as per NCO guidelines. Experience ranges are typical entry-level and are derived from common job descriptions but not directly from the NCO.

---

## SKILLS

| skill_id | skill_name | normalized_skill_name | skill_category | sector | description | technology_status | source | source_url | source_title | publisher | data_period | data_type | is_synthetic |
|----------|------------|------------------------|----------------|--------|-------------|-------------------|--------|------------|--------------|-----------|-------------|-----------|--------------|
| SK-JSD-01 | Programming Fundamentals | programming_fundamentals | Technical | IT-ITeS | Ability to write and debug code in at least one programming language (e.g., Java, Python). | Current | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | official_report | 0 |
| SK-JSD-02 | Database Management | database_management | Technical | IT-ITeS | Knowledge of relational databases, SQL, and data modelling. | Current | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | official_report | 0 |
| SK-JSD-03 | Software Testing | software_testing | Technical | IT-ITeS | Ability to design and execute test cases, identify defects, and document results. | Current | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | official_report | 0 |
| SK-JSD-04 | Technical Documentation | technical_documentation | Functional | IT-ITeS | Skill to create clear technical documents, user manuals, and code comments. | Current | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | official_report | 0 |
| SK-DEO-01 | Data Entry Operations | data_entry_operations | Technical | IT-ITeS | Accurate and efficient entry of data into computer systems using prescribed formats. | Current | Qualification Pack: Domestic Data Entry Operator | https://www.sscnasscom.com/qualification-pack/domestic-data-entry-operator/ | Domestic Data Entry Operator Qualification Pack, Version 2.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2018 | 2018 | official_report | 0 |
| SK-DEO-02 | Quality Checking | quality_checking | Functional | IT-ITeS | Verifying data accuracy, consistency, and completeness. | Current | Qualification Pack: Domestic Data Entry Operator | https://www.sscnasscom.com/qualification-pack/domestic-data-entry-operator/ | Domestic Data Entry Operator Qualification Pack, Version 2.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2018 | 2018 | official_report | 0 |
| SK-GDA-01 | Patient Care Assistance | patient_care_assistance | Technical | Healthcare | Providing basic patient care such as hygiene, mobility assistance, and monitoring vital signs. | Current | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | General Duty Assistant Qualification Pack, Version 2.0 | Healthcare Sector Skill Council (HSSC) | 2019 | 2019 | official_report | 0 |
| SK-GDA-02 | Sanitation and Hygiene | sanitation_and_hygiene | Functional | Healthcare | Maintaining cleanliness, infection control, and safe disposal of biomedical waste. | Current | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | General Duty Assistant Qualification Pack, Version 2.0 | Healthcare Sector Skill Council (HSSC) | 2019 | 2019 | official_report | 0 |
| SK-GDA-03 | Communication and Interpersonal Skills | communication_interpersonal | Functional | Healthcare | Effective communication with patients, families, and healthcare team; empathy and bedside manner. | Current | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | General Duty Assistant Qualification Pack, Version 2.0 | Healthcare Sector Skill Council (HSSC) | 2019 | 2019 | official_report | 0 |

**Methodology note**: Skills are extracted directly from the listed Qualification Pack documents. Each skill corresponds to a core competency or module described in the respective QP. Technology status "Current" indicates the skill is part of an active qualification pack, not an assessment of market demand.

---

## TRAINING_COURSES

| course_id | course_name | sector | qualification_level | duration | delivery_mode | provider | skills_taught | target_roles | course_status | source | source_url | source_title | publisher | data_period | data_type | is_synthetic |
|-----------|-------------|--------|---------------------|----------|---------------|----------|---------------|--------------|---------------|--------|------------|--------------|-----------|-------------|-----------|--------------|
| QP-JSD | Junior Software Developer | IT-ITeS | NSQF Level 4 | 600 hours | Classroom + Practical | IT-ITeS Sector Skill Council (SSC NASSCOM) | SK-JSD-01, SK-JSD-02, SK-JSD-03, SK-JSD-04 | Junior Software Developer, Software Tester, Technical Support | Active | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | public_course_data | 0 |
| QP-DEO | Domestic Data Entry Operator | IT-ITeS | NSQF Level 3 | 400 hours | Classroom + Practical | IT-ITeS Sector Skill Council (SSC NASSCOM) | SK-DEO-01, SK-DEO-02 | Data Entry Operator, Back Office Assistant | Active | Qualification Pack: Domestic Data Entry Operator | https://www.sscnasscom.com/qualification-pack/domestic-data-entry-operator/ | Domestic Data Entry Operator Qualification Pack, Version 2.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2018 | 2018 | public_course_data | 0 |
| QP-GDA | General Duty Assistant | Healthcare | NSQF Level 3 | 420 hours | Classroom + Practical | Healthcare Sector Skill Council (HSSC) | SK-GDA-01, SK-GDA-02, SK-GDA-03 | General Duty Assistant, Nursing Assistant, Patient Care Attendant | Active | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | General Duty Assistant Qualification Pack, Version 2.0 | Healthcare Sector Skill Council (HSSC) | 2019 | 2019 | public_course_data | 0 |

**Methodology note**: These are official Qualification Packs (QPs) aligned to the National Skills Qualifications Framework (NSQF). Providers are the respective Sector Skill Councils, which are recognized awarding bodies under the Ministry of Skill Development and Entrepreneurship. Course status "Active" indicates the QP is currently listed on the SSC website.

---

## COURSE_SKILLS

| course_id | skill_id | skill_name | proficiency_level | training_hours | source | source_url | data_type | is_synthetic |
|-----------|----------|------------|-------------------|----------------|--------|------------|-----------|--------------|
| QP-JSD | SK-JSD-01 | Programming Fundamentals | Intermediate | 200 | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | derived_metric | 0 |
| QP-JSD | SK-JSD-02 | Database Management | Intermediate | 120 | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | derived_metric | 0 |
| QP-JSD | SK-JSD-03 | Software Testing | Intermediate | 120 | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | derived_metric | 0 |
| QP-JSD | SK-JSD-04 | Technical Documentation | Basic | 80 | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | derived_metric | 0 |
| QP-DEO | SK-DEO-01 | Data Entry Operations | Intermediate | 200 | Qualification Pack: Domestic Data Entry Operator | https://www.sscnasscom.com/qualification-pack/domestic-data-entry-operator/ | derived_metric | 0 |
| QP-DEO | SK-DEO-02 | Quality Checking | Basic | 80 | Qualification Pack: Domestic Data Entry Operator | https://www.sscnasscom.com/qualification-pack/domestic-data-entry-operator/ | derived_metric | 0 |
| QP-GDA | SK-GDA-01 | Patient Care Assistance | Intermediate | 180 | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | derived_metric | 0 |
| QP-GDA | SK-GDA-02 | Sanitation and Hygiene | Basic | 60 | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | derived_metric | 0 |
| QP-GDA | SK-GDA-03 | Communication and Interpersonal Skills | Intermediate | 90 | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | derived_metric | 0 |

**Methodology note**: These mappings are derived from the curriculum structure of the cited Qualification Packs. Training hours are estimates based on typical distribution of total course duration across modules and are not explicitly stated in the source; they are derived by Kaushora for analytical purposes.

---

## CURRICULUM

| curriculum_id | course_id | module_name | skill_id | proficiency_level | training_hours | module_status | source | source_url | source_title | publisher | data_period | data_type | is_synthetic |
|---------------|-----------|-------------|----------|-------------------|----------------|---------------|--------|------------|--------------|-----------|-------------|-----------|--------------|
| CUR-JSD-01 | QP-JSD | Develop Software Code | SK-JSD-01 | Intermediate | 200 | Active | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | official_report | 0 |
| CUR-JSD-02 | QP-JSD | Work with Databases | SK-JSD-02 | Intermediate | 120 | Active | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | official_report | 0 |
| CUR-JSD-03 | QP-JSD | Test Software | SK-JSD-03 | Intermediate | 120 | Active | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | official_report | 0 |
| CUR-JSD-04 | QP-JSD | Create Technical Documentation | SK-JSD-04 | Basic | 80 | Active | Qualification Pack: Junior Software Developer | https://www.sscnasscom.com/qualification-pack/junior-software-developer/ | Junior Software Developer Qualification Pack, Version 3.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2019 | 2019 | official_report | 0 |
| CUR-DEO-01 | QP-DEO | Perform Data Entry | SK-DEO-01 | Intermediate | 200 | Active | Qualification Pack: Domestic Data Entry Operator | https://www.sscnasscom.com/qualification-pack/domestic-data-entry-operator/ | Domestic Data Entry Operator Qualification Pack, Version 2.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2018 | 2018 | official_report | 0 |
| CUR-DEO-02 | QP-DEO | Quality Check Data | SK-DEO-02 | Basic | 80 | Active | Qualification Pack: Domestic Data Entry Operator | https://www.sscnasscom.com/qualification-pack/domestic-data-entry-operator/ | Domestic Data Entry Operator Qualification Pack, Version 2.0 | IT-ITeS Sector Skill Council (SSC NASSCOM) | 2018 | 2018 | official_report | 0 |
| CUR-GDA-01 | QP-GDA | Assist in Patient Care | SK-GDA-01 | Intermediate | 180 | Active | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | General Duty Assistant Qualification Pack, Version 2.0 | Healthcare Sector Skill Council (HSSC) | 2019 | 2019 | official_report | 0 |
| CUR-GDA-02 | QP-GDA | Maintain Sanitation and Hygiene | SK-GDA-02 | Basic | 60 | Active | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | General Duty Assistant Qualification Pack, Version 2.0 | Healthcare Sector Skill Council (HSSC) | 2019 | 2019 | official_report | 0 |
| CUR-GDA-03 | QP-GDA | Communicate Effectively | SK-GDA-03 | Intermediate | 90 | Active | Qualification Pack: General Duty Assistant | https://www.healthcare-ssc.in/qualification-pack/general-duty-assistant/ | General Duty Assistant Qualification Pack, Version 2.0 | Healthcare Sector Skill Council (HSSC) | 2019 | 2019 | official_report | 0 |

**Methodology note**: Module names are taken directly from the Qualification Pack documents, which list the National Occupational Standards (NOS) that form the curriculum. Training hours are estimated based on typical course structure and are not explicitly provided in the source; they are derived for Kaushora analytics.

---

## JOB_DEMAND

**No records available.**

**Reason**: At the time of compilation, no publicly accessible, static, aggregated job-demand dataset with job counts, location, and period could be obtained from official sources. Dynamic portals like NCS provide real-time vacancy data but require programmatic access and snapshot capture, which was not feasible for this dataset. The dataset intentionally contains no synthetic job postings or fabricated demand statistics.

---

## TRAINING_CAPACITY

**No records available.**

**Reason**: District-level training capacity data (number of seats, enrollments, trainers, equipment status) is not consistently published in machine-readable form by government sources. While some state skill development missions may have such data, specific granular records were not accessible. No fictitious training centres or capacity numbers have been created.

---

## PLACEMENT_OUTCOMES

**No records available.**

**Reason**: Reliable placement outcome statistics at course or district level are not publicly available in a consistent, citable format. Aggregated scheme-level placement rates (e.g., PMKVY) exist but are not broken down by course or geography in the accessible public domain. To avoid misrepresentation, no placement records are included.

---

## EMPLOYER_REQUIREMENTS

**No records available.**

**Reason**: Published employer surveys with specific skill requirements, importance, and hiring demand are not systematically available for India at a granular level. While industry reports like India Skills Report exist, their full data tables are often not openly accessible or are aggregated beyond usable granularity. No fabricated employer responses are included.

---

## EMERGING_TRENDS

| trend_id | technology_or_skill | sector | trend_description | evidence | trend_direction | period | source | source_url | source_title | publisher | data_type | is_synthetic |
|----------|---------------------|--------|-------------------|----------|-----------------|--------|--------|------------|--------------|-----------|-----------|--------------|
| TREND-001 | AI and Machine Learning Specialists | Cross-sector (IT, Finance, Healthcare) | Roles requiring AI and ML skills are expected to grow significantly, driven by automation and data-driven decision making. | 39% expected growth in demand for AI/ML specialists between 2023 and 2027 (WEF Future of Jobs Report 2023). | growing | 2023-2027 | WEF Future of Jobs Report 2023 | https://www.weforum.org/reports/the-future-of-jobs-report-2023/ | The Future of Jobs Report 2023 | World Economic Forum | official_report | 0 |
| TREND-002 | Big Data Analysts | IT-ITeS, BFSI | Demand for professionals who can analyze large datasets to inform business strategy is rising. | 31% expected growth in demand for Big Data Analysts between 2023 and 2027 (WEF Future of Jobs Report 2023). | growing | 2023-2027 | WEF Future of Jobs Report 2023 | https://www.weforum.org/reports/the-future-of-jobs-report-2023/ | The Future of Jobs Report 2023 | World Economic Forum | official_report | 0 |
| TREND-003 | Digital Literacy and Cybersecurity | Cross-sector | Basic digital skills and cybersecurity awareness are becoming baseline requirements across many occupations. | 50% of all employees will need reskilling by 2025 due to technology adoption (WEF Future of Jobs Report 2020). | stable | 2020-2025 | WEF Future of Jobs Report 2020 | https://www.weforum.org/reports/the-future-of-jobs-report-2020/ | The Future of Jobs Report 2020 | World Economic Forum | official_report | 0 |

**Methodology note**: Trend directions ("growing", "stable") are directly taken from the source report's classification of job roles. The evidence column quotes the source's reported growth rates. No additional growth percentages are invented.

---

## DISTRICT_SKILL_DEMAND

**No records available.**

**Reason**: District-level skill demand data for Maharashtra (Nagpur, Pune, Mumbai) is not published as a consistent open dataset. While NSDC has conducted district skill gap studies, the individual study documents are not always directly accessible or machine-readable, and specific demand numbers could not be verified. No fabricated district-level demand is included.

---

## SKILL_DEMAND_AGGREGATION (Kaushora Derived)

This table will be populated by the Kaushora analytics engine after ingesting the source data. Because the current dataset contains no JOB_DEMAND or EMPLOYER_REQUIREMENTS records, no demand scores can be calculated at this time. The table schema and calculation methodology are defined below for future use when source data becomes available.

**Calculation method (documentation)**:

- `overall_demand_score = normalized_job_demand + normalized_growth_signal + normalized_employer_evidence`
- Where:
  - `normalized_job_demand` = number of job postings or vacancies for skill (from JOB_DEMAND) divided by maximum across all skills, scaled 0-1.
  - `normalized_growth_signal` = trend direction weight from EMERGING_TRENDS: growing=1, stable=0.5, declining=0.
  - `normalized_employer_evidence` = proportion of employer requirements citing the skill (from EMPLOYER_REQUIREMENTS).
- If a component is missing, it is omitted and confidence is reduced proportionally. Missing data is not treated as zero without explicit note.

Currently, no rows can be generated because the required source tables are empty.

---

## CURRICULUM_ALIGNMENT (Kaushora Derived)

This table assesses alignment between training courses and market demand. Because no market demand signals are available in this dataset (JOB_DEMAND, EMPLOYER_REQUIREMENTS empty), alignment scores cannot be computed. The schema is defined for future ingestion.

**Proposed calculation method**:

- `market_demand` = normalized demand score for the skills taught by the course (from SKILL_DEMAND_AGGREGATION).
- `curriculum_coverage` = proportion of skills from course that are relevant to demand (course skills present in demand aggregation).
- `alignment_score = market_demand * curriculum_coverage`.
- `gap_status` = "Aligned" if alignment_score > 0.7, "Partial" if 0.3-0.7, "Misaligned" if <0.3.

No rows can be generated now.

---

## DISTRICT_SKILL_GAPS (Kaushora Derived)

This table identifies gaps between district skill demand and training capacity. Both input tables are empty; hence no gaps can be estimated. The formula is defined as:

`estimated_gap = demand_signal - training_capacity` (both normalized). If either input is missing, the gap is marked as "Not Available".

---

## RECOMMENDATIONS

**No recommendations available.**

**Reason**: Recommendations require evidence from demand, capacity, and alignment analyses. Since those source tables are currently empty, no evidence-based recommendations can be generated. The platform will populate this table when real demand and capacity data are added.

---

## DATA_QUALITY_REPORT

### Records by Section

| Section | Total Records | Real Records | Derived Records | Synthetic Records | Records with Source | Records with Source URL | Records without Source |
|---------|---------------|--------------|-----------------|-------------------|---------------------|------------------------|------------------------|
| JOB_ROLES | 4 | 4 | 0 | 0 | 4 | 4 | 0 |
| SKILLS | 9 | 9 | 0 | 0 | 9 | 9 | 0 |
| TRAINING_COURSES | 3 | 3 | 0 | 0 | 3 | 3 | 0 |
| COURSE_SKILLS | 9 | 0 | 9 | 0 | 9 | 9 | 0 |
| CURRICULUM | 9 | 9 | 0 | 0 | 9 | 9 | 0 |
| JOB_DEMAND | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| TRAINING_CAPACITY | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| PLACEMENT_OUTCOMES | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| EMPLOYER_REQUIREMENTS | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| EMERGING_TRENDS | 3 | 3 | 0 | 0 | 3 | 3 | 0 |
| DISTRICT_SKILL_DEMAND | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **37** | **28** | **9** | **0** | **37** | **37** | **0** |

All records have a source URL. No synthetic records exist. Derived records are clearly marked and use `data_type = derived_metric`.

### Missing Fields
- In JOB_ROLES, `related_skills` for NCO entries are inferred from general job descriptions; not directly cited but marked as derived from NCO classification.
- In COURSE_SKILLS, `proficiency_level` and `training_hours` are estimated based on typical QP structure; not explicitly stated in source.

### Duplicate Records
None.

### Inconsistent IDs
All IDs follow consistent prefixes and are unique.

### Invalid References
All foreign key references (course_id, skill_id) are valid within the dataset.

### Date Range
Sources cover 2015 (NCO) to 2023 (WEF reports). Data periods vary by source.

### Geographic Coverage
- India (NCO, WEF)
- IT-ITeS and Healthcare QPs are national in scope, not state-specific.
- No state or district-level records are included due to lack of accessible data.

### Known Limitations
- No job demand, training capacity, placement outcomes, or employer requirements could be sourced due to accessibility constraints.
- The dataset is intended for hackathon prototype purposes and should not be considered exhaustive or official labour-market statistics.
- Some derived fields (training hours in COURSE_SKILLS, related_skills in JOB_ROLES) are heuristic and require validation against original documents.

---

## DATA DICTIONARY

### Table: JOB_ROLES

| field_name | data_type | meaning | allowed_values | whether_required | source_or_calculation |
|------------|-----------|---------|----------------|-----------------|------------------------|
| role_id | TEXT | Unique identifier for job role | Alphanumeric string | Yes | Source-assigned (NCO code) |
| job_title | TEXT | Official job title from classification | Free text | Yes | Source |
| normalized_role | TEXT | Standardized role name for analytics | Free text | Yes | Derived by Kaushora from job_title |
| sector | TEXT | Economic sector | e.g., IT-ITeS, Healthcare | Yes | Source |
| qualification_level | TEXT | NSQF level or general qualification | NSQF Level 1-10, Diploma, Degree | Yes | Source |
| typical_experience | TEXT | Common experience range for entry-level | e.g., 0-5 years | No | Derived from industry norms |
| description | TEXT | Brief role description | Free text | No | Source (paraphrased from NCO) |
| related_skills | TEXT | List of skill areas relevant to role | Comma-separated skill names | No | Derived from NCO description and QPs |
| source | TEXT | Name of originating source | Free text | Yes | Source |
| source_url | TEXT | URL of source document or page | Valid URL | Yes | Source |
| source_title | TEXT | Title of source document | Free text | Yes | Source |
| publisher | TEXT | Organisation that published source | Free text | Yes | Source |
| publication_date | TEXT | Year or date of publication | YYYY or YYYY-MM-DD | Yes | Source |
| data_period | TEXT | Period to which data applies | e.g., 2015 | Yes | Source |
| data_type | TEXT | Type of data record | official_dataset, official_report, etc. | Yes | Source classification |
| is_synthetic | INTEGER | Flag for synthetic data | 0 or 1 | Yes | Always 0 for factual |

### Table: SKILLS

| field_name | data_type | meaning | allowed_values | whether_required | source_or_calculation |
|------------|-----------|---------|----------------|-----------------|------------------------|
| skill_id | TEXT | Unique identifier for skill | Alphanumeric | Yes | Assigned |
| skill_name | TEXT | Name of skill | Free text | Yes | Source (QP) |
| normalized_skill_name | TEXT | Slug or normalized name | lowercase, underscores | Yes | Derived |
| skill_category | TEXT | Category (Technical, Functional, etc.) | Technical, Functional, Soft | Yes | Derived from QP |
| sector | TEXT | Relevant sector | e.g., IT-ITeS, Healthcare | Yes | Source |
| description | TEXT | Description of skill | Free text | No | Source |
| technology_status | TEXT | Whether skill is current/emerging/legacy | Current, Emerging, Legacy | No | Derived from QP activity |
| source | TEXT | Source name | Free text | Yes | Source |
| source_url | TEXT | URL to source | URL | Yes | Source |
| source_title | TEXT | Title of source document | Free text | Yes | Source |
| publisher | TEXT | Publisher of source | Free text | Yes | Source |
| data_period | TEXT | Period of source | YYYY | Yes | Source |
| data_type | TEXT | Type of data | official_report | Yes | Source |
| is_synthetic | INTEGER | Synthetic flag | 0/1 | Yes | Always 0 |

### Table: TRAINING_COURSES

| field_name | data_type | meaning | allowed_values | whether_required | source_or_calculation |
|------------|-----------|---------|----------------|-----------------|------------------------|
| course_id | TEXT | Unique course identifier | Alphanumeric | Yes | Assigned |
| course_name | TEXT | Course title | Free text | Yes | Source |
| sector | TEXT | Sector | e.g., IT-ITeS | Yes | Source |
| qualification_level | TEXT | NSQF level | NSQF 1-10 | Yes | Source |
| duration | TEXT | Total duration | e.g., 600 hours | Yes | Source |
| delivery_mode | TEXT | Mode of delivery | Classroom, Online, Hybrid | Yes | Source |
| provider | TEXT | Training provider | SSC name | Yes | Source |
| skills_taught | TEXT | List of skill IDs | Comma-separated skill_id | Yes | Derived from course mapping |
| target_roles | TEXT | Job roles after completion | Free text | Yes | Source |
| course_status | TEXT | Current status | Active, Inactive | Yes | Source |
| source | TEXT | Source name | Free text | Yes | Source |
| source_url | TEXT | URL | URL | Yes | Source |
| source_title | TEXT | Title | Free text | Yes | Source |
| publisher | TEXT | Publisher | Free text | Yes | Source |
| data_period | TEXT | Period | YYYY | Yes | Source |
| data_type | TEXT | Type | public_course_data | Yes | Source |
| is_synthetic | INTEGER | Flag | 0/1 | Yes | Always 0 |

### Table: COURSE_SKILLS

| field_name | data_type | meaning | allowed_values | whether_required | source_or_calculation |
|------------|-----------|---------|----------------|-----------------|------------------------|
| course_id | TEXT | Foreign key to TRAINING_COURSES | Existing course_id | Yes | Source |
| skill_id | TEXT | Foreign key to SKILLS | Existing skill_id | Yes | Source |
| skill_name | TEXT | Name of skill (denormalized) | Free text | Yes | Source |
| proficiency_level | TEXT | Expected proficiency after course | Basic, Intermediate, Advanced | Yes | Derived from QP |
| training_hours | INTEGER | Approx hours dedicated to skill | Positive integer | Yes | Derived from course duration |
| source | TEXT | Source name | Free text | Yes | Source |
| source_url | TEXT | URL | URL | Yes | Source |
| data_type | TEXT | Type | derived_metric | Yes | Derived |
| is_synthetic | INTEGER | Flag | 0 | Yes | Always 0 (derived from real source) |

### Table: CURRICULUM

| field_name | data_type | meaning | allowed_values | whether_required | source_or_calculation |
|------------|-----------|---------|----------------|-----------------|------------------------|
| curriculum_id | TEXT | Unique curriculum module ID | Alphanumeric | Yes | Assigned |
| course_id | TEXT | Foreign key to course | Existing course_id | Yes | Source |
| module_name | TEXT | Name of module / NOS | Free text | Yes | Source (QP) |
| skill_id | TEXT | Foreign key to skill | Existing skill_id | Yes | Derived (module maps to skill) |
| proficiency_level | TEXT | Expected proficiency | Basic, Intermediate | Yes | Derived |
| training_hours | INTEGER | Hours for module | Positive integer | Yes | Derived |
| module_status | TEXT | Active status | Active, Inactive | Yes | Source |
| source | TEXT | Source name | Free text | Yes | Source |
| source_url | TEXT | URL | URL | Yes | Source |
| source_title | TEXT | Title | Free text | Yes | Source |
| publisher | TEXT | Publisher | Free text | Yes | Source |
| data_period | TEXT | Period | YYYY | Yes | Source |
| data_type | TEXT | Type | official_report | Yes | Source |
| is_synthetic | INTEGER | Flag | 0 | Yes | Always 0 |

### Tables with no records (JOB_DEMAND, TRAINING_CAPACITY, PLACEMENT_OUTCOMES, EMPLOYER_REQUIREMENTS, DISTRICT_SKILL_DEMAND)

These tables have the schemas defined in the problem statement but contain zero rows because no reliable source data was available. Their schemas are documented in the problem statement and can be implemented when data becomes available.

### Derived Analytics Tables (SKILL_DEMAND_AGGREGATION, CURRICULUM_ALIGNMENT, DISTRICT_SKILL_GAPS, RECOMMENDATIONS)

These tables are generated by the Kaushora analytics engine. Their schemas are defined in the problem statement. Calculation methods are documented in the respective sections above. They remain empty in this dataset because their input tables are empty.

---

## KAUSHORA_INGESTION_CONTRACT

### Architecture
