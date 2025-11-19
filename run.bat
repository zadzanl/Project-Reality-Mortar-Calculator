@echo off
REM Project Reality Mortar Calculator - Windows Launcher
REM Double-click this file to start the calculator

echo ====================================
echo PR MORTAR CALCULATOR - Starting...
echo ====================================
echo.

REM Change to the directory where this script is located
cd /d "%~dp0"

REM Try to detect Python installation
REM Windows Python Launcher (py) - recommended method
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Found Python via py launcher
    py calculator\server.py
    goto :end
)

REM Try python3 command
where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Found Python via python3 command
    python3 calculator\server.py
    goto :end
)

REM Try python command
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Found Python via python command
    python calculator\server.py
    goto :end
)

REM Python not found - show error message
echo.
echo ====================================
echo ERROR: Python not found
echo ====================================
echo.
echo Python 3.8 or newer is required to run this calculator.
echo.
echo Please install Python from:
echo   https://www.python.org/downloads/
echo.
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:end
REM Server stopped - clean exit
echo.
echo ====================================
echo Server stopped.
echo You can close this window.
echo ====================================
echo.
pause
