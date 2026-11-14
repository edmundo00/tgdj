@echo off
rem Analiza el ritmo de una cancion. Arrastra el audio encima de este .bat, o:
rem   ritmo.bat "ruta\cancion.flac" [--compas 3/4] [--uno 12.3] [--pulso mitad] [--separar]
"%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe" "%~dp0ritmo.py" %*
pause
