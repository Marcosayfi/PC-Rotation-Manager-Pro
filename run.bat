@echo off
REM PC Rotation Manager Pro - Normal Run
REM Uses python.exe (not pythonw.exe) for reliable operation on all systems.
REM The console window can be minimized.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    py main.py
)
