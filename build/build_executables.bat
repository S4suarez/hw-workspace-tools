@echo off
REM ============================================================
REM  Build all HW Workspace tools into standalone .exe files
REM  Requirements: pip install -r requirements.txt
REM  Output:       dist\  (one .exe per tool)
REM ============================================================

echo.
echo === HW Workspace -- Build Executables ===
echo.

REM Check that PyInstaller is available
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller not found.
    echo Run:  pip install -r requirements.txt
    pause
    exit /b 1
)

REM Move to repo root (one level up from build/)
cd /d "%~dp0.."

echo Building mep_auto_extract.exe ...
pyinstaller --onefile --name mep_auto_extract execution\mep_auto_extract.py
if errorlevel 1 ( echo FAILED: mep_auto_extract & pause & exit /b 1 )

echo.
echo Building rollout_schedule_extractor.exe ...
pyinstaller --onefile --name rollout_schedule_extractor execution\rollout_schedule_extractor.py
if errorlevel 1 ( echo FAILED: rollout_schedule_extractor & pause & exit /b 1 )

echo.
echo Building classify_plan_sheets.exe ...
pyinstaller --onefile --name classify_plan_sheets execution\classify_plan_sheets.py
if errorlevel 1 ( echo FAILED: classify_plan_sheets & pause & exit /b 1 )

echo.
echo Building extract_mep_pages.exe ...
pyinstaller --onefile --name extract_mep_pages execution\extract_mep_pages.py
if errorlevel 1 ( echo FAILED: extract_mep_pages & pause & exit /b 1 )

echo.
echo ============================================================
echo  Build complete. Executables are in:  dist\
echo.
echo  Files to upload to GitHub Release:
echo    dist\mep_auto_extract.exe
echo    dist\rollout_schedule_extractor.exe
echo    dist\classify_plan_sheets.exe
echo    dist\extract_mep_pages.exe
echo ============================================================
echo.
pause
