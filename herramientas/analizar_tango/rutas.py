"""Dónde están las cosas (carpeta de trabajo, música, partituras, ffmpeg, pythons de cada modelo).

Todas las herramientas de analizar_tango sacan las rutas de aquí, para que funcionen en cualquier ordenador.

Orden para elegir la carpeta de trabajo (TDJ):
  1. la variable de entorno TDJ_DIR
  2. "tdj" en rutas_local.json (junto a este archivo; no se sube a git). Ejemplo:
        {"tdj": "C:/Users/yo/Tango", "analisis": "C:/Users/yo/Tango/Analisis tangos"}
  3. D:\\Dropbox\\TDJ si existe (el ordenador de Edmundo)
  4. la carpeta «TDJ» dentro de la carpeta del usuario

Dentro de TDJ:
  Analisis tangos\\   los análisis (_ritmo, _datos, _juntar) y la página ritmo.html   (TDJ_ANALISIS para cambiarla)
  MUSICA\\            donde se buscan los audios guardados con ruta relativa
  Partituras\\convertidas\\   donde se buscan las partituras .mxl
"""
import os, json, glob, shutil

AQUI = os.path.dirname(os.path.abspath(__file__))


def _local():
    f = os.path.join(AQUI, "rutas_local.json")
    try:
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


_L = _local()
# las rutas de rutas_local.json pueden ser relativas a esta carpeta (p. ej. "../Analisis tangos" en el paquete para compartir)
for _k in ("tdj", "analisis", "venvs"):
    if _L.get(_k) and not os.path.isabs(_L[_k]):
        _L[_k] = os.path.join(AQUI, _L[_k])


def _elegir_tdj():
    if os.environ.get("TDJ_DIR"):
        return os.environ["TDJ_DIR"]
    if _L.get("tdj"):
        return _L["tdj"]
    if os.path.isdir(r"D:\Dropbox\TDJ"):
        return r"D:\Dropbox\TDJ"
    return os.path.join(os.path.expanduser("~"), "TDJ")


TDJ = os.path.normpath(_elegir_tdj())
ANALISIS = os.path.normpath(os.environ.get("TDJ_ANALISIS") or _L.get("analisis") or os.path.join(TDJ, "Analisis tangos"))
RITMO = os.path.join(ANALISIS, "_ritmo")
DATOS = os.path.join(ANALISIS, "_datos")
MUSICA = os.path.join(TDJ, "MUSICA")
PARTITURAS = os.path.join(TDJ, "Partituras", "convertidas")
VENVS = os.path.normpath(os.environ.get("TDJ_VENVS") or _L.get("venvs") or os.path.join(os.path.expanduser("~"), "venvs"))


def python_de(venv):
    """el python de un entorno de ~/venvs (Windows o Linux/Mac)."""
    for p in (os.path.join(VENVS, venv, "Scripts", "python.exe"), os.path.join(VENVS, venv, "bin", "python")):
        if os.path.isfile(p):
            return p
    return os.path.join(VENVS, venv, "Scripts", "python.exe")


def buscar_audio(a):
    """un audio guardado con ruta absoluta o relativa (a MUSICA o a TDJ). None si no está."""
    if not a:
        return None
    for r in (a, os.path.join(MUSICA, a), os.path.join(TDJ, a)):
        if os.path.exists(r):
            return r
    return None


def buscar_partitura(p):
    for r in (p, os.path.join(PARTITURAS, p), os.path.join(TDJ, p)):
        if r and os.path.exists(r):
            return os.path.abspath(r)
    return None


def preparar_ffmpeg():
    """si ffmpeg no está en el PATH, lo busca en las carpetas de siempre y lo añade. Devuelve (ffmpeg, ffprobe)."""
    if not shutil.which("ffmpeg"):
        for d in (os.environ.get("FFMPEG_DIR", ""), r"C:\ffmpeg\bin",
                  os.path.join(os.path.expanduser("~"), "herramientas", "ffmpeg", "bin"),
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links"),   # winget install Gyan.FFmpeg
                  *glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
                                          "Gyan.FFmpeg*", "ffmpeg-*", "bin"))):
            if d and (os.path.isfile(os.path.join(d, "ffmpeg.exe")) or os.path.isfile(os.path.join(d, "ffmpeg"))):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
                break
    return shutil.which("ffmpeg") or "ffmpeg", shutil.which("ffprobe") or "ffprobe"


def buscar_edge():
    """Edge o Chrome para las pruebas sin ventana."""
    for p in (os.environ.get("TDJ_NAVEGADOR", ""),
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              shutil.which("msedge") or "", shutil.which("google-chrome") or "", shutil.which("chromium") or ""):
        if p and os.path.isfile(p):
            return p
    return r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


if __name__ == "__main__":
    for k in ("TDJ", "ANALISIS", "MUSICA", "PARTITURAS", "VENVS"):
        v = globals()[k]
        print(f"{k:11} {v}   {'(existe)' if os.path.isdir(v) else '(NO EXISTE)'}")
    print(f"{'ffmpeg':11} {preparar_ffmpeg()[0]}")
    print(f"{'navegador':11} {buscar_edge()}")
