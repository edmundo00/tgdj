@echo off
rem Prepara la pagina para marcar pisadas: marcar_pisadas.bat "video.mp4" "cancion.flac" --compases 26-30 --bailarines "Sol,London"
rem Python: el de %USERPROFILE%\venvs\analizar_tango si existe; si no, el que haya en el PATH
set "TDJ_PY=%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe"
if not exist "%TDJ_PY%" set "TDJ_PY=python"
"%TDJ_PY%" -X utf8 "%~dp0marcar_pisadas.py" %*
if not defined TDJ_SIN_PAUSA pause
