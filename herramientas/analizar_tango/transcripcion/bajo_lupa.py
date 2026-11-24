"""Notas del contrabajo para la lupa de la página de ritmo (fila «bajo (notas)»).

Uso (python de venvs\\analizar_tango):
    python bajo_lupa.py "<canción.flac>" [--mid notas.mid] [--ritmo "<carpeta de _ritmo>"]

- Sin --mid, transcribe la canción con YourMT3+ (transcripcion\\yourmt3.py, python de venvs\\yourmt3, ~9 min en el
  procesador) y guarda el MIDI entero en _ritmo\\<canción>\\yourmt3.mid (para no repetirlo).
- Se queda con las notas graves (por debajo de re3): es lo único que YourMT3+ acierta bien en tango
  (prueba con «El Huracán», 18-11-2026: 23 % de notas iguales a la partitura frente a 5 % al azar).
- Escribe _ritmo\\<canción>\\bajo_datos.js (window.BAJO) que la página carga sola. --ritmo si la carpeta de _ritmo
  no se llama igual que el archivo de audio.
"""
import os, sys, json, argparse, subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rutas
RAIZ = rutas.ANALISIS
PY_YOURMT3 = rutas.python_de("yourmt3")
TECHO = 50          # re3: lo que quede por debajo cuenta como bajo
NOMBRES = ["Do", "Do#", "Re", "Mib", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "Sib", "Si"]


def notas_graves(ruta_mid):
    import pretty_midi
    m = pretty_midi.PrettyMIDI(ruta_mid)
    ns = sorted((n.start, n.end, n.pitch) for i in m.instruments if not i.is_drum for n in i.notes if n.pitch < TECHO)
    out = []
    for s, e, p in ns:   # la misma nota dos veces casi a la vez (dos «instrumentos» del modelo): una sola
        if out and abs(out[-1][0] - s) < 0.03 and out[-1][2] % 12 == p % 12:
            continue
        out.append([round(s, 3), round(e, 3), int(p)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--mid", help="MIDI ya hecho con YourMT3+ (si no, se transcribe)")
    ap.add_argument("--ritmo", help="nombre de la carpeta en _ritmo (por defecto, el del archivo)")
    a = ap.parse_args()
    carpeta = os.path.join(RAIZ, "_ritmo", a.ritmo or os.path.splitext(os.path.basename(a.audio))[0])
    if not os.path.isdir(carpeta):
        sys.exit(f"No existe {carpeta}: pasa antes ritmo.py a la canción, o di la carpeta con --ritmo")
    mid = a.mid or os.path.join(carpeta, "yourmt3.mid")
    if not a.mid and not os.path.exists(mid):
        print("Transcribiendo con YourMT3+ (unos 9 min)…", flush=True)
        subprocess.run([PY_YOURMT3, "-X", "utf8", "-W", "ignore", os.path.join(AQUI, "yourmt3.py"), a.audio, mid], check=True)
    notas = notas_graves(mid)
    datos = dict(modelo="YourMT3+ (notas graves de la mezcla)", techo=TECHO, notas=notas)
    ruta = os.path.join(carpeta, "bajo_datos.js")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("window.BAJO = "); json.dump(datos, f, ensure_ascii=False); f.write(";\n")
    usadas = {}
    for _, _, p in notas:
        usadas[NOMBRES[p % 12]] = usadas.get(NOMBRES[p % 12], 0) + 1
    top = ", ".join(f"{k} {v}" for k, v in sorted(usadas.items(), key=lambda x: -x[1])[:6])
    print(f"{ruta}: {len(notas)} notas del bajo (más usadas: {top})")


if __name__ == "__main__":
    main()
