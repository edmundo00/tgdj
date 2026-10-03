@echo off
rem Genera dist\TangoTags\TangoTags.exe (no hace falta Python para abrirlo).
rem El .exe usa config.ini, data\ y resources\ de esta carpeta del proyecto.
rem Se compila fuera de Dropbox (Dropbox bloquea los archivos mientras sincroniza) y luego se copia.
cd /d "%~dp0"
set COMPILAR=%LOCALAPPDATA%\TangoTags_compilacion
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name TangoTags ^
    --exclude-module tkinter ^
    --hidden-import control_slides ^
    --hidden-import src.biblioteca.trabajador ^
    --collect-submodules av ^
    --distpath "%COMPILAR%\dist" --workpath "%COMPILAR%\build" ^
    tangotags.py
if errorlevel 1 goto error
robocopy "%COMPILAR%\dist\TangoTags" "dist\TangoTags" /MIR /R:10 /W:3 /NFL /NDL /NJH /NP
if errorlevel 8 goto error
echo.
echo Listo: dist\TangoTags\TangoTags.exe
pause
exit /b 0
:error
echo.
echo Algo fallo al crear el .exe (mira los mensajes de arriba).
pause
exit /b 1
