@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYW=pythonw
where pythonw >nul 2>nul || set PYW=python
start "" %PYW% "%~dp0main.py"
exit
