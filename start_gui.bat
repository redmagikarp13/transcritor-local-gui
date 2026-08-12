@echo off
cd /d "%~dp0"

IF EXIST ".venv" (
    call .venv\Scripts\Activate.ps1
    rem Se não puder usar ps1 no cmd, tenta o bat
    if errorlevel 1 call .venv\Scripts\activate.bat
)

set PYTHONPATH=src
python src\transcritor\gui\main.py
pause
