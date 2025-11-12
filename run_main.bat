@echo off
cd /d "%~dp0"

call .venv\Scripts\activate.bat
uv run main.py
