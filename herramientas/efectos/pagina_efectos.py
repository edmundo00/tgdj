"""Hace «Elegir efectos.html»: escuchar los efectos de la Valentino y marcar los que se quieren."""
import json
import os
import re
import struct
from pathlib import Path

RAIZ = Path(r"C:\Users\edmun\Documents\Soulseek Downloads\complete\blueflops\Valentino.Sound Effects Library")
SALIDA = Path(r"D:\Dropbox\TDJ\MUSICA\Elegir efectos.html")

# (volumen, número, nombre en español, grupo) — los propuestos (salen marcados)
PROPUESTOS = [
    (12, 22, "Silbato de policía (varios pitidos)", "📣 Silbatos"),
    (24, 62, "Silbato de policía inglés 1", "📣 Silbatos"),
    (24, 63, "Silbato de policía inglés 2", "📣 Silbatos"),
    (23, 11, "Silbato de árbitro con público", "📣 Silbatos"),
    (12, 25, "Silbato de émbolo (fiuuu) 1", "📣 Silbatos"),
    (12, 90, "Silbato whoopie 1", "📣 Silbatos"),
    (2, 38, "Aplausos 1", "👏 Aplausos"),
    (2, 39, "Aplausos 2", "👏 Aplausos"),
    (2, 42, "Aplausos 3", "👏 Aplausos"),
    (2, 45, "Aplausos 4", "👏 Aplausos"),
    (23, 15, "Ovación con gritos", "👏 Aplausos"),
    (19, 27, "Ovación de estadio", "👏 Aplausos"),
    (12, 73, "Campanilla de mostrador (atención)", "🔔 Avisos"),
    (12, 10, "Campana suiza, 3 toques", "🔔 Avisos"),
    (12, 76, "Campana de barco, un toque", "🔔 Avisos"),
    (12, 66, "Triángulo, un golpe", "🔔 Avisos"),
    (1, 87, "Timbre de puerta din-don", "🔔 Avisos"),
    (24, 67, "Campanas de iglesia", "⛪ Campanas"),
    (1, 90, "Campanas de iglesia - las 12", "⛪ Campanas"),
    (12, 53, "Campana de ring de boxeo, 3 toques (última tanda)", "🥊 Última tanda"),
    (10, 24, "Corneta - toque de diana", "🎺 Cornetas"),
    (10, 27, "Corneta - toque de silencio", "🎺 Cornetas"),
    (21, 30, "Redoble de caja largo con platillo", "🥁 Redobles"),
    (21, 28, "Redoble de caja corto con platillo", "🥁 Redobles"),
    (17, 7, "Timbal con crescendo", "🥁 Redobles"),
    (21, 26, "Golpe de platillo", "🥁 Redobles"),
    (17, 18, "Gong mediano", "🎐 Gong"),
    (2, 26, "Gong grande", "🎐 Gong"),
    (24, 59, "Corcho de cava 1", "🥂 Fiesta"),
    (24, 60, "Corcho de cava 2", "🥂 Fiesta"),
    (1, 7, "Copas brindando", "🥂 Fiesta"),
    (12, 20, "Matasuegras de Nochevieja", "🥂 Fiesta"),
    (25, 34, "Cohete que silba y explota", "🥂 Fiesta"),
    (24, 52, "Reloj de cuco - las 12", "🕛 Reloj"),
    (8, 4, "Reloj de pared dando la hora", "🕛 Reloj"),
    (21, 74, "Castañuelas", "💃 Baile"),
    (27, 7, "Claqué, un paso", "💃 Baile"),
    (27, 52, "Risas enlatadas 1", "😄 Humor"),
    (27, 56, "Risas enlatadas 2", "😄 Humor"),
    (27, 59, "Risas enlatadas 3", "😄 Humor"),
    (9, 10, "Beso", "😄 Humor"),
    (24, 74, "Carillón de viento de cristal", "🎐 Suave"),
]

