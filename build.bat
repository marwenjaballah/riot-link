@echo off
title Build Riot Link Executable
cd /d "%~dp0"

echo ========================================================
echo               Building Riot Link Standalone
echo ========================================================
echo.

echo [1/3] Checking dependencies...
python -m pip install -r requirements.txt

echo.
echo [2/3] Compiling with PyInstaller...
pyinstaller --clean -y RiotLink.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed! Check the console output above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Build succeeded!
echo The standalone executable is ready at: dist\RiotLink.exe
echo.
pause
