"""
Dollar Tree Plan Sheet Classifier
Extracts and classifies MEP + Fire Alarm sheet IDs from a plan set PDF.

Usage:
    python execution/classify_plan_sheets.py --pdf <path_to_pdf>
    python execution/classify_plan_sheets.py --pdf plans.pdf --debug

Output:
    Mechanical
    M-101
    ...

    Plumbing
    P-101
    ...

    Electric
    E-101
    ...

    Fire Alarm
    FA-1
    ...
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Sheet ID patterns
# ---------------------------------------------------------------------------
SHEET_PATTERNS = {
    "Mechanical": re.compile(r"\bM[-.]?\d[\w.-]*\b", re.IGNORECASE),
    "Plumbing":   re.compile(r"\bP[-.]?\d[\w.-]*\b", re.IGNORECASE),
    "Electric":   re.compile(r"\bE[-.]?\d[\w.-]*\b", re.IGNORECASE),
    "Fire Alarm": re.compile(r"\bFA[-.]?D?[-.]?\d[\w.-]*\b", re.IGNORECASE),
}

# Ensure Fire Alarm check runs before Electric (FA starts with F, not E, so no conflict)
DISCIPLINE_ORDER = ["Mechanical", "Plumbing", "Electric", "Fire Alarm"]

# Keywords used as backup when sheet ID is ambiguous
KEYWORDS = {
    "Mechanical": ["hvac", "rtu", "diffuser", "ductwork", "duct ", "air device",
                   "mech schedule", "ventilation", "exhaust", "controls"],
    "Plumbing":   ["domestic water", "sanitary", "storm drain", "gas piping",
                   "fixtures", "water heater", "plumbing"],
    "Electric":   ["lighting", "power plan", "one-line", "panel schedule",
                   "receptacle", "grounding", "site electric"],
    "Fire Alarm": ["fire alarm", "fa riser", "device layout", "annunciator",
                   "nac", "smoke detector", "pull station"],
}

# Headings that indicate a sheet index page
INDEX_HEADINGS = re.compile(
    r"(sheet\s+index|drawing\s+index|index\s+of\s+(drawings|sheets)|list\s+of\s+(drawings|sheets))",
    re.IGNORECASE,
)

# Broad sheet ID: letter prefix + digits (used for index parsing)
ANY_SHEET_ID = re.compile(r"\b([A-Z]{1,3}[-.]?\d[\w.-]*)\b")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_pages(pdf_path: str, debug: bool = False) -> list[dict]:
    """Return list of {page_num, text} dicts."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page_num": i, "text": text})
            if debug:
                print(f"[DEBUG] Page {i}: {len(text)} chars", file=sys.stderr)
    return pages


def find_index_pages(pages: list[dict]) -> list[dict]:
    """Return pages that appear to contain a sheet index."""
    return [p for p in pages if INDEX_HEADINGS.search(p["text"])]


def classify_sheet_id(sheet_id: str, title: str = "") -> str | None:
    """
    Classify a single sheet ID string.
    Returns discipline name or None if unclassifiable.
    """
    sid = sheet_id.strip()

    # Fire Alarm first (FA prefix — check before generic letter checks)
    if re.match(r"^FA", sid, re.IGNORECASE):
        return "Fire Alarm"

    prefix = re.match(r"^([A-Z]+)", sid, re.IGNORECASE)
    if prefix:
        p = prefix.group(1).upper()
        if p == "M":
            return "Mechanical"
        if p == "P":
            return "Plumbing"
        if p == "E":
            return "Electric"

    # Keyword fallback on title
    if title:
        t = title.lower()
        for discipline, kws in KEYWORDS.items():
            if any(kw in t for kw in kws):
                return discipline

    return None


