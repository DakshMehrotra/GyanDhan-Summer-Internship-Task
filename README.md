# Coventry University Course Scraper

## Overview
A Python web scraper that extracts structured course data for **5 courses** directly from
the official Coventry University website (`https://www.coventry.ac.uk/`).

> **All data is fetched exclusively from official Coventry University web pages.**  
> No third-party platforms, pre-existing datasets, or manual copy-pasting are used.

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP requests to fetch web pages |
| `beautifulsoup4` | HTML parsing and data extraction |
| `json` | Output formatting (built-in) |
| `re` | Regex-based field extraction (built-in) |
| `logging` | Structured run logs (built-in) |

---

## Setup Steps

### 1. Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### 2. Install dependencies

```bash
pip install requests beautifulsoup4
```

Or, if your system requires it:

```bash
pip install requests beautifulsoup4 --break-system-packages
```

### 3. Clone / place the files

Ensure the following files are in the same folder:
```
coventry_scraper/
├── scraper.py          ← main scraper script
├── coventry_courses.json  ← output (auto-generated)
└── README.md           ← this file

```

---

## How to Run

```bash
cd coventry_scraper
python scraper.py
```

The scraper will:
1. Log each course URL being fetched
2. Parse the HTML from each official Coventry University course page
3. Extract all required schema fields
4. Save results to `coventry_courses.json`

Expected terminal output:
```
08:00:01  INFO  Starting Coventry University scraper ...
08:00:01  INFO  Scraping: https://www.coventry.ac.uk/course-structure/pg/ees/advanced-aerospace-engineering-msc/
08:00:03  INFO    ✓ Advanced Aerospace Engineering MSc
...
08:00:12  INFO  Done! 5 course records saved to coventry_courses.json
```

---

## How Course URLs Are Discovered

The 5 course URLs are sourced from Coventry University's official A-Z postgraduate
course listing page:

**https://www.coventry.ac.uk/study-at-coventry/postgraduate-study/az-course-list/**

These are hardcoded in `COURSE_URLS` inside `scraper.py` for reliability.
The scraper uses a **duplicate-check set** to ensure no URL is processed twice.

---

## Output Format

### File: `coventry_courses.json`

A JSON array with exactly **5 objects**, one per course. Each object follows the
required schema:

```json
[
  {
    "program_course_name":               "Advanced Aerospace Engineering MSc",
    "university_name":                   "Coventry University",
    "course_website_url":                "https://www.coventry.ac.uk/...",
    "campus":                            "Coventry",
    "country":                           "United Kingdom",
    "address":                           "Priory Street, Coventry, CV1 5FB, United Kingdom",
    "study_level":                       "Postgraduate",
    "course_duration":                   "1 year full-time; up to 2 years with placement",
    "all_intakes_available":             "March 2026, May 2026, July 2026",
    "mandatory_documents_required":      "Academic transcripts, degree certificate ...",
    "yearly_tuition_fee":                "Refer to Postgraduate Finance page ...",
    "scholarship_availability":          "International Scholarships available ...",
    "gre_gmat_mandatory_min_score":      "NA",
    "indian_regional_institution_restrictions": "NA",
    "class_12_boards_accepted":          "NA",
    "gap_year_max_accepted":             "NA",
    "min_duolingo":                      "NA",
    "english_waiver_class12":            "NA",
    "english_waiver_moi":                "Waiver possible if prior degree taught in English ...",
    "min_ielts":                         "6.5 overall, with no component lower than 5.5",
    "kaplan_test_of_english":            "NA",
    "min_pte":                           "NA",
    "min_toefl":                         "NA",
    "ug_academic_min_gpa":               "Honours degree 2:2 or above ...",
    "twelfth_pass_min_cgpa":             "NA",
    "mandatory_work_exp":                "NA",
    "max_backlogs":                      "NA"
  },
  ...
]
```

### Field Explanation

| Field | Description |
|---|---|
| `program_course_name` | Official course title extracted from the `<h1>` tag |
| `university_name` | Always "Coventry University" |
| `course_website_url` | The final official Coventry University course page URL |
| `campus` | Extracted from the "Location" field on the course page |
| `country` | United Kingdom (static for all Coventry main campus courses) |
| `address` | Official university address |
| `study_level` | Inferred from URL pattern (`/pg/` = Postgraduate, `/ug/` = Undergraduate) |
| `course_duration` | From the "Duration" section on the course feature block |
| `all_intakes_available` | From the "Start date" section on the course feature block |
| `mandatory_documents_required` | Extracted from the entry/application requirements section |
| `yearly_tuition_fee` | Extracted from the fees section (exact figures are on course pages) |
| `scholarship_availability` | Extracted from the scholarship/funding section |
| `gre_gmat_mandatory_min_score` | Coventry does not require GRE/GMAT → "NA" |
| `min_ielts` | Extracted via regex search for IELTS score pattern |
| `min_pte` | Extracted via regex search for PTE score pattern |
| `min_toefl` | Extracted via regex search for TOEFL score pattern |
| `ug_academic_min_gpa` | Raw text extracted from the entry requirements section |
| `mandatory_work_exp` | Extracted from page; "NA" if not mentioned |
| All other fields | "NA" — either not applicable to PG courses or not stated on page |

### Missing Values
All unavailable or not-applicable fields are returned as `"NA"` as per the assignment spec.

---

## 5 Courses Scraped

| # | Course | URL |
|---|---|---|
| 1 | Advanced Aerospace Engineering MSc | https://www.coventry.ac.uk/course-structure/pg/ees/advanced-aerospace-engineering-msc/ |
| 2 | Advanced Software Engineering MSc | https://www.coventry.ac.uk/course-structure/pg/ees/advanced-software-engineering-msc/ |
| 3 | MBA Master of Business Administration | https://www.coventry.ac.uk/course-structure/pg/cbl/masters-in-business-administration/ |
| 4 | Applied Psychology MSc | https://www.coventry.ac.uk/course-structure/pg/hls/applied-psychology-msc/ |
| 5 | Automotive Engineering MSc | https://www.coventry.ac.uk/course-structure/pg/ees/automotive-engineering-msc/ |

---

## Scraper Design Notes

- **Modular functions**: each field (IELTS, fees, duration, etc.) has its own dedicated
  extraction function, making the code easy to extend or debug.
- **Graceful missing value handling**: every extractor returns `"NA"` if the field is absent.
- **Duplicate prevention**: a `seen_urls` set prevents the same course being processed twice.
- **Polite crawling**: a 1.5-second delay between requests avoids overloading the server.
- **Official source only**: all data originates from `coventry.ac.uk` pages exclusively.
- **No manual copy-pasting**: the scraper runs end-to-end without human intervention.
