# HW Workspace Tools

Construction document processing tools for plan set extraction and rollout schedule analysis.

---

## Tools

### 1. MEP Auto-Extractor
Scans a full plan set PDF, identifies MEP/FA sheets, applies scope-filtering rules, and outputs a clean PDF ready for subcontractor pricing. Outputs to your Desktop automatically.

**Keep:** Floor plans (x-1xx), schedules (x-2xx), single-lines, legends (x-0xx), FA new-work plans
**Exclude:** Details (x-3xx), specs (x-4xx), sequence-of-ops, compliance sheets (EN-xxx), FA spec sheets

### 2. Rollout Schedule Extractor
Extracts milestone dates from retail construction timetable PDFs. Calculates day offsets from a construction start anchor date and outputs a structured CSV for a master rollout tracker.

### 3. Plan Sheet Classifier *(support tool)*
Reads a plan set PDF and classifies every MEP/FA sheet by discipline (M/P/E/FA). Used as a diagnostic fallback when the auto-extractor needs guidance.

### 4. MEP Page Extractor *(support tool)*
Manually extracts specific pages from a PDF by page number. Used as a fallback when the auto-extractor needs targeted output.

---

## For the Client

**No installation required.** Download the pre-built `.exe` files from the [Releases](../../releases) tab.

See [docs/user_guide.md](docs/user_guide.md) for step-by-step usage instructions.

---

## For Developers

### Repository Structure

```
/
├── README.md               <- This file
├── CHANGELOG.md            <- Version history and update log
├── requirements.txt        <- Python dependencies (for building)
├── execution/              <- Python source scripts
│   ├── mep_auto_extract.py
│   ├── rollout_schedule_extractor.py
│   ├── classify_plan_sheets.py
│   └── extract_mep_pages.py
├── directives/             <- SOPs and business logic rules
│   ├── extract_mepf.md
│   ├── dollar_tree_plan_classifier.md
│   └── rollout_schedule_extractor.md
├── build/                  <- Build scripts for creating .exe files
│   └── build_executables.bat
├── docs/                   <- Documentation
│   ├── user_guide.md       <- Client-facing instructions
│   └── developer_notes.md  <- Update and release workflow
├── CLAUDE.md               <- AI agent instructions (mirrored)
├── AGENTS.md               <- AI agent instructions (mirrored)
└── GEMINI.md               <- AI agent instructions (mirrored)
```

### Architecture

This project uses a 3-layer architecture:

| Layer | Location | Purpose |
|---|---|---|
| Directive | `directives/` | SOPs — what to do and why |
| Orchestration | AI agent | Intelligent routing and error handling |
| Execution | `execution/` | Deterministic Python scripts |

### Building Executables

See [docs/developer_notes.md](docs/developer_notes.md) for the full build and release workflow.

Quick start:
```
build\build_executables.bat
```

### Dependencies

- Python 3.10+
- pdfplumber 0.11.7
- pypdf 6.7.2
- PyInstaller 6.x (for building `.exe` files)

Install: `pip install -r requirements.txt`

---

## Releases

Versioned releases with pre-built `.exe` files are published under the [Releases](../../releases) tab. Each release includes a changelog entry describing what changed.
