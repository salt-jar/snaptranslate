@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Running self test (deps / OCR / translation)...
echo.
%PY% tools\selftest.py %*
echo.
pause
