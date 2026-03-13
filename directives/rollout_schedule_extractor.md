# Retail Construction Timetable Date Extractor — Directive

## Goal
Extract milestone dates from retail construction timetable / rollout schedule PDFs, convert them into relative schedule offsets from an anchor date, and output structured rows ready to append into a master rollout tracker (CSV or Excel).

This directive is **completely separate** from the MEP Scope Extraction directive. Do not use MEPF scripts for this task.

---

## Inputs
- One or more timetable/rollout schedule PDFs (file path provided by user)
- Optional: project name, store number, or location override if not readable from the document

---

## What to Extract

Extract only milestone-style schedule items. Examples (not exhaustive):

| Category | Examples |
|---|---|
| Construction | Construction Scheduled Start, Construction Complete, Punchlist Complete |
| Delivery | Lock Delivery, Safe Delivery, HVAC Equipment Delivery, Electric Panel Delivery, Cooler/Freezer/Ice Box Delivery |
| Install | Flooring Date, Burglar Alarm Install, Sign Installed Date |
| Arrival | SDC Arrival |
| Turnover | Turnover, Est Turnover |
| Opening | Estimated Open Date, Est Open Date |
| HVAC | HVAC Equipment Delivery |
| Refrigeration | Cooler Delivery, Freezer Delivery, Ice Box Delivery |
| IT | IT Installation Start Date |
| Utility | Stock Delivery |
| Sitework | Landscaping Date |

**Ignore completely:**
- Contact names, phone numbers, voicemail references, staff lists
- Vendor names not tied to a dated milestone
- Empty or undated fields
- Generic header/footer/export software text
- Comments without actual schedule dates

---

## Anchor Date Logic

1. **Default anchor:** `Construction Scheduled Start`
2. **Fallback order** (if Construction Scheduled Start is missing):
   1. Developer Construction Start Date
   2. Est Turnover
   3. Earliest major construction-related milestone date
3. Record which milestone was used as anchor in the output

---

## Offset Calculation

```
Offset Days = Milestone Date - Anchor Date
```

- Anchor milestone itself = 0
- Milestone before anchor = negative offset
- Two milestones with same date but different labels = keep as separate rows

---

## Normalization Rules
- Dates → `YYYY-MM-DD`
- Preserve original milestone label in `Original Milestone Label`
- Create cleaned version in `Clean Milestone Label`
- Do not invent missing dates
- Unclear label → keep original wording, mark `Needs Review = TRUE`
- Date without year → infer only if obvious from surrounding dates; otherwise flag

---

## Execution Steps

### Run the extractor

```bash
python execution/rollout_schedule_extractor.py \
  --pdf "<full path to PDF>" \
  --project "<project name>" \
  --store "<store number>" \
  --location "<city, state>"
```

Output goes to Desktop as `<store>_<location>_Rollout-Schedule.csv`

### Optional flags

| Flag | Purpose |
|---|---|
| `--out <path>` | Override output path |
| `--append <path>` | Append rows to an existing master CSV instead of creating a new file |
| `--debug` | Print per-page extraction details |
| `--anchor "<label>"` | Override the anchor milestone label |

### Preview without writing output

```bash
python execution/rollout_schedule_extractor.py --pdf "<path>" --dry-run
```

---

## Output Format

### Main table (CSV columns)

| Column | Notes |
|---|---|
| Project Name | From document or `--project` flag |
| Store Number | From document or `--store` flag |
| Location | From document or `--location` flag |
| Anchor Milestone | Label of the milestone used as day-0 |
| Anchor Date | YYYY-MM-DD |
| Milestone Category | Construction / Delivery / Install / etc. |
| Original Milestone Label | Verbatim from document |
| Clean Milestone Label | Normalized label |
| Milestone Date | YYYY-MM-DD |
| Offset Days | Integer (can be negative) |
| Source Page | 1-based page number where found |
| Confidence | High / Medium / Low |
| Needs Review | TRUE / FALSE |

### Summary section (appended after main table)

```
--- SUMMARY ---
Anchor Used: Construction Scheduled Start (2026-02-23)
Total Milestones Extracted: 12
Milestones Needing Review: 1
Duplicate/Conflicting Dates: 0
Earliest Milestone: 2026-02-23 (Construction Scheduled Start, offset 0)
Latest Milestone: 2026-04-30 (Est Open Date, offset +66)
```

---

## Master Tracker Behavior
- When `--append` is used, new rows are added to the bottom of the existing CSV with no column changes
- Each project is a separate group — do not merge stores together
- Column headers are written only when creating a new file

---

## Naming Convention
- Intermediate: `.tmp/<store>_<location>_Rollout-Schedule.csv`
- Desktop deliverable: `<store>_<location>_Rollout-Schedule.csv`
- Master tracker: user-specified path passed via `--append`

---

## Self-Annealing Notes

### Tested: Dollar Tree Accruent timetable (DT 10983 Stratford, NJ)

**Layout:** 5-page PDF with 8-char left margin and a two-column layout starting at character ~43.
pdfplumber `layout=True` preserves column structure. Column split detected from the END of
whitespace gaps (not the midpoint), which correctly handles rows where left-column content
varies in length.

**Known edge case — "Vendor" word split at column boundary:**
When a left-column label ending in "Vendor" (e.g. "Candy Merchandiser/Helium Tank Vendor")
crosses the col_split position, the suffix "or" bleeds into the right column and appears in
the "Original Milestone Label" field as a prefix (e.g. "or Candy Merchandiser...").
The **Clean Milestone Label is still correct** because whitespace is normalized before keyword
matching. This is a cosmetic issue only; no data is wrong.

**Milestones correctly extracted:** 36 (including Construction Scheduled Start as anchor)
**Pages with data:** Pages 3, 4, 5 (pages 1-2 are staff/contact lists — no milestones)

**Other notes:**
- Pages 1-2 are always noise (staff lists, phone numbers) — correctly return 0 milestones
- Footer URL "https://accruent.dollartree.com/..." appears on every page — filtered by URL check
- "SDC           Arrival" (extra internal spaces) — handled by whitespace normalization in match_known_milestone()
- Date formats seen: `MM/DD/YYYY` only — others supported but not yet encountered

---

## Example

Input:
```
Construction Scheduled Start: 02/23/2026
Lock Delivery: 03/02/2026
Safe Delivery: 03/16/2026
Construction Complete: 04/03/2026
Est Open Date: 04/30/2026
```

Expected output:

| Milestone | Date | Offset Days |
|---|---|---|
| Construction Scheduled Start | 2026-02-23 | 0 |
| Lock Delivery | 2026-03-02 | +7 |
| Safe Delivery | 2026-03-16 | +21 |
| Construction Complete | 2026-04-03 | +39 |
| Est Open Date | 2026-04-30 | +66 |
