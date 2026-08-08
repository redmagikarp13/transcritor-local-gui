@echo off
cd /d "%~dp0"

IF EXIST ".venv" (
    call .venv\Scripts\Activate.ps1
    rem Se não puder usar ps1 no cmd, tenta o bat
    if errorlevel 1 call .venv\Scripts\activate.bat
)

python gui\main.py
pause
