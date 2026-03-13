# Changelog

All notable changes to this project are documented here.

Format: `[vX.Y.Z] - YYYY-MM-DD`
- **Added** — new features or tools
- **Changed** — changes to existing behavior
- **Fixed** — bug fixes
- **Notes** — context, edge cases, or client-specific observations

---

## [v1.0.0] - 2026-03-12

### Added
- `mep_auto_extract.py` — Automated MEP/FA scope extractor. Scans plan sets, classifies sheets by discipline, applies filtering rules, outputs clean PDF to Desktop.
- `rollout_schedule_extractor.py` — Retail construction timetable extractor. Reads milestone dates, calculates day offsets from anchor date, outputs CSV.
- `classify_plan_sheets.py` — Support tool. Classifies plan set sheets by discipline (M/P/E/FA).
- `extract_mep_pages.py` — Support tool. Manually extracts specific pages from a PDF by page number.
- `directives/extract_mepf.md` — SOP for MEP scope filtering rules (universal).
- `directives/dollar_tree_plan_classifier.md` — SOP for Dollar Tree plan classification.
- `directives/rollout_schedule_extractor.md` — SOP for rollout schedule extraction.
- Initial documentation: README, user guide, developer notes, build scripts.

### Notes
- Tested on Dollar Tree Accruent timetable format (DT 10983 Stratford, NJ).
- MEP extractor uses three detection fallbacks: pdfplumber text, PDF PageLabels, and --include flag for image-based pages.
- Output paths use `Path.home() / "Desktop"` — works on any Windows machine regardless of username.

---

<!-- Template for future releases:

## [vX.Y.Z] - YYYY-MM-DD

### Added
-

### Changed
-

### Fixed
-

### Notes
-

-->
