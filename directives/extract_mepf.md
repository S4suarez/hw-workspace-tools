# MEP Scope Extraction Directive

## Goal
When a plan set PDF is dropped in, extract only the **actionable subcontractor-scope sheets** for Mechanical, Plumbing, Electrical, and Fire Alarm trades. Strip all boilerplate, narrative, and compliance sheets. Output a clean PDF ready to share for subcontractor pricing.

## Inputs
- Source PDF (full plan set or pre-filtered MEP/FA set)
- If a full plan set: first run `execution/classify_sheets.py` or use the Dollar Tree Plan Classifier directive to isolate MEP/FA pages
- If already a MEP/FA set: proceed directly to filtering

## Filtering Rules

### KEEP — Actionable Scope
| Sheet Type | Examples |
|---|---|
| Floor plans | M-101, P-101, E-101, E-102, FA1, FAD1 |
| Schedules | M-201, P-201, E-201 |
| Single-line diagrams | E-202 |
| Legends / symbols | E-001 |
| Fire alarm new-work plans | FA1, FA2, FAD1 |

**Rule of thumb:** If a subcontractor needs it to count equipment, size materials, or understand layout — keep it.

### EXCLUDE — Boilerplate / Narrative
| Sheet Type | Examples |
|---|---|
| Details / standard details | M-301, P-301, E-201 (detail sheets) |
| Specifications | M-401, P-401 |
| Sequence of operations | M-402 |
| Compliance / code sheets | EN-101 |
| Fire alarm specifications | FA3 |

**Rule of thumb:** If it's generic, reused across projects, or narrative-heavy — exclude it.

### Sheet Prefix Reference
| Prefix | Trade |
|---|---|
| M- | Mechanical |
| P- | Plumbing |
| E- / EN- | Electrical |
| FA / FAD | Fire Alarm |

## Execution Steps

### Chat Shorthands

When the user says one of these, map it to the `--discipline` flag:

| User says | `--discipline` | Trades extracted |
|---|---|---|
| extract mepf | `mepf` | Mechanical + Electrical + Plumbing + Fire Alarm (all) |
| extract mep | `mep` | Mechanical + Electrical + Plumbing (no FA) |
| extract m | `m` | Mechanical only |
| extract e | `e` | Electrical only |
| extract p | `p` | Plumbing only |
| extract f | `f` | Fire Alarm only |
| extract me | `me` | Mechanical + Electrical |
| (any combo) | letters in any order | corresponding trades |

Default (no shorthand given) = `mepf` (all trades).

### Preferred: Fully Automated (handles large files — no attachment needed)

User provides the file path. Run the auto-extractor which classifies, filters, and extracts in one pass:

```
python execution/mep_auto_extract.py \
  --pdf "<full path to PDF>" \
  --job <job number> \
  --location "<store or location name>"
```

Output goes directly to Desktop as `<job>_<location>_MEP-Scope.pdf`.

Use `--list-only` first to preview the sheet classification before committing:
```
python execution/mep_auto_extract.py --pdf "<path>" --list-only
```

Use `--debug` to see per-page sheet ID detection if results look wrong.

Use `--include` to force-add specific pages by 1-based page number (for fully image-based pages):
```
python execution/mep_auto_extract.py --pdf "<path>" --job 1234 --location "Store" --include 33,40
```

### Non-Standard / Project-Specific Sheets

Some plan sets include sheets beyond the standard numbering series. These are **project-specific scope pages** — not present on every job, but always actionable when they appear. Examples:

| Sheet | Type | Notes |
|---|---|---|
| FAD1, FAD2 | Fire Alarm Drawings | Project-specific FA detail/drawing sheets. Not in every set. |
| E-202, E-103, E-103A | Additional Electrical | Extra schedules or plans added per project scope. |
| P1, P2 | Unnumbered Plumbing | Some sets use bare numbers instead of P-101 style. |

These pages are already classified as KEEP by the script. Detection issues arise when:
- **Title block uses non-standard fonts** → text extraction picks up wrong content (e.g. equipment model numbers). The script's **page-label fallback** handles this automatically.
- **Page is fully image-based (scanned)** → no text or labels at all. Use `--include` to force-add by page number.

When `--debug` output shows a page as `n/a [exclude]` but you know it's a scope sheet, check:
1. Is the sheet ID in the page label? (debug will show `via label` if so)
2. If not, identify the page number visually and use `--include`.

### Fallback: Manual Page Selection

If the auto-extractor misses sheets (e.g. non-standard sheet numbering), fall back to manual:

1. Run `execution/classify_plan_sheets.py --pdf <path>` to get the sheet list
2. Identify page numbers manually, apply filtering rules above
3. Run extraction:
   ```
   python execution/extract_mep_pages.py \
     --pdf <source.pdf> \
     --pages <comma-separated 1-based page numbers> \
     --out .tmp/<project>_MEP-Scope.pdf
   ```
4. Copy to Desktop: `cp .tmp/<project>_MEP-Scope.pdf ~/Desktop/<project>_MEP-Scope.pdf`

4. **Confirm output** — Report the page count and sheet list to the user.

## Naming Convention
- Intermediate: `.tmp/<JobNumber>_<Location>_MEP-Scope.pdf`
- Desktop deliverable: `<JobNumber>_<Location>_MEP-Scope.pdf`

## Notes
- The `incorrect startxref pointer` warning from pypdf is benign — output is valid.
- If the source PDF is a full plan set (not pre-filtered), pages shift — always verify page numbers after classification before running extraction.
- When in doubt about a sheet, ask the user before excluding. Default to keeping if it shows field-measurable content.
