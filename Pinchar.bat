@echo off
rem Doble clic para abrir Pinchar (el programa para pinchar milongas)
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" pinchar.py
