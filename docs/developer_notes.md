# Developer Notes

How to update scripts, rebuild executables, and publish a new release to GitHub.

---

## Workflow Overview

```
Edit script  ->  Test locally  ->  Build .exe  ->  Commit + Push  ->  Create GitHub Release  ->  Client downloads
```

---

## 1. Making Changes to a Script

All source code lives in `execution/`. Edit the relevant `.py` file, test it with Python directly, then rebuild the executable.

If you discover a new edge case or changed behavior, also update the corresponding directive in `directives/` so the SOP stays accurate.

---

## 2. Testing Locally (with Python)

```bash
python execution/mep_auto_extract.py --pdf "C:\path\to\test.pdf" --list-only
python execution/rollout_schedule_extractor.py --pdf "C:\path\to\timetable.pdf" --dry-run
```

Use `--list-only` / `--dry-run` first so you can verify output before writing files.

---

## 3. Building Executables

### One-Time Setup (first time only)
```
pip install -r requirements.txt
```

### Build All Tools
Double-click `build\build_executables.bat` or run from Command Prompt:
```
build\build_executables.bat
```

Output goes to `dist\`:
```
dist\
  mep_auto_extract.exe
  rollout_schedule_extractor.exe
  classify_plan_sheets.exe
  extract_mep_pages.exe
```

> Note: PyInstaller generates a `build\` subfolder and `.spec` files — these are auto-generated and gitignored. Do not commit them.

### If a Build Fails
- Check that `pip install -r requirements.txt` completed without errors
- Run the PyInstaller command manually to see the full error:
  ```
  pyinstaller --onefile --name mep_auto_extract execution\mep_auto_extract.py
  ```

---

## 4. Updating the Changelog

Before pushing, add an entry to [CHANGELOG.md](../CHANGELOG.md):

```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Changed
- Brief description of what changed and why

### Fixed
- Any bugs resolved

### Notes
- Edge cases or client-specific context
```

**Version numbering:**
- `v1.0.0` → `v1.1.0` for new features or added milestones
- `v1.1.0` → `v1.1.1` for bug fixes only
- `v1.0.0` → `v2.0.0` for breaking changes (e.g. CSV column changes)

---

## 5. Committing and Pushing to GitHub

```bash
git add .
git commit -m "v1.1.0 - brief description of change"
git push
```

> Do not commit `dist\`, `build\*.spec`, `build\<tool-name>\`, or `.tmp\`. These are in `.gitignore`.

---

## 6. Creating a GitHub Release (so client can download .exe files)

After pushing:

1. Go to your GitHub repo → **Releases** → **Draft a new release**
2. Tag: `v1.1.0` (match the version in CHANGELOG.md)
3. Title: `v1.1.0 - brief description`
4. Body: paste the relevant CHANGELOG.md entry
5. Under **Assets**, attach the `.exe` files from `dist\`:
   - `mep_auto_extract.exe`
   - `rollout_schedule_extractor.exe`
   - `classify_plan_sheets.exe`
   - `extract_mep_pages.exe`
6. Publish release

Client then goes to the Releases tab, finds the latest release, and downloads the `.exe` files they need.

---

## 7. Sending to Client

Share the link to the Releases page:
```
https://github.com/S4suarez/<repo-name>/releases/latest
```

Tell the client to download the `.exe` files and refer to [docs/user_guide.md](user_guide.md) for usage.

---

## 8. File Reference

| File | What to edit |
|---|---|
| `execution/*.py` | Actual tool logic |
| `directives/*.md` | SOPs and business rules |
| `CHANGELOG.md` | Every release gets an entry here |
| `docs/user_guide.md` | Update if commands or behavior changes |
| `requirements.txt` | Add/update Python dependencies |
| `build/build_executables.bat` | Update if a new script is added |

---

## Common Issues

**Script finds wrong sheets / misses sheets**
- Run with `--list-only` or `--dry-run` to inspect what's being detected
- Check `directives/extract_mepf.md` for filtering rules
- Add missed pages manually with `--include "33,40"`

**pdfplumber fails on a PDF**
- Some PDFs are fully image-based and have no extractable text
- Use the `--include` flag to force-add those pages by page number

**Date not found in rollout timetable**
- Check if the milestone label matches the whitelist in `rollout_schedule_extractor.py` (search for `KNOWN_MILESTONES`)
- Add the new label to the whitelist and rebuild

**Built .exe crashes on client machine**
- Make sure you built on a Windows machine (PyInstaller builds are OS-specific)
- Re-run the build script and retest the new `.exe` locally before uploading
