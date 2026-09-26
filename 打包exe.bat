@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo ============================================================
echo   SnapTranslate - build a standalone exe (PyInstaller)
echo   Output: dist\SnapTranslate\
echo ============================================================
echo.
%PY% tools\build.py %*
echo.
pause
