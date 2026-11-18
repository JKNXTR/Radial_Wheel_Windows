@echo off
rem Optional: builds a standalone RadialWheel.exe (dist\RadialWheel). install.bat then installs it without Python.
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3.9-3.13 is required to build. & pause & exit /b 1)
python -m venv build\venv || goto :err
call build\venv\Scripts\activate.bat
python -m pip install --upgrade pip || goto :err
python -m pip install -r requirements-dev.txt || goto :err
pyinstaller --noconfirm --clean --windowed --name RadialWheel --icon app\assets\app.ico ^
  --paths app --add-data "app\assets;assets" --add-data "app\lang;lang" ^
  --collect-submodules comtypes --hidden-import pycaw.pycaw app\main.py || goto :err
echo.
echo Done: dist\RadialWheel\RadialWheel.exe   (now run install.bat)
pause
exit /b 0
:err
echo.
echo BUILD FAILED.
pause
exit /b 1
