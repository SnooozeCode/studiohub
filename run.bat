@echo off
setlocal enabledelayedexpansion

REM ==========================================
REM Ensure script runs from its own directory
REM ==========================================
cd /d "%~dp0"

REM ==========================================
REM Verify virtual environment exists
REM ==========================================
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ERROR: Virtual environment not found.
    echo Expected: .venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

REM ==========================================
REM Run the application
REM ==========================================
echo Starting StudioHub...
echo.

".venv\Scripts\python.exe" -m studiohub
set EXITCODE=%ERRORLEVEL%

REM ==========================================
REM Error handling
REM ==========================================
if NOT "%EXITCODE%"=="0" (
    echo.
    echo ==========================================
    echo StudioHub exited with error code %EXITCODE%
    echo ==========================================
    echo.
    pause
)

exit /b %EXITCODE%