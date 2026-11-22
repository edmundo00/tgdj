"""Copia los efectos elegidos (texto «EFECTOS / VAL12-22 = nombre …») a MUSICA\\Edmundo\\Efectos, en FLAC, con su
nombre en español y SIN el silencio del principio y del final (los de la Valentino traen ~11 s al final).

    python copiar_efectos.py lista.txt
"""
import json
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).parent
DESTINO = Path(r"D:\Dropbox\TDJ\MUSICA\Edmundo\Efectos")
RAIZ = Path(r"C:\Users\edmun\Documents\Soulseek Downloads\complete\blueflops\Valentino.Sound Effects Library")
# quita el silencio del principio y (dándole la vuelta) el del final; deja 0,15 s de cola para que no corte en seco
SIN_SILENCIO = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,"
                "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,areverse")


def archivos_valentino():
    d = {}
    for carpeta in RAIZ.iterdir():
        m = re.search(r"VAL (\d+)", carpeta.name)
        if m and carpeta.is_dir():
            for a in carpeta.rglob("*.flac"):
                n = re.match(r"\s*(\d+)\s*\.", a.stem)
                if n:
                    d[f"VAL{int(m.group(1)):02d}-{int(n.group(1)):02d}"] = a
    return d


def limpio(nombre):
    return re.sub(r'[<>:"/\\|?*]', "-", nombre).strip(" .")


def copiar(origen, nombre, umbral=-50):
    """umbral: dB por debajo de los cuales es «silencio» (Mixkit ya viene cortado: -70, para no comerse colas suaves)."""
    DESTINO.mkdir(parents=True, exist_ok=True)
    salida = DESTINO / f"{limpio(nombre)}.flac"
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(origen), "-af", SIN_SILENCIO.replace("-50dB", f"{umbral}dB"),
                        "-c:a", "flac", "-compression_level", "8", "-metadata", f"title={nombre}",
                        "-metadata", "genre=Efecto", str(salida)], capture_output=True, text=True)
    if r.returncode:
        print("FALLA", nombre, r.stderr[-300:])
        return None
    return salida


if __name__ == "__main__":
    lineas = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    vale = archivos_valentino()
    for linea in lineas:
        m = re.match(r"\s*(VAL\d+-\d+)\s*=\s*(.+)", linea)
        if not m:
            continue
        origen = vale.get(m.group(1))
        if origen is None:
            print("NO ESTÁ", m.group(1))
            continue
        s = copiar(origen, m.group(2).strip())
        if s:
            print(f"{s.stat().st_size / 1e6:5.2f} MB  {s.name}")
