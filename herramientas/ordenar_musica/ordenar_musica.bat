@echo off
rem Ordenar toda la musica (PLAN_ORDENAR_MUSICA.md), fases 1-4. No toca ningun archivo de musica.
rem Se puede cortar y volver a lanzar: sigue donde lo dejo.
cd /d "%~dp0"
set PY=%USERPROFILE%\venvs\analizar_tango\Scripts\python.exe
"%PY%" -X utf8 huellas_todas.py --procesos 5 || goto fin
"%PY%" -X utf8 huellas_todas.py --recodo --procesos 5 || goto fin
"%PY%" -X utf8 grupos.py || goto fin
python -X utf8 fichas.py
:fin
if not defined TDJ_SIN_PAUSA pause
