@echo off
rem Analiza el ritmo de una cancion. Arrastra el audio encima de este .bat, o:
rem   ritmo.bat "ruta\cancion.flac" [--compas 3/4] [--uno 12.3] [--pulso mitad] [--separar]
rem Python: el de %USERPROFILE%\venvs\analizar_tango si existe; si no, el que haya en el PATH
set "TDJ_PY=%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe"
if not exist "%TDJ_PY%" set "TDJ_PY=python"
"%TDJ_PY%" "%~dp0ritmo.py" --abrir %*
rem TDJ_SIN_PAUSA=1 evita la pausa cuando lo lanza otro programa
if not defined TDJ_SIN_PAUSA pause
