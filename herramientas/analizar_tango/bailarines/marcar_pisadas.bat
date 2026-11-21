@echo off
rem Prepara la pagina para marcar pisadas: marcar_pisadas.bat "video.mp4" "cancion.flac" --compases 26-30 --bailarines "Sol,London"
"%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe" -X utf8 "%~dp0marcar_pisadas.py" %*
if not defined TDJ_SIN_PAUSA pause
