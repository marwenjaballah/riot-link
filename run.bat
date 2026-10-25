@echo off
title Riot Link Launcher
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Riot Link exited with error code %ERRORLEVEL%.
    pause
)
