@echo off
rem Junta 2, 3 o 4 canciones para compararlas y alternarlas. Arrastra los audios encima de este .bat, o:
rem   juntar.bat "cancion1.flac" "cancion2.flac" [cancion3] [cancion4]
rem Python: el de %USERPROFILE%\venvs\analizar_tango si existe; si no, el que haya en el PATH
set "TDJ_PY=%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe"
if not exist "%TDJ_PY%" set "TDJ_PY=python"
"%TDJ_PY%" "%~dp0juntar.py" --abrir %*
rem TDJ_SIN_PAUSA=1 evita la pausa cuando lo lanza otro programa
if not defined TDJ_SIN_PAUSA pause
