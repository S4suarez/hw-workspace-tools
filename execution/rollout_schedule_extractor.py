"""
Retail Construction Timetable Date Extractor
---------------------------------------------
Extracts milestone dates from rollout schedule PDFs, calculates day offsets
from an anchor date, and outputs a structured CSV for a master rollout tracker.

Usage:
    python execution/rollout_schedule_extractor.py --pdf "<path>" [options]

Options:
    --pdf <path>          Path to the timetable PDF (required)
    --project <name>      Project name override
    --store <number>      Store number override
    --location <city>     Location override
    --out <path>          Output CSV path (default: Desktop/<store>_<location>_Rollout-Schedule.csv)
    --append <path>       Append rows to an existing master CSV
    --anchor <label>      Override anchor milestone label
    --dry-run             Print results without writing any files
    --debug               Print per-page extraction details
"""

import argparse
import csv
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Known milestone whitelist  (keyword_lower, clean_label, category)
# Longer/more-specific entries first so longest match wins.
# Only milestone dates are extracted — vendor names never appear here.
# ---------------------------------------------------------------------------
KNOWN_MILESTONES = [
    # Construction timeline
    ("construction scheduled start",           "Construction Scheduled Start",           "Construction"),
    ("developer construction start date",      "Developer Construction Start Date",      "Construction"),
    ("developer construction start",           "Developer Construction Start Date",      "Construction"),
    ("developer construction end date",        "Developer Construction End Date",        "Construction"),
    ("developer closing date",                 "Developer Closing Date",                 "Construction"),
    ("construction complete",                  "Construction Complete",                  "Construction"),
    ("store order date",                       "Store Order Date",                       "Construction"),
    ("ll work complete",                       "LL Work Complete",                       "Construction"),
    # IT
    ("it installation start date",             "IT Installation Start Date",             "IT"),
    ("it install",                             "IT Installation Start Date",             "IT"),
    # Punchlist
    ("punchlist complete",                     "Punchlist Complete",                     "Punchlist"),
    ("punch list complete",                    "Punchlist Complete",                     "Punchlist"),
    ("punchlist date",                         "Punchlist Date",                         "Punchlist"),
    # Turnover / Opening / Arrival
    ("est open date",                          "Estimated Open Date",                    "Opening"),
    ("estimated open date",                    "Estimated Open Date",                    "Opening"),
    ("est turnover",                           "Est Turnover",                           "Turnover"),
    ("sdc arrival",                            "SDC Arrival",                            "Arrival"),
    ("mdse from store closing arrival",        "MDSE From Store Closing Arrival",        "Delivery"),
    ("liquidator arrival date",                "Liquidator Arrival Date",                "Arrival"),
    ("keys turnover to landlord",              "Keys Turnover To Landlord",              "Turnover"),
    # Stock / Merchandise
    ("stock delivery",                         "Stock Delivery",                         "Delivery"),
    # Vendor deliveries
    ("lights/occupancy sensors delivery",      "Lights/Occupancy Sensors Delivery",      "Delivery"),
    ("lights/occupancy sensors",               "Lights/Occupancy Sensors Delivery",      "Delivery"),
    ("electric panel delivery",                "Electric Panel Delivery",                "Electrical"),
    ("ems equipment delivery",                 "EMS Equipment Delivery",                 "Delivery"),
    ("hvac equip delivery",                    "HVAC Equipment Delivery",                "HVAC"),
    ("hvac equipment delivery",                "HVAC Equipment Delivery",                "HVAC"),
    ("hardware delivery",                      "Hardware Delivery",                      "Delivery"),
    ("graphic package delivery",               "Graphic Package Delivery",               "Delivery"),
    ("lock delivery",                          "Lock Delivery",                          "Delivery"),
    ("safe delivery",                          "Safe Delivery",                          "Delivery"),
    ("slatwall/gondola delivery",              "Slatwall/Gondola Delivery",              "Delivery"),
    ("candy merchandiser/helium tank delivery","Candy Merchandiser/Helium Tank Delivery","Delivery"),
    ("candy merchandiser/helium tank",         "Candy Merchandiser/Helium Tank Delivery","Delivery"),
    ("checkout delivery",                      "Checkout Delivery",                      "Delivery"),
    ("snack zone graphics delivery",           "Snack Zone Graphics Delivery",           "Delivery"),
    ("snack zone cooler delivery",             "Snack Zone Cooler Delivery",             "Refrigeration"),
    ("snack zone power pole delivery",         "Snack Zone Power Pole Delivery",         "Delivery"),
    ("snack zone ice cream cooler install",    "Snack Zone Ice Cream Cooler Install",    "Install"),
    ("concrete floor date",                    "Concrete Floor Date",                    "Install"),
    ("plumbing fixture delivery",              "Plumbing Fixture Delivery",              "Plumbing"),
    ("consolidated fixture delivery",          "Consolidated Fixture Delivery",          "Delivery"),
    ("modular office delivery",                "Modular Office Delivery",                "Delivery"),
    ("d/c fixture delivery",                   "D/C Fixture Delivery",                   "Delivery"),
    ("sign installed date",                    "Sign Installed Date",                    "Signage"),
    ("awning or canopy delivery",              "Awning Or Canopy Delivery",              "Delivery"),
    ("freezer/cooler delivery",                "Freezer/Cooler Delivery",                "Refrigeration"),
    ("ice box delivery",                       "Ice Box Delivery",                       "Refrigeration"),
    ("store supply order w/cart delivery",     "Store Supply Order W/Cart Delivery",     "Delivery"),
    ("oeb basket delivery",                    "OEB Basket Delivery",                    "Delivery"),
    ("fire/sprinkler alarm install",           "Fire/Sprinkler Alarm Install",           "Security"),
    ("baler delivery",                         "Baler Delivery",                         "Delivery"),
    ("property landscaping date",              "Property Landscaping Date",              "Sitework"),
    ("floor care date",                        "Floor Care Date",                        "Install"),
    ("security grill delivery",                "Security Grill Delivery",                "Security"),
    ("window graphics",                        "Window Graphics",                        "Signage"),
    ("automatic doors delivery",               "Automatic Doors Delivery",               "Delivery"),
    ("conveyor delivery",                      "Conveyor Delivery",                      "Delivery"),
    ("aluminum ramp delivery",                 "Aluminum Ramp Delivery",                 "Delivery"),
    ("warehouse racking delivery",             "Warehouse Racking Delivery",             "Delivery"),
    ("cart retention delivery",                "Cart Retention Delivery",                "Delivery"),
    ("burglar alarm install",                  "Burglar Alarm Install",                  "Security"),
    ("skylight delivery",                      "Skylight Delivery",                      "Delivery"),
    ("customer queue delivery",                "Customer Queue Delivery",                "Delivery"),
    ("lift table delivery",                    "Lift Table Delivery",                    "Delivery"),
    ("air curtain delivery",                   "Air Curtain Delivery",                   "Delivery"),
    ("pestcontrol",                            "Pest Control Date",                      "Other"),
    ("pest control",                           "Pest Control Date",                      "Other"),
    # Relocation/closing
    ("last freight delivery",                  "Last Freight Delivery",                  "Delivery"),
    ("20 yard dumpster to arrive",             "20 Yard Dumpster To Arrive",             "Delivery"),
    ("last poll day",                          "Last Poll Day",                          "Other"),
    ("sign removal date",                      "Sign Removal Date",                      "Signage"),
    ("utility cut off",                        "Utility Cut Off",                        "Utility"),
    ("last business date",                     "Last Business Date",                     "Other"),
    ("expense pack up material",               "Expense Pack Up Material",               "Other"),
]

