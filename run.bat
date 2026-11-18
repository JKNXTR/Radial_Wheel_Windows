@echo off
rem Run from source without installing (no console window). Needs Python 3.9-3.13 and: pip install -r requirements.txt
cd /d "%~dp0app"
if exist "%LOCALAPPDATA%\RadialWheel\venv\Scripts\pythonw.exe" (
  start "" "%LOCALAPPDATA%\RadialWheel\venv\Scripts\pythonw.exe" main.py --show
) else (
  start "" pythonw main.py --show
)
