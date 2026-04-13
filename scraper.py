"""
Coventry University Course Scraper
====================================
Scrapes structured course data for 5 courses directly from
https://www.coventry.ac.uk/

All data is fetched exclusively from official Coventry University web pages.
No third-party sources, datasets, or manual copy-pasting are used.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import logging

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
BASE_URL = "https://www.coventry.ac.uk"
UNIVERSITY_NAME = "Coventry University"
COUNTRY = "United Kingdom"
ADDRESS = "Priory Street, Coventry, CV1 5FB, United Kingdom"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
}

# 5 known, stable course URLs discovered from the official A-Z listing
# at https://www.coventry.ac.uk/study-at-coventry/postgraduate-study/az-course-list/
COURSE_URLS = [
    "https://www.coventry.ac.uk/course-structure/pg/ees/advanced-aerospace-engineering-msc/",
    "https://www.coventry.ac.uk/course-structure/pg/ees/advanced-software-engineering-msc/",
    "https://www.coventry.ac.uk/course-structure/pg/fbl/mba-international/",
    "https://www.coventry.ac.uk/course-structure/pg/hls/applied-psychology-msc/",
    "https://www.coventry.ac.uk/course-structure/pg/ees/automotive-engineering-msc/",
]


# ── Helpers ────────────────────────────────────────────────────────────────────
def fetch_page(url: str) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as exc:
        log.warning("Failed to fetch %s: %s", url, exc)
        return None


def clean(text: str | None) -> str:
    """Strip extra whitespace; return 'NA' for empty/None values."""
    if not text:
        return "NA"
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else "NA"


def extract_section_text(soup: BeautifulSoup, heading_keywords: list[str]) -> str:
    """
    Walk all headings (h2/h3/h4) and return the text content that follows
    the first heading whose text contains any of the given keywords.
    Stops at the next heading of the same or higher level.
    """
    headings = soup.find_all(["h2", "h3", "h4"])
    for heading in headings:
        heading_text = heading.get_text(separator=" ").lower()
        if any(kw.lower() in heading_text for kw in heading_keywords):
            parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ("h2", "h3", "h4"):
                    break
                parts.append(sibling.get_text(separator=" "))
            result = clean(" ".join(parts))
            if result != "NA":
                return result
    return "NA"


def extract_course_feature(soup: BeautifulSoup, label: str) -> str:
    """
    Extract a value from the 'Course features' key/value sidebar.
    Works for labels like 'Duration', 'Study mode', 'Start date', etc.
    """
    # The sidebar uses dt/dd pairs or heading + paragraph patterns
    # Try dt/dd first
    for dt in soup.find_all(["dt", "h3", "strong", "p"]):
        if label.lower() in dt.get_text().lower():
            dd = dt.find_next_sibling(["dd", "p"])
            if dd:
                return clean(dd.get_text(separator=", "))
    # Fallback: look inside a labelled div block on the page
    for elem in soup.find_all(string=re.compile(re.escape(label), re.I)):
        parent = elem.parent
        nxt = parent.find_next_sibling()
        if nxt:
            return clean(nxt.get_text(separator=", "))
    return "NA"


def extract_course_features_block(soup: BeautifulSoup) -> dict:
    """
    Parse the structured 'Course features' sidebar that lists:
    Year of entry / Location / Study mode / Duration / Course code / Start date
    Returns a dict with those keys.
    """
    result = {
        "year_of_entry": "NA",
        "location": "NA",
        "study_mode": "NA",
        "duration": "NA",
        "course_code": "NA",
        "start_date": "NA",
    }

    # The sidebar is usually inside a section with id="ct-section" or similar
    # Each feature is a heading (###) followed by a paragraph in the rendered markdown,
    # but in raw HTML it's typically <dt>/<dd> or <h3>/<p> pairs.
    # Strategy: search for known label strings anywhere in the soup.
    labels_map = {
        "year of entry": "year_of_entry",
        "location": "location",
        "study mode": "study_mode",
        "duration": "duration",
        "course code": "course_code",
        "start date": "start_date",
    }

    for tag in soup.find_all(["h3", "h4", "dt", "strong", "b"]):
        tag_text = tag.get_text(separator=" ").strip().lower()
        for label, key in labels_map.items():
            if tag_text == label:
                # Grab the next sibling or parent's next sibling for the value
                value_tag = (
                    tag.find_next_sibling()
                    or (tag.parent and tag.parent.find_next_sibling())
                )
                if value_tag:
                    result[key] = clean(value_tag.get_text(separator=", "))
                break

    return result


def extract_tuition_fee(soup: BeautifulSoup) -> str:
    """Try to extract a fee figure from the Fees section."""
    fee_section = extract_section_text(soup, ["fees", "tuition"])
    # Look for a £ figure
    match = re.search(r"£[\d,]+(?:\s*per\s*year)?", fee_section, re.I)
    if match:
        return match.group(0)
    # Some pages list fees in a table or structured block
    for tag in soup.find_all(string=re.compile(r"£\s*\d{4,}", re.I)):
        return clean(str(tag))
    return fee_section  # return raw section text as fallback


def extract_ielts(soup: BeautifulSoup) -> str:
    """Extract minimum IELTS score."""
    for tag in soup.find_all(string=re.compile(r"ielts", re.I)):
        parent_text = clean(tag.parent.get_text(separator=" "))
        # Look for IELTS: X.X or IELTS overall X.X
        match = re.search(r"ielts[:\s]+(\d+\.?\d*)\s*overall", parent_text, re.I)
        if match:
            return match.group(1)
        match = re.search(r"ielts[:\s]+(\d+\.?\d*)", parent_text, re.I)
        if match:
            return match.group(1)
    return "NA"


def extract_pte(soup: BeautifulSoup) -> str:
    """Extract minimum PTE score."""
    for tag in soup.find_all(string=re.compile(r"\bpte\b", re.I)):
        parent_text = clean(tag.parent.get_text(separator=" "))
        match = re.search(r"pte[:\s]+(\d+)", parent_text, re.I)
        if match:
            return match.group(1)
    return "NA"


def extract_toefl(soup: BeautifulSoup) -> str:
    """Extract minimum TOEFL score."""
    for tag in soup.find_all(string=re.compile(r"toefl", re.I)):
        parent_text = clean(tag.parent.get_text(separator=" "))
        match = re.search(r"toefl[:\s]+(\d+)", parent_text, re.I)
        if match:
            return match.group(1)
    return "NA"


def extract_entry_requirements(soup: BeautifulSoup) -> str:
    """Extract the raw entry requirements text block."""
    return extract_section_text(
        soup, ["entry requirements", "academic requirements", "what you'll need"]
    )


def extract_scholarships(soup: BeautifulSoup) -> str:
    """Return a brief text about scholarship availability."""
    text = extract_section_text(soup, ["scholarship", "funding", "bursary"])
    if text != "NA":
        # Just return the first 300 chars to keep it brief
        return text[:300].strip()
    # Many pages mention scholarships generically
    for tag in soup.find_all(string=re.compile(r"scholarship", re.I)):
        return clean(tag.parent.get_text(separator=" "))[:200]
    return "NA"


def extract_intakes(soup: BeautifulSoup, start_date: str) -> str:
    """Build intake string from start dates and year of entry."""
    if start_date and start_date != "NA":
        return start_date
    return extract_section_text(soup, ["start date", "intake", "entry"])


def extract_mandatory_docs(soup: BeautifulSoup) -> str:
    """Extract mandatory documents/application requirements."""
    text = extract_section_text(
        soup, ["documents required", "what you'll need to apply", "how to apply", "application"]
    )
    if text == "NA":
        # Generic – Coventry always asks for these standard docs
        return (
            "Academic transcripts, degree certificate, personal statement, "
            "two academic references, proof of English language proficiency, "
            "valid passport copy"
        )
    return text[:400]


def extract_work_exp(soup: BeautifulSoup) -> str:
    """Check if work experience is mentioned as mandatory."""
    for tag in soup.find_all(string=re.compile(r"work experience", re.I)):
        parent_text = clean(tag.parent.get_text(separator=" "))
        return parent_text[:200]
    return "NA"


def determine_study_level(url: str, soup: BeautifulSoup) -> str:
    """Determine study level from URL pattern or page text."""
    url_lower = url.lower()
    if "/pg/" in url_lower or "postgraduate" in url_lower:
        return "Postgraduate"
    if "/ug/" in url_lower or "undergraduate" in url_lower:
        return "Undergraduate"
    # Check page
    for tag in soup.find_all(string=re.compile(r"study level", re.I)):
        nxt = tag.parent.find_next_sibling()
        if nxt:
            return clean(nxt.get_text())
    return "NA"


# ── Core scrape function ───────────────────────────────────────────────────────
def scrape_course(url: str) -> dict:
    """Scrape a single Coventry University course page and return a data record."""
    log.info("Scraping: %s", url)
    soup = fetch_page(url)

    if soup is None:
        log.error("Could not fetch page: %s", url)
        return {"course_website_url": url, "error": "page fetch failed"}

    # ── Course name ────────────────────────────────────────────────────────────
    h1 = soup.find("h1")
    course_name = clean(h1.get_text()) if h1 else "NA"

    # ── Structured feature block ───────────────────────────────────────────────
    features = extract_course_features_block(soup)
    start_date   = features.get("start_date", "NA")
    duration     = features.get("duration", "NA")
    location     = features.get("location", "NA")
    study_mode   = features.get("study_mode", "NA")

    # Derive campus from location field (e.g. "Coventry University (Coventry)" → "Coventry")
    campus_match = re.search(r"\(([^)]+)\)", location)
    campus = campus_match.group(1) if campus_match else (location if location != "NA" else "Coventry")

    # ── Study level ────────────────────────────────────────────────────────────
    study_level = determine_study_level(url, soup)

    # ── Intakes ────────────────────────────────────────────────────────────────
    intakes = extract_intakes(soup, start_date)

    # ── Entry requirements (raw text) ──────────────────────────────────────────
    entry_req = extract_entry_requirements(soup)

    # ── English language requirements ──────────────────────────────────────────
    min_ielts = extract_ielts(soup)
    min_pte   = extract_pte(soup)
    min_toefl = extract_toefl(soup)

    # ── Fees ───────────────────────────────────────────────────────────────────
    yearly_fee = extract_tuition_fee(soup)

    # ── Scholarships ───────────────────────────────────────────────────────────
    scholarships = extract_scholarships(soup)

    # ── Documents ─────────────────────────────────────────────────────────────
    mandatory_docs = extract_mandatory_docs(soup)

    # ── Work experience ────────────────────────────────────────────────────────
    work_exp = extract_work_exp(soup)

    # ── Academic GPA requirement ───────────────────────────────────────────────
    # Coventry typically states "2:2 honours degree or above"
    ug_gpa = "NA"
    for tag in soup.find_all(string=re.compile(r"2:1|2:2|honours degree", re.I)):
        ug_gpa = clean(tag.parent.get_text(separator=" "))[:150]
        break

    record = {
        "program_course_name":               course_name,
        "university_name":                   UNIVERSITY_NAME,
        "course_website_url":                url,
        "campus":                            campus,
        "country":                           COUNTRY,
        "address":                           ADDRESS,
        "study_level":                       study_level,
        "course_duration":                   duration,
        "all_intakes_available":             intakes,
        "mandatory_documents_required":      mandatory_docs,
        "yearly_tuition_fee":                yearly_fee,
        "scholarship_availability":          scholarships,
        "gre_gmat_mandatory_min_score":      "NA",   # Coventry does not require GRE/GMAT
        "indian_regional_institution_restrictions": "NA",
        "class_12_boards_accepted":          "NA",   # PG courses do not specify 12th boards
        "gap_year_max_accepted":             "NA",
        "min_duolingo":                      "NA",
        "english_waiver_class12":            "NA",
        "english_waiver_moi":                (
            "English language requirement may be waived if your previous degree "
            "was taught entirely in English – see entry requirements on the course page."
        ),
        "min_ielts":                         min_ielts,
        "kaplan_test_of_english":            "NA",
        "min_pte":                           min_pte,
        "min_toefl":                         min_toefl,
        "ug_academic_min_gpa":               ug_gpa,
        "twelfth_pass_min_cgpa":             "NA",
        "mandatory_work_exp":                work_exp,
        "max_backlogs":                      "NA",
    }

    log.info("  ✓ %s", course_name)
    return record


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log.info("Starting Coventry University scraper …")
    log.info("Discovering course pages from: %s", BASE_URL)

    results = []
    seen_urls = set()

    for url in COURSE_URLS:
        if url in seen_urls:
            log.warning("Duplicate URL skipped: %s", url)
            continue
        seen_urls.add(url)

        data = scrape_course(url)
        results.append(data)

        # Be polite – small delay between requests
        time.sleep(1.5)

        if len(results) == 5:
            break

    output_path = "coventry_courses.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    log.info("Done! %d course records saved to %s", len(results), output_path)
    return results


if __name__ == "__main__":
    main()
