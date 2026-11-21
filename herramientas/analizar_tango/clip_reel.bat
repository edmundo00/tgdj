@echo off
chcp 65001 >nul
rem Arrastra encima el tramo_….json que baja la página de ritmo («💾 Guardar el trozo»). Sin nada: el más reciente de Descargas.
if exist C:\ffmpeg\bin set PATH=C:\ffmpeg\bin;%PATH%
"%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe" -X utf8 "%~dp0clip_reel.py" %*
if not defined TDJ_SIN_PAUSA pause
