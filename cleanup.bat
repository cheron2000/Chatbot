@echo off
REM Cleanup script for legacy files and test artifacts

echo Cleaning up legacy files...

REM Remove legacy Python files
if exist app.py (
    echo Removing app.py...
    del app.py
)

if exist chatinfiltration.py (
    echo Removing chatinfiltration.py...
    del chatinfiltration.py
)

if exist vector_memory.py (
    echo Removing vector_memory.py...
    del vector_memory.py
)

REM Remove test artifacts
echo Removing test artifacts...
del /Q infiltration_results_*.json 2>nul
del /Q infiltration_results_*.csv 2>nul
del /Q infiltration_results_*.html 2>nul
del /Q comparison_*.json 2>nul

REM Remove achievement folder (contains sensitive docs)
if exist achivementfolder (
    echo Removing achivementfolder...
    rmdir /S /Q achivementfolder
)

echo.
echo Cleanup complete!
echo.
echo Removed:
echo - Legacy Python files (app.py, chatinfiltration.py, vector_memory.py)
echo - Test artifacts (infiltration_results_*, comparison_*)
echo - Achievement folder (sensitive documentation)
echo.
echo Your project is now clean and ready for production!
pause
