"""Baja de Mixkit los efectos marcados en pagina_mixkit.py (o los ids que se le den) y los deja en
MUSICA\\Edmundo\\Efectos en FLAC, con su nombre en español y sin silencio al principio ni al final.

    python bajar_mixkit.py            # los propuestos (marcados) de pagina_mixkit.py
    python bajar_mixkit.py 478 974    # solo esos
"""
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from copiar_efectos import copiar

AQUI = Path(__file__).parent

fuente = (AQUI / "pagina_mixkit.py").read_text(encoding="utf-8")
FILAS = [(int(i), n, m == "True") for i, n, m in
         re.findall(r'\((\d+), "([^"]+)", "[^"]+", \d+, (True|False)\)', fuente)]

if __name__ == "__main__":
    pedidos = {int(x) for x in sys.argv[1:]}
    elegidos = [(i, n) for i, n, m in FILAS if (i in pedidos if pedidos else m)]
    bajadas = Path(tempfile.mkdtemp(prefix="mixkit_"))          # carpeta nueva y vacía solo para lo bajado
    total = 0
    for i, nombre in elegidos:
        wav = bajadas / f"{i}.wav"
        url = f"https://assets.mixkit.co/active_storage/sfx/{i}/{i}.wav"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                                        timeout=60) as r:
                wav.write_bytes(r.read())
        except Exception as e:
            print("NO SE PUDO BAJAR", i, nombre, e)
            continue
        total += wav.stat().st_size
        s = copiar(wav, nombre, umbral=-70)       # ya vienen cortados: solo el silencio digital
        if s:
            print(f"{s.stat().st_size / 1e6:5.2f} MB  {s.name}")
        time.sleep(0.5)                                          # sin prisas con su servidor
    print(f"Bajado: {total / 1e6:.1f} MB ({len(elegidos)} efectos) en {bajadas}")
