"""
Fase 1 de PLAN_ORDENAR_MUSICA.md: huella de sonido (Shazam propio, src/diapos/huellas.py) de TODA la música.

    python huellas_todas.py [--procesos 5] [--limite N] [--coleccion Edmundo]

- Recorre TDJ\\MUSICA (la carpeta Edmundo primero) y guarda la huella de cada archivo en
  %LOCALAPPDATA%\\TangoTags\\huellas.sqlite (fuera de Dropbox: es caché, ~3,5 GB, se puede rehacer).
- Se corta y sigue: solo hace lo nuevo o cambiado (mismo tamaño y fecha = ya hecho).
- No abre los archivos «solo en la nube» de Dropbox (no fuerza descargas). No toca ningún archivo de música.
- Prioridad baja y sin ventanas. Estado en TDJ\\MUSICA\\..\\PYTHON\\tgdj\\herramientas\\ordenar_musica\\_HUELLAS_ESTADO.txt
"""
import argparse
import ctypes
import multiprocessing as mp
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import zlib

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
TGDJ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, os.path.join(TGDJ, "src", "diapos"))
import huellas  # noqa: E402

TDJ = os.path.dirname(os.path.dirname(TGDJ))
MUSICA = os.path.join(TDJ, "MUSICA")
# Extractos de El Recodo ya bajados (data/db.csv, columna audio30 = …/mediatheque/30x/<n>.mp3)
RECODO = os.path.join(TDJ, "tangolinkdatabase", "MP3", "_TANGO", "mediatheque")
PREFIJO_RECODO = "@recodo" + os.sep
# Fuera de Dropbox (2 GB) y fuera de AppData: lo que Claude escribe en AppData lo esconde la app de Claude en su
# carpeta propia (Packages\Claude_…\LocalCache) y los programas de Edmundo no lo ven (pasó el 20-11-2026).
BD = os.path.join(os.environ["USERPROFILE"], "TangoTags_datos", "huellas.sqlite")
os.makedirs(os.path.dirname(BD), exist_ok=True)
ESTADO = os.path.join(AQUI, "_HUELLAS_ESTADO.txt")
EXTENSIONES = {".flac", ".mp3", ".m4a", ".wav", ".aif", ".aiff", ".ogg", ".opus", ".wma", ".ape", ".wv"}
_EN_NUBE = 0x400000 | 0x1000      # Dropbox «solo en la nube»
BAJA = 0x00004000                 # BELOW_NORMAL_PRIORITY_CLASS
SIN_VENTANA = 0x08000000          # CREATE_NO_WINDOW
FFMPEG = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"


