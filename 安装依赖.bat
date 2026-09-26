@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo ============================================================
echo   SnapTranslate - install dependencies into .\vendor
echo ============================================================
echo.
%PY% tools\install_deps.py
echo.
echo If everything above shows OK, run  启动.bat  to start.
pause