# Anchor preference order (lowercase keywords, longest match wins)
ANCHOR_PREFERENCE = [
    "construction scheduled start",
    "developer construction start",
    "est turnover",
    "turnover",
]

# Date regex patterns (tried in order)
DATE_PATTERNS = [
    r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',   # MM/DD/YYYY or M/D/YYYY
    r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})\b',    # MM/DD/YY
]


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date_from_match(m):
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def extract_dates_from_line(line):
    """Return list of (date_obj, raw_str) found in line."""
    results = []
    for pattern in DATE_PATTERNS:
        for m in re.finditer(pattern, line):
            d = parse_date_from_match(m)
            if d:
                results.append((d, m.group(0)))
    return results


# ---------------------------------------------------------------------------
# Known milestone matching
# ---------------------------------------------------------------------------

def match_known_milestone(label):
    """
    Match label text against known milestones.
    Returns (clean_label, category) or (None, None).
    Normalizes internal whitespace before matching so extra spaces don't break lookups.
    Longest keyword match wins.
    """
    # Collapse any run of whitespace to a single space before matching
    lower = re.sub(r'\s+', ' ', label).lower().strip()
    best = None
    best_len = 0
    for keyword, clean_label, category in KNOWN_MILESTONES:
        if keyword in lower and len(keyword) > best_len:
            best = (clean_label, category)
            best_len = len(keyword)
    return best if best else (None, None)


