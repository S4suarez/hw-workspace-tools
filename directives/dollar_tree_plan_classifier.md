# Dollar Tree Plan Sheet Classifier

## Role
Read Dollar Tree construction plan PDFs and identify which pages belong to these disciplines: **Mechanical, Plumbing, Electric, Fire Alarm**.

## Inputs
- A Dollar Tree building plan set PDF (may include cover sheet, indices, architectural sheets, and MEP sheets)

## Tools
- `execution/classify_plan_sheets.py` — extracts text from the PDF and classifies sheets

## Output Goal
Return only the sheet IDs grouped under the correct discipline using the exact template. No extra commentary.

---

## Classification Logic

### Step 1: Prefer the Sheet Index
If the set includes a "Sheet Index", "Drawing Index", "Index of Sheets", or similar:
- Extract sheet IDs and their titles from that list
- Classify from that list

Only fall back to title blocks if an index is missing or incomplete.

### Step 2: Sheet ID Patterns (primary signal)
| Discipline  | Patterns                           |
|-------------|------------------------------------|
| Mechanical  | M (e.g. M-101, M1.01, M101)        |
| Plumbing    | P (e.g. P-101, P1.01, P101)        |
| Electric    | E (e.g. E-001, E-101, E1.01, E101) |
| Fire Alarm  | FA, FAD (e.g. FA1, FA2, FA-101)    |

### Step 3: Keyword Backup (when sheet IDs are unclear)
- **Mechanical**: HVAC, RTU, diffusers, duct, air device, mech schedule, ventilation, exhaust, controls
- **Plumbing**: domestic water, sanitary, vent, storm, gas piping, fixtures, water heater
- **Electric**: lighting, power, one-line, panel schedule, receptacles, grounding, site electric, telecom (only if clearly inside electric scope)
- **Fire Alarm**: fire alarm, FA riser, device layout, annunciator, NAC, smoke detector, pull station

---

## Normalization Rules
- Output sheet IDs only — not page numbers
- Preserve exact sheet ID format (hyphens, leading zeros, letters)
- If the same sheet appears multiple times — list it once
- Telecom/low voltage: only include under Electric if the set treats it as part of Electric (often "E" sheets)
- If you cannot confidently classify a sheet — leave it out

---

## Output Template (strict)

Return ONLY this template with four headings in this exact order.
One sheet ID per line. Include heading even if no sheets found.

```
Mechanical
<sheet id>
<sheet id>

Plumbing
<sheet id>
<sheet id>

Electric
<sheet id>
<sheet id>

Fire Alarm
<sheet id>
<sheet id>
```

---

## Execution Flow

1. Run `execution/classify_plan_sheets.py --pdf <path_to_pdf>`
2. Script extracts text from all pages
3. Script locates sheet index (if present) and extracts sheet IDs + titles
4. Script classifies each sheet ID by pattern, then keyword
5. Script outputs the classified result in template format

---

## Edge Cases & Learnings
- Some Dollar Tree sets use hyphenated IDs (M-101), others use decimal (M1.01) — preserve as-is
- Cover sheets and architectural sheets (A-xxx) are ignored
- If sheet index spans multiple pages, the script reads all of them before classifying
