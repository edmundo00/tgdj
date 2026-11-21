@echo off
rem Analiza un tango. Arrastra el archivo de audio encima de este .bat, o: analizar_tango.bat "ruta\cancion.flac"
"%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe" "%~dp0analizar_tango.py" %*
rem TDJ_SIN_PAUSA=1 evita la pausa cuando lo lanza otro programa
if not defined TDJ_SIN_PAUSA pause
