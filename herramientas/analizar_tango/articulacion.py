"""Cortado o ligado (staccato / legato): cuánto baja el sonido ENTRE golpe y golpe.

Por cada pulso se mira la envolvente de la mezcla (ventanas de 10 ms):
  silencio  = parte del pulso por debajo del 25 % de su golpe (pico del primer tercio del pulso).
              Staccato (D'Arienzo 1935): ~30 % · legato (Caló 1942): ~2 %.
  valle     = sonido que queda al final del pulso (percentil 10 de los 2/3 finales) / pico.
              Bajo = cortado, alto = ligado.

Se escribe en la carpeta del análisis:
  articulacion.txt   resumen y compás a compás
  articulacion.csv   compás, segundo, silencio %, valle

Uso suelto (sobre un análisis ya hecho, sin repetirlo):
  python articulacion.py "D:\\Dropbox\\TDJ\\Analisis tangos\\_datos\\<canción>"  [desde_s hasta_s]
"""
import os, sys, csv
import numpy as np

UMBRAL = 0.25     # «casi en silencio» = por debajo del 25 % del golpe
PASO = 0.010      # 10 ms


def envolvente(x, sr):
    """RMS en ventanas de 10 ms (100 valores por segundo)."""
    h = int(sr * PASO)
    n = len(x) // h
    return np.sqrt((np.asarray(x[:n * h], dtype=np.float64).reshape(n, h) ** 2).mean(1))


def por_pulso(env, beats):
    """[(inicio, silencio 0-1, valle 0-1)] para cada pulso."""
    fps = 1 / PASO
    out = []
    for a, b in zip(beats[:-1], beats[1:]):
        seg = env[int(a * fps):int(b * fps)]
        if len(seg) < 5:
            continue
        pico = seg[:max(1, len(seg) // 3)].max() + 1e-12
        out.append((float(a), float((seg < UMBRAL * pico).mean()), float(np.percentile(seg[len(seg) // 3:], 10) / pico)))
    return out


def tramo(env, beats, desde=0.0, hasta=1e9):
    """(silencio medio %, valle mediano, nº de pulsos) entre dos segundos."""
    p = [(s, v) for a, s, v in por_pulso(env, beats) if a >= desde and a < hasta]
    if not p:
        return 0.0, 0.0, 0
    s, v = zip(*p)
    return 100 * float(np.mean(s)), float(np.median(v)), len(p)


def palabra(sil):
    return "CORTADO (staccato)" if sil >= 20 else "LIGADO (legato)" if sil <= 6 else "a medias"


def guardar(out, mezcla, sr, beats, compas):
    env = envolvente(mezcla, sr)
    pp = por_pulso(env, list(beats))
    filas = {}
    for (a, s, v), c in zip(pp, compas):
        f = filas.setdefault(int(c), dict(compas=int(c), seg=round(a, 3), s=[], v=[]))
        f["s"].append(s); f["v"].append(v)
    tab = [dict(compas=f["compas"], seg=f["seg"], silencio=round(100 * np.mean(f["s"])), valle=round(float(np.median(f["v"])), 2))
           for f in filas.values()]
    with open(os.path.join(out, "articulacion.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["compas", "seg", "silencio", "valle"], delimiter=";")
        w.writeheader(); w.writerows(tab)
    sil, val, n = tramo(env, list(beats))
    with open(os.path.join(out, "articulacion.txt"), "w", encoding="utf-8") as fh:
        fh.write("CORTADO O LIGADO (staccato / legato) · cuánto baja el sonido entre golpe y golpe\n")
        fh.write(f"silencio = parte de cada pulso por debajo del {int(UMBRAL * 100)} % de su golpe (mezcla entera)\n")
        fh.write("referencias: D'Arienzo 9 de Julio 1935 (primeros 25 s) 31 % · Caló Al compás del corazón 1942 2 %\n\n")
        fh.write(f"Tango entero: silencio {sil:.0f} % · valle {val:.2f} · {n} pulsos → {palabra(sil)}\n\n")
        fh.write("compás   seg.   silencio  valle\n")
        for t in tab:
            barra = "█" * int(round(t["silencio"] / 5))
            fh.write(f"{t['compas']:5d} {t['seg']:7.2f} {t['silencio']:6d} %  {t['valle']:5.2f}  {barra}\n")
    return sil


def _leer_carpeta(d):
    import soundfile as sf
    pul = list(csv.DictReader(open(os.path.join(d, "pulsos.csv"), encoding="utf-8-sig"), delimiter=";"))
    beats = [float(r["seg"]) for r in pul]
    compas = [int(r["compas"]) for r in pul]
    f = os.path.join(d, "pistas", "mezcla.flac")
    if not os.path.exists(f):
        f = os.path.join(d, "escuchar", "mezcla.ogg")
    x, sr = sf.read(f)
    if x.ndim > 1:
        x = x.mean(1)
    return x, sr, beats, compas


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    d = sys.argv[1]
    x, sr, beats, compas = _leer_carpeta(d)
    if len(sys.argv) > 3:
        s, v, n = tramo(envolvente(x, sr), beats, float(sys.argv[2]), float(sys.argv[3]))
        print(f"{sys.argv[2]}-{sys.argv[3]} s: silencio {s:.0f} % · valle {v:.2f} · {n} pulsos → {palabra(s)}")
    else:
        s = guardar(d, x, sr, beats, compas)
        print(f"silencio {s:.0f} % → {palabra(s)} · {os.path.join(d, 'articulacion.txt')}")
