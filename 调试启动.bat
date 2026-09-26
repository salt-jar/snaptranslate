@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Starting SnapTranslate with console output (for debugging)...
echo Close this window or press Ctrl+C to stop.
echo.
%PY% "%~dp0main.py"
echo.
echo Program exited.
pause