# ---------------------------------------------------------------------------
# Column detection (for layout=True text)
# ---------------------------------------------------------------------------

def detect_column_split(lines):
    """
    Find the character index of the two-column split in layout=True text.
    Ignores leading-margin gaps so they don't compete with the real column gap.
    Returns int or None if single-column.
    """
    # Find the consistent left margin (so we can exclude it from gap detection)
    left_margins = []
    for line in lines:
        if line.strip():
            left_margins.append(len(line) - len(line.lstrip()))
    if not left_margins:
        return None
    left_margins.sort()
    margin = left_margins[len(left_margins) // 2]  # median margin

    gap_positions = []
    for line in lines:
        stripped = line.rstrip()
        content = stripped.lstrip()
        if len(content) < 30:
            continue
        for m in re.finditer(r'\s{4,}', stripped):
            # Use the END of the gap (= start of right column) — this is
            # consistent across rows regardless of left-column content length.
            col_start = m.end()
            # Skip leading-margin gaps and gaps that end near the right edge
            if col_start <= margin + 8:
                continue
            if col_start > len(stripped) - 5:
                continue
            gap_positions.append(col_start)

    if len(gap_positions) < 3:
        return None

    # Bucket by 8-char windows, find the most frequent bucket
    buckets = Counter(round(p / 8) * 8 for p in gap_positions)
    best_bucket, best_count = buckets.most_common(1)[0]
    if best_count < 2:
        return None

    near = [p for p in gap_positions if abs(p - best_bucket) <= 8]
    return int(sum(near) / len(near))


# ---------------------------------------------------------------------------
# Core page extraction
# ---------------------------------------------------------------------------

def extract_milestones_from_page(page, page_num, debug=False):
    """
    Extract milestones using layout=True text + column-aware parsing.
    Only returns milestones matching the known-milestone whitelist.
    """
    text = page.extract_text(layout=True)
    if not text or not text.strip():
        return []

    lines = text.split('\n')
    col_split = detect_column_split(lines)

    if debug:
        print(f"\n--- Page {page_num} | col_split={col_split} | lines={len(lines)} ---")

    # Build column line lists: list of (line_idx_in_page, text)
    left_col = []
    right_col = []

    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        # Skip URL/footer lines
        if 'http' in line.lower() or 'accruent' in line.lower():
            continue

        if col_split and len(line) > col_split:
            left_part = line[:col_split].strip()
            right_part = line[col_split:].strip()
        else:
            left_part = line.strip()
            right_part = ""

        if left_part:
            left_col.append((idx, left_part))
        if right_part:
            right_col.append((idx, right_part))

    milestones = []

    for col_lines in [left_col, right_col]:
        for i, (line_idx, text) in enumerate(col_lines):
            dates = extract_dates_from_line(text)
            if not dates:
                continue

            # --- Find the label for this date line ---

            # 1. Inline label: text on the same line before/around the date
            inline = text
            for _, raw in dates:
                inline = inline.replace(raw, "")
            inline = re.sub(r'[\s:,\-/]+$', '', inline).strip()
            inline = re.sub(r'^[\s:,\-/]+', '', inline).strip()

            # 2. Look backward in same column for the nearest label line
            backward_label = ""
            for j in range(i - 1, max(i - 5, -1), -1):
                prev_idx, prev_text = col_lines[j]
                if 'http' in prev_text.lower():
                    continue
                if extract_dates_from_line(prev_text):
                    break  # hit another value line, stop
                if prev_text.strip():
                    backward_label = prev_text.strip()
                    break

            # Combine: prefer backward label; append inline if it adds context
            if backward_label and inline:
                combined = backward_label + " " + inline
            elif backward_label:
                combined = backward_label
            elif inline:
                combined = inline
            else:
                continue

            # 3. Match against known milestones
            clean_label, category = match_known_milestone(combined)

            # If combined didn't match, try each part separately
            if not clean_label and backward_label:
                clean_label, category = match_known_milestone(backward_label)
            if not clean_label and inline:
                clean_label, category = match_known_milestone(inline)

            if not clean_label:
                if debug:
                    print(f"  [SKIP - unknown] '{combined[:60]}'")
                continue

            for date_obj, _ in dates:
                if debug:
                    print(f"  [MILESTONE] '{clean_label}' = {date_obj} (col {'L' if col_lines is left_col else 'R'})")
                milestones.append({
                    "original_label": combined.strip(),
                    "clean_label": clean_label,
                    "category": category,
                    "date": date_obj,
                    "source_page": page_num,
                    "confidence": "High",
                    "needs_review": False,
                })

    return milestones


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata_from_text(full_text):
    meta = {"store": None, "location": None}
    for pat in [r'store\s*#\s*(\d{3,6})', r'store\s*no\.?\s*(\d{3,6})', r'#\s*(\d{4,6})\b']:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            meta["store"] = m.group(1)
            break
    # City, ST pattern
    m = re.search(r'\b([A-Za-z][A-Za-z\s]+,\s*[A-Z]{2})\b', full_text)
    if m:
        meta["location"] = m.group(1).strip()
    return meta


# ---------------------------------------------------------------------------
# Anchor selection
# ---------------------------------------------------------------------------

def find_anchor(milestones, override_label=None):
    preference = [override_label.lower()] if override_label else ANCHOR_PREFERENCE
    for pref in preference:
        for m in milestones:
            if pref in m["clean_label"].lower():
                return m, m["clean_label"]
    if milestones:
        earliest = min(milestones, key=lambda x: x["date"])
        return earliest, earliest["clean_label"]
    return None, None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_pdf(pdf_path, project=None, store=None, location=None,
                anchor_override=None, debug=False):
    print(f"Opening: {pdf_path}")
    all_milestones = []
    full_text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"  Pages: {total_pages}")

        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            # Check for text content
            plain = page.extract_text()
            if not plain or not plain.strip():
                print(f"  Page {page_num}: [image-only or empty -- skipped]")
                continue
            full_text_parts.append(plain)

            page_milestones = extract_milestones_from_page(page, page_num, debug=debug)
            all_milestones.extend(page_milestones)
            print(f"  Page {page_num}: {len(page_milestones)} milestone(s) found")

    if not all_milestones:
        print("  WARNING: No milestones extracted.")
        return [], {}

    full_text = "\n".join(full_text_parts)
    auto_meta = extract_metadata_from_text(full_text)
    store = store or auto_meta.get("store") or "UNKNOWN"
    location = location or auto_meta.get("location") or "UNKNOWN"
    project = project or f"Store {store}"

    # Deduplicate: same clean_label + same date = keep first
    seen = set()
    deduped = []
    for m in all_milestones:
        key = (m["clean_label"].lower(), m["date"])
        if key not in seen:
            seen.add(key)
            deduped.append(m)
    duplicates_removed = len(all_milestones) - len(deduped)
    all_milestones = deduped

    anchor_milestone, anchor_label = find_anchor(all_milestones, anchor_override)
    if not anchor_milestone:
        print("  ERROR: Could not determine anchor date.")
        return [], {}

    anchor_date = anchor_milestone["date"]
    print(f"  Anchor: '{anchor_label}' = {anchor_date}")

    rows = []
    for m in all_milestones:
        offset = (m["date"] - anchor_date).days
        rows.append({
            "Project Name":          project,
            "Store Number":          store,
            "Location":              location,
            "Anchor Milestone":      anchor_label,
            "Anchor Date":           anchor_date.strftime("%Y-%m-%d"),
            "Milestone Category":    m["category"],
            "Original Milestone Label": m["original_label"],
            "Clean Milestone Label": m["clean_label"],
            "Milestone Date":        m["date"].strftime("%Y-%m-%d"),
            "Offset Days":           offset,
            "Source Page":           m["source_page"],
            "Confidence":            m["confidence"],
            "Needs Review":          "TRUE" if m["needs_review"] else "FALSE",
        })

    rows.sort(key=lambda r: r["Milestone Date"])

    needs_review_count = sum(1 for r in rows if r["Needs Review"] == "TRUE")
    dates = [r["Milestone Date"] for r in rows]
    summary = {
        "anchor_used":       f"{anchor_label} ({anchor_date.strftime('%Y-%m-%d')})",
        "total":             len(rows),
        "needs_review":      needs_review_count,
        "duplicates":        duplicates_removed,
        "earliest":          rows[0]["Milestone Date"] if rows else "N/A",
        "latest":            rows[-1]["Milestone Date"] if rows else "N/A",
        "earliest_label":    rows[0]["Clean Milestone Label"] if rows else "N/A",
        "latest_label":      rows[-1]["Clean Milestone Label"] if rows else "N/A",
        "earliest_offset":   rows[0]["Offset Days"] if rows else 0,
        "latest_offset":     rows[-1]["Offset Days"] if rows else 0,
    }
    return rows, summary


