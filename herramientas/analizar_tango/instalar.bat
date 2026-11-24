@echo off
chcp 65001 >nul
title Instalar el visor de tangos
setlocal
echo ================================================================
echo  Instalar el visor de tangos (solo hace falta una vez)
echo  Tarda unos minutos y baja ~1-2 GB (Python, PyTorch, modelos).
echo ================================================================
echo.

rem ---------- 1. Python
set "PYBASE="
where py >nul 2>nul && (py -3.12 -c "import sys" >nul 2>nul && set "PYBASE=py -3.12")
if not defined PYBASE where py >nul 2>nul && (py -3.13 -c "import sys" >nul 2>nul && set "PYBASE=py -3.13")
if not defined PYBASE where py >nul 2>nul && (py -3.11 -c "import sys" >nul 2>nul && set "PYBASE=py -3.11")
if not defined PYBASE (
  echo [1/3] No hay Python 3.11-3.13. Lo instalo con winget...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto sin_python
  set PYBASE="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
echo [1/3] Python: %PYBASE%

rem ---------- 2. ffmpeg
where ffmpeg >nul 2>nul && goto hay_ffmpeg
if exist "C:\ffmpeg\bin\ffmpeg.exe" goto hay_ffmpeg
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe" goto hay_ffmpeg
echo [2/3] Instalo ffmpeg (para leer y escribir audio) con winget...
winget install -e --id Gyan.FFmpeg --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo.
  echo  No he podido instalar ffmpeg. Bajalo de https://www.gyan.dev/ffmpeg/builds/ ^(release essentials^),
  echo  descomprimelo y deja la carpeta bin en C:\ffmpeg\bin. Luego vuelve a pasar INSTALAR.bat.
  pause
  exit /b 1
)
:hay_ffmpeg
echo [2/3] ffmpeg: listo

rem ---------- 3. Entorno con las librerias
set "VENV=%USERPROFILE%\venvs\analizar_tango"
if not exist "%VENV%\Scripts\python.exe" (
  echo [3/3] Creando el entorno en %VENV% ...
  %PYBASE% -m venv "%VENV%"
  if errorlevel 1 goto sin_python
)
echo [3/3] Instalando las librerias (lo mas largo)...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
set PYTHONUTF8=1
"%VENV%\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo  Algo ha fallado instalando las librerias ^(mira el error de arriba^). Hazle una foto y mandasela a Edmundo.
  pause
  exit /b 1
)
"%VENV%\Scripts\python.exe" -X utf8 -c "import librosa, torch, beat_this; print('Comprobado: todo importa bien')"
echo.
echo ================================================================
echo  LISTO. Ahora abre el visor con ABRIR VISOR.bat
echo ================================================================
pause
exit /b 0

:sin_python
echo.
echo  No he podido instalar Python. Instalalo a mano desde https://www.python.org/downloads/
echo  (version 3.12, marcando "Add python.exe to PATH") y vuelve a pasar INSTALAR.bat.
pause
exit /b 1