# además, sin marcar, para elegir: todo lo de estos tipos (por el nombre del archivo)
OTROS = [
    ("📣 Silbatos", r"whistle(?!.*(train|boat|ship|liner|tug|ferry|factory|riverboat|tea|wind|locomotive|rocket))"),
    ("👏 Aplausos", r"applau|cheer|ovation"),
    ("⛪ Campanas", r"church"),
    ("🎐 Gong", r"gong"),
    ("💃 Baile", r"tap dance|castanet"),
    ("🔔 Avisos", r"\bbells?\b|chime|triangle|doorbell|door bell"),
    ("🥁 Redobles", r"\broll\b|cymbal|rim shot"),
    ("🎺 Cornetas", r"bugle"),
    ("🥂 Fiesta", r"cork|toast|noisemaker|firework.*(rocket|explosion)|party"),
    ("🕛 Reloj", r"clock"),
    ("😄 Humor", r"laugh|kiss|slide whistle|whoopie"),
]
FUERA = r"screw|dice|automobile|bowling|billiard|lujon|templeblock|bongo|machine|gun|truck|jet|train|siren|alarm|oxygen|microwave|seat belt|fire truck|buoy|crossing|cow|ice cream|sleigh|scream|chimpanzee|moan|hi-hat|tom|tabla|tympani - (walking|ram|suspense|asian)"


def duracion_flac(ruta):
    try:
        with open(ruta, "rb") as f:
            if f.read(4) != b"fLaC":
                return None
            f.read(4)
            d = f.read(34)
        x = int.from_bytes(d[10:18], "big")
        frecuencia = x >> 44
        muestras = x & ((1 << 36) - 1)
        return muestras / frecuencia if frecuencia else None
    except OSError:
        return None


import subprocess
from concurrent.futures import ThreadPoolExecutor


def suena(ruta):
    """Segundos hasta donde hay sonido (sin el silencio del final que traen muchos)."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(ruta), "-af", "silencedetect=n=-50dB:d=0.5", "-f", "null", "-"],
                         capture_output=True, text=True, errors="replace").stderr
    inicios = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", out)]
    finales = re.findall(r"silence_end: ([\d.]+)", out)
    total = duracion_flac(ruta)
    if inicios and total and (len(finales) < len(inicios) or abs(float(finales[-1]) - total) < 0.1):
        return inicios[-1]
    return total


archivos = {}
for carpeta in RAIZ.iterdir():
    m = re.search(r"VAL (\d+)", carpeta.name)
    if not m or not carpeta.is_dir():
        continue
    vol = int(m.group(1))
    for a in carpeta.rglob("*.flac"):
        n = re.match(r"\s*(\d+)\s*\.", a.stem)
        if n:
            archivos[(vol, int(n.group(1)))] = a

filas, vistos = [], set()
for vol, num, nombre, grupo in PROPUESTOS:
    a = archivos.get((vol, num))
    if a is None:
        print("NO ESTÁ", vol, num, nombre)
        continue
    vistos.add((vol, num))
    filas.append(dict(id=f"VAL{vol:02d}-{num:02d}", nombre=nombre, grupo=grupo, original=re.sub(r"^\s*\d+\s*\.\s*", "", a.stem),
                      url=a.as_uri(), ruta=str(a), seg=duracion_flac(a), mb=round(a.stat().st_size / 1e6, 1), marcado=True))
for (vol, num), a in sorted(archivos.items()):
    if (vol, num) in vistos:
        continue
    texto = a.stem.lower()
    if re.search(FUERA, texto):
        continue
    grupo = next((g for g, patron in OTROS if re.search(patron, texto)), None)
    if not grupo:
        continue
    filas.append(dict(id=f"VAL{vol:02d}-{num:02d}", nombre="", grupo=grupo, original=re.sub(r"^\s*\d+\s*\.\s*", "", a.stem),
                      url=a.as_uri(), ruta=str(a), seg=duracion_flac(a), mb=round(a.stat().st_size / 1e6, 1), marcado=False))

with ThreadPoolExecutor(8) as hilos:
    for f, seg in zip(filas, hilos.map(lambda f: suena(Path(f["ruta"])), filas)):
        f["suena"] = round(seg, 1) if seg else None
for f in filas:
    del f["ruta"]
orden = [g for _, _, _, g in PROPUESTOS] + [g for g, _ in OTROS]
grupos = list(dict.fromkeys(orden))
filas.sort(key=lambda f: (grupos.index(f["grupo"]), not f["marcado"]))
print(len(filas), "efectos;", sum(f["marcado"] for f in filas), "marcados")

html = Path(__file__).with_name("plantilla_efectos.html").read_text(encoding="utf-8")
html = html.replace("__DATOS__", json.dumps(filas, ensure_ascii=False)).replace("__GRUPOS__", json.dumps(grupos, ensure_ascii=False))
SALIDA.write_text(html, encoding="utf-8")
print(SALIDA.as_uri())