def extract_from_index(index_pages: list[dict], debug: bool = False) -> dict[str, list[str]]:
    """
    Parse sheet index pages. Extract (sheet_id, title) pairs and classify.
    Returns dict keyed by discipline.
    """
    results: dict[str, list[str]] = {d: [] for d in DISCIPLINE_ORDER}
    seen: set[str] = set()

    # Typical index line: "M-101  Mechanical Floor Plan" or "M101 - HVAC Plan"
    # We look for lines with a leading sheet-ID-like token
    line_pattern = re.compile(r"^\s*([A-Z]{1,3}[-.]?\d[\w.-]*)\s+[-–]?\s*(.*)", re.IGNORECASE | re.MULTILINE)

    for page in index_pages:
        for match in line_pattern.finditer(page["text"]):
            sheet_id = match.group(1).strip()
            title = match.group(2).strip()

            if sheet_id.upper() in seen:
                continue
            seen.add(sheet_id.upper())

            discipline = classify_sheet_id(sheet_id, title)
            if discipline:
                results[discipline].append(sheet_id)
                if debug:
                    print(f"[DEBUG] Index: {sheet_id!r} -> {discipline} (title: {title!r})", file=sys.stderr)

    return results


def extract_from_title_blocks(pages: list[dict], debug: bool = False) -> dict[str, list[str]]:
    """
    Fallback: scan all pages for sheet ID patterns.
    Returns dict keyed by discipline.
    """
    results: dict[str, list[str]] = {d: [] for d in DISCIPLINE_ORDER}
    seen: set[str] = set()

    for page in pages:
        text = page["text"]

        # Fire Alarm first (avoid E/M/P prefix conflicts)
        for match in SHEET_PATTERNS["Fire Alarm"].finditer(text):
            sid = match.group(0)
            key = sid.upper()
            if key not in seen:
                seen.add(key)
                results["Fire Alarm"].append(sid)

        for discipline in ["Mechanical", "Plumbing", "Electric"]:
            for match in SHEET_PATTERNS[discipline].finditer(text):
                sid = match.group(0)
                key = sid.upper()
                if key not in seen:
                    seen.add(key)
                    results[discipline].append(sid)
                    if debug:
                        print(f"[DEBUG] Title block p{page['page_num']}: {sid!r} -> {discipline}", file=sys.stderr)

    return results


def merge_results(*result_dicts) -> dict[str, list[str]]:
    """Merge multiple result dicts, preserving order, deduplicating."""
    merged: dict[str, list[str]] = {d: [] for d in DISCIPLINE_ORDER}
    seen: set[str] = set()

    for rd in result_dicts:
        for discipline in DISCIPLINE_ORDER:
            for sid in rd.get(discipline, []):
                key = sid.upper()
                if key not in seen:
                    seen.add(key)
                    merged[discipline].append(sid)

    return merged


def format_output(results: dict[str, list[str]]) -> str:
    lines = []
    for discipline in DISCIPLINE_ORDER:
        lines.append(discipline)
        for sid in results[discipline]:
            lines.append(sid)
        lines.append("")  # blank line between sections
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Classify MEP/FA sheets in a Dollar Tree plan PDF.")
    parser.add_argument("--pdf", required=True, help="Path to the plan set PDF")
    parser.add_argument("--debug", action="store_true", help="Print debug info to stderr")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if args.debug:
        print(f"[DEBUG] Opening {pdf_path}", file=sys.stderr)

    pages = extract_pages(str(pdf_path), debug=args.debug)
    index_pages = find_index_pages(pages)

    if index_pages:
        if args.debug:
            print(f"[DEBUG] Found sheet index on page(s): {[p['page_num'] for p in index_pages]}", file=sys.stderr)
        results = extract_from_index(index_pages, debug=args.debug)

        # If index yielded thin results, supplement with title block scan
        total = sum(len(v) for v in results.values())
        if total < 3:
            if args.debug:
                print("[DEBUG] Index sparse — supplementing with title block scan", file=sys.stderr)
            fallback = extract_from_title_blocks(pages, debug=args.debug)
            results = merge_results(results, fallback)
    else:
        if args.debug:
            print("[DEBUG] No sheet index found — falling back to title block scan", file=sys.stderr)
        results = extract_from_title_blocks(pages, debug=args.debug)

    print(format_output(results))


if __name__ == "__main__":
    main()
