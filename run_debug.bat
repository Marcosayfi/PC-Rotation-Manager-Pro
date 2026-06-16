@echo off
REM PC Rotation Manager Pro - Debug Run (With Console Window)
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    py main.py
)
pause
