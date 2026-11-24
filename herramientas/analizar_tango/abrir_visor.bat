@echo off
chcp 65001 >nul
title Visor de tangos (no cierres esta ventana)
rem Abre el visor de tangos en el navegador, con los botones para analizar canciones desde la página.
set "TDJ_PY=%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe"
if not exist "%TDJ_PY%" (
  echo.
  echo  Falta instalar el programa. Haz doble clic en INSTALAR.bat ^(solo la primera vez^).
  echo.
  pause
  exit /b 1
)
"%TDJ_PY%" -X utf8 "%~dp0servidor.py" %*
if errorlevel 1 pause
