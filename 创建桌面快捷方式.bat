@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Creating desktop shortcut...
%PY% tools\make_shortcut.py %*
echo.
pause
