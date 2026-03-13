# User Guide

Tools for processing construction plan sets and rollout schedules. No installation required — download and run.

---

## Getting Started

1. Go to the [Releases](../../../releases) tab on GitHub
2. Under the latest release, download the `.exe` file(s) you need
3. Save them anywhere on your computer (Desktop works fine)
4. Double-click or run from Command Prompt as shown below

> These are standalone programs — no Python, no installs, nothing else required.

---

## Tool 1: MEP Auto-Extractor

**What it does:** Takes a full construction plan set PDF and extracts only the MEP/FA sheets needed for subcontractor pricing. Filters out details, specs, and compliance pages automatically. Saves the result to your Desktop.

**File:** `mep_auto_extract.exe`

### Basic Usage

Open Command Prompt, navigate to the folder where you saved the `.exe`, and run:

```
mep_auto_extract.exe --pdf "C:\path\to\your\plans.pdf"
```

**Output:** A filtered PDF saved to your Desktop named:
`<JobNumber>_<Location>_MEP-Scope.pdf`

### With Job Info

```
mep_auto_extract.exe --pdf "C:\path\to\plans.pdf" --job 10983 --location "Stratford NJ"
```

### Extract Only One Trade

```
mep_auto_extract.exe --pdf "C:\path\to\plans.pdf" --discipline e
```

Discipline options:
| Flag | Trades Included |
|---|---|
| `mepf` | All trades — Mechanical, Electrical, Plumbing, Fire Alarm (default) |
| `m` | Mechanical only |
| `e` | Electrical only |
| `p` | Plumbing only |
| `f` | Fire Alarm only |
| `me` | Mechanical + Electrical |
| *(any combination)* | Mix and match letters |

### Preview Before Extracting

```
mep_auto_extract.exe --pdf "C:\path\to\plans.pdf" --list-only
```

Prints which pages would be included without writing any files.

### Force-Include Specific Pages

If a page was missed (common with image-heavy plans):

```
mep_auto_extract.exe --pdf "C:\path\to\plans.pdf" --include "33,40"
```

### Custom Output Location

```
mep_auto_extract.exe --pdf "C:\path\to\plans.pdf" --out "C:\Users\YourName\Documents\output.pdf"
```

---

## Tool 2: Rollout Schedule Extractor

**What it does:** Reads a retail construction timetable PDF and extracts all milestone dates. Calculates how many days each milestone is before or after the construction start date. Outputs a CSV for tracking.

**File:** `rollout_schedule_extractor.exe`

### Basic Usage

```
rollout_schedule_extractor.exe --pdf "C:\path\to\timetable.pdf" --project "Dollar Tree" --store "10983" --location "Stratford NJ"
```

**Output:** A CSV saved to your Desktop named:
`<store>_<location>_Rollout-Schedule.csv`

### Preview Without Saving

```
rollout_schedule_extractor.exe --pdf "C:\path\to\timetable.pdf" --dry-run
```

### Append to an Existing Master Tracker

```
rollout_schedule_extractor.exe --pdf "C:\path\to\timetable.pdf" --store "10984" --location "Camden NJ" --append "C:\path\to\master-tracker.csv"
```

### Override the Anchor Milestone

The anchor defaults to "Construction Scheduled Start". To use a different milestone as day 0:

```
rollout_schedule_extractor.exe --pdf "C:\path\to\timetable.pdf" --anchor "Developer Construction Start Date"
```

---

## Tool 3: Plan Sheet Classifier *(support tool)*

**What it does:** Reads a plan set and prints every MEP/FA sheet ID grouped by discipline. Useful for checking what's in a plan set before extracting.

**File:** `classify_plan_sheets.exe`

```
classify_plan_sheets.exe --pdf "C:\path\to\plans.pdf"
```

---

## Tool 4: MEP Page Extractor *(support tool)*

**What it does:** Manually pulls specific pages out of a PDF by page number. Use this when you need precise control over which pages to extract.

**File:** `extract_mep_pages.exe`

```
extract_mep_pages.exe --pdf "C:\path\to\plans.pdf" --pages "13,15-32" --out "C:\Users\YourName\Desktop\output.pdf"
```

Page ranges like `15-32` are supported. Pages are 1-based (page 1 = first page of the PDF).

---

## Tips

- **Drag and drop paths:** In Windows Explorer, hold Shift and right-click a file, then choose "Copy as path" to get the full path with quotes ready to paste.
- **Path with spaces:** Always wrap file paths in quotes if they contain spaces.
- **Output always goes to Desktop** unless you specify `--out`.
- If a tool seems to miss sheets, use `--list-only` first to see what it detects, then use `--include` to add any missed pages.
