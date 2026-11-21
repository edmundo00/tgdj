@echo off
rem Video con destellos en las pisadas: video_pisadas.bat "carpeta marcar_..." [--lento 0.5] [--compases 28-29]
"%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe" -X utf8 "%~dp0video_pisadas.py" %*
if not defined TDJ_SIN_PAUSA pause
