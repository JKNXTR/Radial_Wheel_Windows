@echo off
rem Radial Wheel - graphical installer (no console window, no administrator rights).
cd /d "%~dp0"
start "" powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
exit
