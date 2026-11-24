@echo off
chcp 65001 >nul
rem Arrastra encima el tramo_….json que baja la página de ritmo («💾 Guardar el trozo»). Sin nada: el más reciente de Descargas.
rem Python: el de %USERPROFILE%\venvs\analizar_tango si existe; si no, el que haya en el PATH
set "TDJ_PY=%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe"
if not exist "%TDJ_PY%" set "TDJ_PY=python"
"%TDJ_PY%" -X utf8 "%~dp0clip_reel.py" %*
if not defined TDJ_SIN_PAUSA pause
