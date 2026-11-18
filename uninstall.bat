@echo off
rem Radial Wheel - graphical uninstaller.
cd /d "%~dp0"
start "" powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1" %*
exit
