@echo off
rem Doble clic para abrir TangoTags
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" tangotags.py
