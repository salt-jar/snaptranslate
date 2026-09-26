@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo ============================================================
echo   Download offline translation language packs
echo   Offline translation = text never leaves this computer
echo ============================================================
echo.
echo   Usage:
echo     %PY% tools\offline_pack.py --available          list packs
echo     %PY% tools\offline_pack.py --installed          show installed
echo     %PY% tools\offline_pack.py --download zh-en     download one
echo     %PY% tools\offline_pack.py --download-popular   download common pairs
echo.
echo   You can also download packs inside the app:
echo     Settings - Translation engines - Manage offline packs
echo.
%PY% tools\offline_pack.py %*
echo.
pause
