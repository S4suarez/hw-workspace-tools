"""
MEP Auto-Extractor
Scans a full plan set PDF, identifies MEP/FA sheets by page, applies
scope-filtering rules, and outputs a clean PDF ready for subcontractor pricing.

No need to attach the PDF -- just pass the file path.

Usage:
    python execution/mep_auto_extract.py --pdf <path>
    python execution/mep_auto_extract.py --pdf <path> --job 1234 --location "Store 5678"
    python execution/mep_auto_extract.py --pdf <path> --out "C:/Users/me/Desktop/output.pdf"
    python execution/mep_auto_extract.py --pdf <path> --list-only
    python execution/mep_auto_extract.py --pdf <path> --discipline mepf   # all trades (default)
    python execution/mep_auto_extract.py --pdf <path> --discipline e      # electrical only
    python execution/mep_auto_extract.py --pdf <path> --discipline mep    # mechanical + electrical + plumbing
    python execution/mep_auto_extract.py --pdf <path> --include "33,28:E-202"  # force-include / override

Discipline shorthand (any combination of letters):
  m = Mechanical   e = Electrical   p = Plumbing   f = Fire Alarm
  mepf = all trades (default when --discipline is omitted)

Output defaults to Desktop/<JobNumber>_<Location>_MEP-Scope.pdf
If --job / --location are omitted, the source filename stem is used.

Filtering rules (from directives/extract_mepf.md):
  KEEP:    floor plans (x-1xx), schedules (x-2xx), single-lines, legends (x-0xx), FA plans
  EXCLUDE: details (x-3xx), specs (x-4xx), sequence-of-ops, EN-xxx compliance, FA spec sheets

Detection fallbacks (in order):
  1. Text extraction via pdfplumber
  2. PDF PageLabels (catches pages with image-heavy content or non-standard fonts)
  3. --include flag for truly image-based pages with no extractable metadata
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

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("ERROR: pypdf not installed. Run: pip install pypdf", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Page label parsing (fallback when text extraction misses the title block)
# ---------------------------------------------------------------------------

def build_page_label_map(pdf_path: str) -> dict[int, str]:
    """
    Parse the PDF's /PageLabels dictionary.
    Returns {0-indexed page number: label string}.
    Only includes pages with an explicit label (not generic decimal sequences).
    """
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    result = {}
    try:
        labels_obj = reader.trailer["/Root"].get("/PageLabels")
        if not labels_obj:
            return result
        nums = labels_obj.get("/Nums", [])
        # nums is [page_index, label_dict, page_index, label_dict, ...]
        for i in range(0, len(nums) - 1, 2):
            page_idx = int(nums[i])
            label_dict = nums[i + 1]
            # Only care about entries with an explicit /P prefix (fixed label, not sequential)
            prefix = label_dict.get("/P", "")
            if prefix:
                result[page_idx] = str(prefix)
    except Exception:
        pass
    return result


def sheet_id_from_label(label: str) -> str | None:
    """
    Extract a sheet ID from a PDF page label string.
    Labels often look like: '[1] 25161003_01-FAD1' or '0130A_001-E-202'
    Strategy: grab the last dash-separated token that looks like a sheet ID.
    """
    # Try last segment after the last hyphen/underscore
    tokens = re.split(r"[-_]", label)
    for token in reversed(tokens):
        token = token.strip()
        if re.match(r"^(FA|M|P|EN|E)\w*\d", token, re.IGNORECASE):
            return token
    return None


# ---------------------------------------------------------------------------
# Sheet ID detection patterns
# ---------------------------------------------------------------------------

# Ordered so Fire Alarm is checked before Electric (no prefix conflict, but good practice)
SHEET_PATTERNS = [
    ("Fire Alarm", re.compile(r"\bFA[-.]?D?[-.]?\d[\w.-]*\b", re.IGNORECASE)),
    ("Mechanical", re.compile(r"\bM[-.]?\d[\w.-]*\b",          re.IGNORECASE)),
    ("Plumbing",   re.compile(r"\bP[-.]?\d[\w.-]*\b",          re.IGNORECASE)),
    ("Electric",   re.compile(r"\b(EN|E)[-.]?\d[\w.-]*\b",     re.IGNORECASE)),
]

# Broad: any sheet-ID-looking token (used to find the "primary" ID on a page)
ANY_SHEET_ID = re.compile(r"\b([A-Z]{1,3}[-.]?\d[\w.-]*)\b", re.IGNORECASE)

# Content signals that override a Plumbing mis-classification to Electric.
# Panel schedules, power distribution notes, etc. get picked up as "P1" because
# "P" + digit matches Plumbing before we find E-2xx in the title block.
ELECTRICAL_CONTENT_SIGNALS = re.compile(
    r"(PANEL\s+NAME|PANEL\s+SCHEDULE|PANELBOARD|POWER\s+DISTRIBUTION"
    r"|ELECTRICAL\s+NOTES|LOAD\s+SCHEDULE|CIRCUIT\s+BREAKER|DISTRIBUTION\s+PANEL)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Filtering logic
# ---------------------------------------------------------------------------

def classify_sheet_id(sid: str) -> tuple[str | None, str]:
    """
    Returns (discipline, verdict) where verdict is 'keep' or 'exclude'.
    discipline is None if the sheet is not MEP/FA.
    """
    s = sid.strip().upper()

    # --- Determine discipline ---
    if re.match(r"^FA", s):
        discipline = "Fire Alarm"
    elif re.match(r"^EN", s):
        discipline = "Electric"   # EN = electrical compliance
    elif re.match(r"^M[-.]?\d", s):
        discipline = "Mechanical"
    elif re.match(r"^P[-.]?\d", s):
        discipline = "Plumbing"
    elif re.match(r"^E[-.]?\d", s):
        discipline = "Electric"
    else:
        return None, "exclude"  # not MEP/FA

    # --- Apply filtering rules ---

    # EN-xxx = electrical compliance/code sheets -> always exclude
    if re.match(r"^EN", s):
        return discipline, "exclude"

    # Extract numeric suffix
    num_match = re.search(r"\d+", s)
    if not num_match:
        return discipline, "keep"   # no number, keep by default

    num = int(num_match.group())

    # Fire Alarm: FA3 / FA-3 = spec sheet -> exclude; FA1, FA2, FAD1 = plans -> keep
    if discipline == "Fire Alarm":
        # The "3" series for FA means spec sheets
        if re.match(r"^FA[-.]?D?[-.]?3", s):
            return discipline, "exclude"
        return discipline, "keep"

    # All other disciplines: classify by numeric series
    hundreds = (num // 100) * 100

    if hundreds == 0:
        # x-001, x-002 etc. = legends, general notes, title sheets
        # Keep legends (E-001, etc.); general/cover sheets (G-001) already excluded above
        return discipline, "keep"
    elif hundreds == 100:
        # x-101, x-102 = floor plans -> KEEP
        return discipline, "keep"
    elif hundreds == 200:
        # x-201, x-202 = schedules, single-lines -> KEEP
        return discipline, "keep"
    elif hundreds == 300:
        # x-301, x-302 = details -> EXCLUDE
        return discipline, "exclude"
    elif hundreds >= 400:
        # x-401 = specs, x-402 = sequence of ops, x-403+ -> EXCLUDE
        return discipline, "exclude"
    else:
        # Unknown series -> keep (safe default)
        return discipline, "keep"


# ---------------------------------------------------------------------------
# Page scanning
# ---------------------------------------------------------------------------

def find_primary_sheet_id(text: str) -> str | None:
    """
    Find the most likely sheet ID on a page.
    Strategy: collect all sheet-ID-like tokens, prefer the one that appears
    last (title blocks are typically at the bottom of construction drawings).
    """
    matches = ANY_SHEET_ID.findall(text)
    # Filter to tokens that look like real sheet IDs (letter prefix + digits)
    candidates = [m for m in matches if re.match(r"^[A-Z]{1,3}[-.]?\d", m, re.IGNORECASE)]
    if not candidates:
        return None
    # Prefer MEP/FA prefixes; last occurrence wins (title block heuristic)
    mep_candidates = [c for c in candidates if re.match(r"^(FA|M|P|EN|E)[-.]?\d", c, re.IGNORECASE)]
    if mep_candidates:
        return mep_candidates[-1]
    return candidates[-1]


def scan_pdf(pdf_path: str, debug: bool = False) -> list[dict]:
    """
    Scan every page of the PDF.
    Returns list of {page_num, sheet_id, discipline, verdict, text_snippet, source}.

    Detection order:
      1. pdfplumber text extraction
      2. PDF PageLabels fallback (catches pages where title-block fonts don't extract)
    """
    label_map = build_page_label_map(pdf_path)

    results = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"Scanning {total} pages...", file=sys.stderr)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            sid = find_primary_sheet_id(text)
            source = "text"
            discipline, verdict = (None, "exclude") if sid is None else classify_sheet_id(sid)

            # Content-based reclassification: a page tagged as Plumbing but containing
            # electrical panel keywords is almost certainly a panel schedule (E-2xx).
            # This catches pages where the title block prints something like "P1" or "Panel 1"
            # but the actual content is an electrical panel schedule.
            if discipline == "Plumbing" and ELECTRICAL_CONTENT_SIGNALS.search(text):
                sid = sid  # keep whatever ID was found; caller can override via --include
                discipline = "Electric"
                verdict = "keep"
                source = source + "+content-override"

            # Fallback: try PDF page label when text extraction finds no recognized MEP/FA sheet ID
            # (covers: no text at all, or text picks up wrong token like equipment model numbers)
            if discipline is None and (i - 1) in label_map:
                label_sid = sheet_id_from_label(label_map[i - 1])
                if label_sid:
                    label_disc, label_verdict = classify_sheet_id(label_sid)
                    if label_disc is not None:
                        sid = label_sid
                        discipline = label_disc
                        verdict = label_verdict
                        source = "label"

            if sid is None:
                if debug:
                    print(f"[DEBUG] p{i:3d}: no sheet ID found", file=sys.stderr)
                results.append({
                    "page_num": i,
                    "sheet_id": None,
                    "discipline": None,
                    "verdict": "exclude",
                    "snippet": text[:80].replace("\n", " "),
                    "source": "none",
                })
                continue

            if debug:
                print(f"[DEBUG] p{i:3d}: {sid:12s} -> {discipline or 'n/a':12s} [{verdict}] (via {source})", file=sys.stderr)

            results.append({
                "page_num": i,
                "sheet_id": sid,
                "discipline": discipline,
                "verdict": verdict,
                "snippet": text[:80].replace("\n", " "),
                "source": source,
            })

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def default_output_path(source_pdf: Path, job: str, location: str) -> Path:
    if job and location:
        name = f"{job}_{location}_MEP-Scope.pdf"
    elif job:
        name = f"{job}_MEP-Scope.pdf"
    elif location:
        name = f"{location}_MEP-Scope.pdf"
    else:
        name = f"{source_pdf.stem}_MEP-Scope.pdf"

    desktop = Path.home() / "Desktop"
    return desktop / name


def print_sheet_list(pages: list[dict]) -> None:
    from collections import defaultdict
    by_discipline: dict[str, list] = defaultdict(list)
    skipped = []

    for p in pages:
        if p["verdict"] == "keep" and p["discipline"]:
            by_discipline[p["discipline"]].append(p)
        elif p["sheet_id"] and p["verdict"] == "exclude":
            skipped.append(p)

    order = ["Mechanical", "Plumbing", "Electric", "Fire Alarm"]
    for disc in order:
        sheets = by_discipline.get(disc, [])
        if sheets:
            print(f"\n{disc}")
            for s in sheets:
                print(f"  p{s['page_num']:3d}  {s['sheet_id']}")

    if skipped:
        print("\n-- Excluded (boilerplate / specs / compliance) --")
        for s in skipped:
            print(f"  p{s['page_num']:3d}  {s['sheet_id']:12s}  {s['discipline'] or ''}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Auto-extract MEP/FA scope from a full plan set PDF.")
    parser.add_argument("--pdf",       required=True,  help="Source PDF path (can be 30MB+, no attachment needed)")
    parser.add_argument("--out",       default=None,   help="Output PDF path (default: Desktop/<job>_<loc>_MEP-Scope.pdf)")
    parser.add_argument("--job",       default="",     help="Job number for output filename")
    parser.add_argument("--location",  default="",     help="Location/store name for output filename")
    parser.add_argument("--list-only", action="store_true", help="Print classified sheet list without extracting")
    parser.add_argument("--debug",     action="store_true", help="Print per-page debug info")
    parser.add_argument("--discipline", default="mepf",      help="Trades to include: any combo of m/e/p/f (e.g. 'mepf'=all, 'e'=electrical only, 'mep'=no FA). Default: mepf")
    parser.add_argument("--include",   default="",          help="Comma-separated pages to force-include. Use PAGE or PAGE:SHEETID to override the detected sheet ID (e.g. '33,28:E-202')")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Parse --include entries: "33" or "28:E-202"
    force_include = {}  # {page_num: sheet_id_override or None}
    if args.include:
        for tok in args.include.split(","):
            tok = tok.strip()
            if ":" in tok:
                parts = tok.split(":", 1)
                if parts[0].isdigit():
                    force_include[int(parts[0])] = parts[1].strip()
            elif tok.isdigit():
                force_include[int(tok)] = None

    # Scan
    pages = scan_pdf(str(pdf_path), debug=args.debug)

    # Apply --include overrides
    if force_include:
        for pg_num, sid_override in sorted(force_include.items()):
            entry = next((p for p in pages if p["page_num"] == pg_num), None)
            if not entry:
                print(f"WARNING: --include page {pg_num} out of range", file=sys.stderr)
                continue
            # Apply sheet ID override if provided
            if sid_override:
                disc, verd = classify_sheet_id(sid_override)
                entry["sheet_id"] = sid_override
                entry["discipline"] = disc or "Manual"
                entry["verdict"] = verd
                if args.debug:
                    print(f"[DEBUG] p{pg_num:3d}: overridden to {sid_override} -> {disc} [{verd}]", file=sys.stderr)
            elif entry["verdict"] != "keep":
                entry["verdict"] = "keep"
                entry["discipline"] = entry["discipline"] or "Manual"
                if args.debug:
                    print(f"[DEBUG] p{pg_num:3d}: force-included via --include", file=sys.stderr)

    # Build discipline filter from shorthand (m/e/p/f)
    disc_flags = args.discipline.lower()
    allowed_disciplines = set()
    if "m" in disc_flags: allowed_disciplines.add("Mechanical")
    if "e" in disc_flags: allowed_disciplines.add("Electric")
    if "p" in disc_flags: allowed_disciplines.add("Plumbing")
    if "f" in disc_flags: allowed_disciplines.add("Fire Alarm")
    if not allowed_disciplines:
        print("ERROR: --discipline must contain at least one of m/e/p/f", file=sys.stderr)
        sys.exit(1)

    # Apply discipline filter: exclude kept pages not in allowed set
    if allowed_disciplines != {"Mechanical", "Electric", "Plumbing", "Fire Alarm"}:
        for p in pages:
            if p["verdict"] == "keep" and p["discipline"] not in allowed_disciplines:
                p["verdict"] = "exclude"

    # Report
    keep_pages = [p for p in pages if p["verdict"] == "keep"]
    print_sheet_list(pages)

    if args.list_only:
        print(f"\nTotal pages to keep: {len(keep_pages)} of {len(pages)}")
        return

    if not keep_pages:
        print("\nNo MEP/FA scope pages found. Check --debug for details.", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = default_output_path(pdf_path, args.job, args.location)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for p in keep_pages:
        writer.add_page(reader.pages[p["page_num"] - 1])

    with open(out_path, "wb") as f:
        writer.write(f)

    print(f"\nExtracted {len(keep_pages)} pages -> {out_path}")


if __name__ == "__main__":
    main()
