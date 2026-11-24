@echo off
rem Analiza un tango. Arrastra el archivo de audio encima de este .bat, o: analizar_tango.bat "ruta\cancion.flac"
rem Python: el de %USERPROFILE%\venvs\analizar_tango si existe; si no, el que haya en el PATH
set "TDJ_PY=%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe"
if not exist "%TDJ_PY%" set "TDJ_PY=python"
"%TDJ_PY%" "%~dp0analizar_tango.py" %*
rem TDJ_SIN_PAUSA=1 evita la pausa cuando lo lanza otro programa
if not defined TDJ_SIN_PAUSA pause