def abrir_bd():
    os.makedirs(os.path.dirname(BD), exist_ok=True)
    con = sqlite3.connect(BD, timeout=120)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS huellas (
        rel      TEXT PRIMARY KEY,   -- ruta dentro de TDJ\\MUSICA (igual en todos los PC)
        bytes    INTEGER, mtime INTEGER,
        duracion REAL,               -- segundos
        n        INTEGER,            -- nº de códigos
        codigos  BLOB,               -- zlib( uint32 código[n] + uint16 columna[n] )
        error    TEXT DEFAULT '',
        hecho    REAL)""")
    return con


def empaquetar(huella):
    if not huella:
        return b""
    a = np.array(huella, dtype=np.int64)
    a = a[a[:, 1] < 65536]
    return zlib.compress(a[:, 0].astype(np.uint32).tobytes() + a[:, 1].astype(np.uint16).tobytes(), 6)


def desempaquetar(blob, n):
    """(códigos uint32, columnas uint16) de una fila de la base."""
    if not blob:
        return np.zeros(0, np.uint32), np.zeros(0, np.uint16)
    b = zlib.decompress(blob)
    n = len(b) // 6
    return np.frombuffer(b[:4 * n], np.uint32), np.frombuffer(b[4 * n:], np.uint16)


def ruta_de(rel):
    if rel.startswith(PREFIJO_RECODO):
        return os.path.join(RECODO, rel[len(PREFIJO_RECODO):])
    return os.path.join(MUSICA, rel)


def recorrer_recodo():
    """Extractos largos de El Recodo (carpetas 30x): [(rel, bytes, mtime)]."""
    lista = []
    for d in sorted(os.listdir(RECODO)):
        if not (d.startswith("30") and os.path.isdir(os.path.join(RECODO, d))):
            continue
        for e in os.scandir(os.path.join(RECODO, d)):
            if e.name.lower().endswith(".mp3"):
                st = e.stat()
                lista.append((PREFIJO_RECODO + os.path.join(d, e.name), st.st_size, int(st.st_mtime)))
    return lista


def recorrer():
    """[(rel, bytes, mtime)] de todo TDJ\\MUSICA (Edmundo primero) y nº de archivos en la nube."""
    lista, nube = [], 0
    pila = [MUSICA]
    while pila:
        carpeta = pila.pop()
        try:
            entradas = list(os.scandir(carpeta))
        except OSError:
            continue
        for e in entradas:
            # en Windows, e.stat() sale del propio listado de la carpeta: no abre cada archivo
            if e.is_dir(follow_symlinks=False):
                pila.append(e.path)
                continue
            if os.path.splitext(e.name)[1].lower() not in EXTENSIONES:
                continue
            try:
                st = e.stat(follow_symlinks=False)
            except OSError:
                continue
            if getattr(st, "st_file_attributes", 0) & _EN_NUBE:
                nube += 1
                continue
            lista.append((os.path.relpath(e.path, MUSICA), st.st_size, int(st.st_mtime)))
    lista.sort(key=lambda x: (not x[0].lower().startswith("edmundo" + os.sep), x[0].lower()))
    return lista, nube


def _iniciar_trabajador():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), BAJA)
    except Exception:
        pass


def trabajar(item):
    rel, tam, mt = item
    try:
        r = subprocess.run([FFMPEG, "-v", "error", "-nostdin", "-i", ruta_de(rel), "-vn",
                            "-ac", "1", "-ar", str(huellas.FRECUENCIA), "-f", "s16le", "-"],
                           capture_output=True, creationflags=BAJA | SIN_VENTANA, timeout=600)
        m = np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768
        if len(m) < huellas.FRECUENCIA * 2:
            return rel, tam, mt, len(m) / huellas.FRECUENCIA, 0, b"", "sin audio: " + r.stderr.decode("utf8", "replace")[:200]
        h = huellas.huella_de(m)
        return rel, tam, mt, len(m) / huellas.FRECUENCIA, len(h), empaquetar(h), ""
    except Exception as e:  # noqa: BLE001
        return rel, tam, mt, 0, 0, b"", f"{type(e).__name__}: {e}"[:200]


def escribir_estado(texto):
    with open(ESTADO, "w", encoding="utf8") as f:
        f.write(texto)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procesos", type=int, default=5)
    ap.add_argument("--limite", type=int, default=0, help="solo las N primeras pendientes (para probar)")
    ap.add_argument("--coleccion", default="", help="solo esta carpeta de MUSICA")
    ap.add_argument("--recodo", action="store_true", help="solo los extractos de El Recodo (no TDJ\\MUSICA)")
    a = ap.parse_args()
    _iniciar_trabajador()

    t0 = time.time()
    lista, nube = (recorrer_recodo(), 0) if a.recodo else recorrer()
    if a.coleccion:
        lista = [x for x in lista if x[0].lower().startswith(a.coleccion.lower() + os.sep)]
    con = abrir_bd()
    hechas = {r: (b, m) for r, b, m in con.execute("SELECT rel, bytes, mtime FROM huellas")}
    pendientes = [x for x in lista if hechas.get(x[0]) != (x[1], x[2])]
    ya = len(lista) - len(pendientes)
    if a.limite:
        pendientes = pendientes[:a.limite]
    total = len(pendientes)
    print(f"{len(lista)} archivos ({nube} solo en la nube, no se abren); ya hechos {ya}; "
          f"faltan {total}  (recorrer: {time.time() - t0:.0f} s)", flush=True)

    t1, n, errores = time.time(), 0, 0
    with mp.Pool(a.procesos, initializer=_iniciar_trabajador) as pool:
        for rel, tam, mt, dur, nc, blob, err in pool.imap_unordered(trabajar, pendientes, chunksize=4):
            con.execute("INSERT OR REPLACE INTO huellas VALUES (?,?,?,?,?,?,?,?)",
                        (rel, tam, mt, dur, nc, blob, err, time.time()))
            n += 1
            errores += bool(err)
            if n % 50 == 0 or n == total:
                con.commit()
                v = n / (time.time() - t1)
                falta = (total - n) / v if v else 0
                txt = (f"Huellas de toda la música · {time.strftime('%d-%m-%Y %H:%M')}\n"
                       f"Hechas en esta tanda: {n} de {total}  ({v:.1f} por segundo)\n"
                       f"Errores: {errores}\nFalta: {falta / 60:.0f} min\n"
                       f"Base: {BD}\nSi se corta: volver a lanzar huellas_todas.py (sigue donde lo dejó).\n")
                escribir_estado(txt)
                if n % 500 == 0 or n == total:
                    print(txt.splitlines()[1], "· falta", f"{falta / 60:.0f} min", flush=True)
    con.commit()
    escribir_estado(f"TERMINADO {time.strftime('%d-%m-%Y %H:%M')}: {n} huellas nuevas, {errores} errores, "
                    f"{(time.time() - t0) / 60:.0f} min. Base: {BD}\n")
    print(f"Terminado: {n} huellas, {errores} errores, {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    mp.freeze_support()
    main()
