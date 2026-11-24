@echo off
rem Video con destellos en las pisadas: video_pisadas.bat "carpeta marcar_..." [--lento 0.5] [--compases 28-29]
rem Python: el de %USERPROFILE%\venvs\analizar_tango si existe; si no, el que haya en el PATH
set "TDJ_PY=%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe"
if not exist "%TDJ_PY%" set "TDJ_PY=python"
"%TDJ_PY%" -X utf8 "%~dp0video_pisadas.py" %*
if not defined TDJ_SIN_PAUSA pause
