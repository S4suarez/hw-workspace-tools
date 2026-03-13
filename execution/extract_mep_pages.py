"""
MEP/FA Page Extractor
Extracts specific pages from a plan set PDF and saves them as a new PDF.

Usage:
    python execution/extract_mep_pages.py --pdf <path> --pages <n,n,n> --out <output.pdf>

Example:
    python execution/extract_mep_pages.py --pdf plans.pdf --pages 13,15-32 --out .tmp/MEP_only.pdf
"""

import argparse
import sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("ERROR: pypdf not installed. Run: pip install pypdf", file=sys.stderr)
    sys.exit(1)


def parse_page_spec(spec: str) -> list[int]:
    """Parse a page spec like '1,3,5-10,12' into a list of 1-based page numbers."""
    pages = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return pages


def extract_pages(pdf_path: str, page_numbers: list[int], output_path: str) -> None:
    """Extract 1-based page_numbers from pdf_path and write to output_path."""
    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    writer = PdfWriter()

    for pnum in page_numbers:
        if pnum < 1 or pnum > total:
            print(f"WARNING: Page {pnum} out of range (PDF has {total} pages) — skipped", file=sys.stderr)
            continue
        writer.add_page(reader.pages[pnum - 1])

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)

    print(f"Wrote {len(writer.pages)} pages -> {out}")


def main():
    parser = argparse.ArgumentParser(description="Extract specific pages from a PDF.")
    parser.add_argument("--pdf",   required=True, help="Source PDF path")
    parser.add_argument("--pages", required=True, help="Page numbers to extract, e.g. '13,15-32'")
    parser.add_argument("--out",   required=True, help="Output PDF path")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    page_numbers = parse_page_spec(args.pages)
    extract_pages(str(pdf_path), page_numbers, args.out)


if __name__ == "__main__":
    main()
