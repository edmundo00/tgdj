@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m unittest discover -s tests -p "*_test.py" -v
pause
