@echo off
REM Ensure we run from the script's directory
cd /d "%~dp0"

REM Activate virtual environment (if present)
call .venv\Scripts\activate.bat

REM Run the Python script via uv; pause only if it fails
uv run main.py
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
	echo.
	echo main.py failed with exit code %EXITCODE%.
	echo Press any key to continue...
	pause
)
