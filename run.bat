@echo off
REM File Search & Launcher - Windows Launcher
REM This batch file launches the Python application

echo Starting File Search & Launcher...
pythonw file_search_launcher.py

REM If pythonw is not found, try python
if errorlevel 1 (
    echo Trying alternative Python launcher...
    python file_search_launcher.py
)

if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org
    echo.
    pause
)