def print_summary(summary):
    print("\n--- SUMMARY ---")
    print(f"Anchor Used:                {summary['anchor_used']}")
    print(f"Total Milestones Extracted: {summary['total']}")
    print(f"Milestones Needing Review:  {summary['needs_review']}")
    print(f"Duplicates Removed:         {summary['duplicates']}")
    off_e = summary['earliest_offset']
    off_l = summary['latest_offset']
    print(f"Earliest Milestone:         {summary['earliest']} ({summary['earliest_label']}, offset {off_e:+d})")
    print(f"Latest Milestone:           {summary['latest']} ({summary['latest_label']}, offset {off_l:+d})")


def write_csv(rows, out_path, append=False, summary=None):
    fieldnames = [
        "Project Name", "Store Number", "Location",
        "Anchor Milestone", "Anchor Date",
        "Milestone Category", "Original Milestone Label", "Clean Milestone Label",
        "Milestone Date", "Offset Days", "Source Page", "Confidence", "Needs Review",
    ]
    mode = 'a' if append else 'w'
    write_header = not append or not Path(out_path).exists()

    with open(out_path, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

        if summary and not append:
            f.write("\n--- SUMMARY ---\n")
            f.write(f"Anchor Used,{summary['anchor_used']}\n")
            f.write(f"Total Milestones Extracted,{summary['total']}\n")
            f.write(f"Milestones Needing Review,{summary['needs_review']}\n")
            f.write(f"Duplicates Removed,{summary['duplicates']}\n")
            off_e = summary['earliest_offset']
            off_l = summary['latest_offset']
            f.write(f"Earliest Milestone,{summary['earliest']} ({summary['earliest_label']} offset {off_e:+d})\n")
            f.write(f"Latest Milestone,{summary['latest']} ({summary['latest_label']} offset {off_l:+d})\n")

    print(f"\nOutput -> {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Retail Construction Timetable Date Extractor")
    parser.add_argument("--pdf",      required=True)
    parser.add_argument("--project",  default=None)
    parser.add_argument("--store",    default=None)
    parser.add_argument("--location", default=None)
    parser.add_argument("--out",      default=None)
    parser.add_argument("--append",   default=None)
    parser.add_argument("--anchor",   default=None)
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--debug",    action="store_true")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    rows, summary = process_pdf(
        pdf_path,
        project=args.project,
        store=args.store,
        location=args.location,
        anchor_override=args.anchor,
        debug=args.debug,
    )

    if not rows:
        print("No output generated.")
        sys.exit(1)

    print_summary(summary)

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        print("\nAll extracted milestones:")
        for r in rows:
            print(f"  {r['Milestone Date']}  ({r['Offset Days']:+4d}d)  {r['Clean Milestone Label']}")
        return

    if args.append:
        write_csv(rows, args.append, append=True)
    else:
        if args.out:
            out_path = args.out
        else:
            store_slug = (args.store or "STORE").replace(" ", "-")
            loc_slug = (args.location or "LOCATION").replace(" ", "-").replace(",", "")
            desktop = Path.home() / "Desktop"
            out_path = desktop / f"{store_slug}_{loc_slug}_Rollout-Schedule.csv"
        write_csv(rows, str(out_path), append=False, summary=summary)


if __name__ == "__main__":
    main()
