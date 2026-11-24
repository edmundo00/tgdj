"""Paso 0 del plan de entrenamiento: probar «Beat This!» tal cual viene, frente al pulso actual del programa.

Para cada tango ya analizado (carpetas con pulsos.csv y pistas/mezcla.flac):
  - coincidencia de pulsos (±70 ms) entre Beat This! y el programa
  - en qué tiempo nuestro cae el 1 de Beat This!
  - qué parte de los golpes fuertes cae en el tiempo o en la «y» de cada rejilla (±40 ms, tras quitar el desfase fijo)
Guarda los pulsos de Beat This! en beatthis_<modelo>.csv dentro de cada carpeta.

Uso: python probar_beat_this.py [modelo]   (final0 = grande, small0 = pequeño)
"""
import sys, os, csv, glob
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas
RAIZ = rutas.ANALISIS
MODELO = sys.argv[1] if len(sys.argv) > 1 else "final0"


def leer_pulsos(d):
    r = list(csv.DictReader(open(os.path.join(d, "pulsos.csv"), encoding="utf-8-sig"), delimiter=";"))
    return (np.array([float(x["seg"]) for x in r]), np.array([int(x["compas"]) for x in r]),
            np.array([int(x["tiempo"]) for x in r]))


def golpes_fuertes(d):
    r = list(csv.DictReader(open(os.path.join(d, "golpes.csv"), encoding="utf-8-sig"), delimiter=";"))
    return np.array([float(x["seg"]) for x in r if float(x["fuerza_db"]) > -8])


def coincidencia(a, b, tol=0.07):
    """F-medida entre dos listas de pulsos."""
    if len(a) == 0 or len(b) == 0:
        return 0.0
    ok_a = np.mean([np.min(np.abs(b - x)) < tol for x in a])
    ok_b = np.mean([np.min(np.abs(a - x)) < tol for x in b])
    return 2 * ok_a * ok_b / (ok_a + ok_b + 1e-9)


def encaje(rejilla, hits):
    """% de golpes en el tiempo o en la «y» (±40 ms), quitando antes el desfase fijo."""
    sub = np.sort(np.r_[rejilla, (rejilla[:-1] + rejilla[1:]) / 2])
    h = hits[(hits > sub[0]) & (hits < sub[-1])]
    j = np.clip(np.searchsorted(sub, h), 1, len(sub) - 1)
    a, c = h - sub[j - 1], h - sub[j]
    sd = np.where(np.abs(a) < np.abs(c), a, c)
    off = np.median(sd[np.abs(sd) < 0.12]) if np.any(np.abs(sd) < 0.12) else 0
    return np.mean(np.abs(sd - off) < 0.04) * 100


def main():
    from beat_this.inference import File2Beats
    f2b = File2Beats(checkpoint_path=MODELO, device="cpu", dbn=False)
    carpetas = sorted(set(os.path.dirname(p) for p in glob.glob(os.path.join(RAIZ, "*", "pulsos.csv")) +
                          glob.glob(os.path.join(RAIZ, "_datos", "*", "pulsos.csv"))))
    print(f"Modelo {MODELO} · {len(carpetas)} tangos\n")
    print(f"{'tango':42} {'pulsos/min':>14} {'pulsos iguales':>15} {'1 de BT cae en':>22} {'encaje golpes':>18}")
    print(f"{'':42} {'nuestro  BT':>14} {'':>15} {'1    2    3    4':>22} {'nuestro   BT':>18}")
    for d in carpetas:
        audio = os.path.join(d, "pistas", "mezcla.flac")
        if not os.path.exists(audio):
            continue
        b, c, t = leer_pulsos(d)
        bt, dbt = f2b(audio)
        bt, dbt = np.asarray(bt), np.asarray(dbt)
        with open(os.path.join(d, f"beatthis_{MODELO}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";"); w.writerow(["seg", "es_1"])
            for x in bt:
                w.writerow([round(float(x), 3), int(np.min(np.abs(dbt - x)) < 0.01) if len(dbt) else 0])
        bpm_n = 60 / np.median(np.diff(b)); bpm_b = 60 / np.median(np.diff(bt))
        # comparar a la misma escala (Beat This! puede contar a la mitad o al doble)
        ratio = bpm_b / bpm_n
        f = coincidencia(b, bt)
        if 1.7 < ratio < 2.3:
            f = coincidencia(b, bt[::2]); nota = " (BT al doble)"
        elif 0.4 < ratio < 0.6:
            f = coincidencia(b[::2], bt); nota = " (BT a la mitad)"
        else:
            nota = ""
        cae = {k: 0 for k in (1, 2, 3, 4)}
        for x in dbt:
            i = int(np.argmin(np.abs(b - x)))
            if abs(b[i] - x) < 0.1:
                cae[int(t[i])] += 1
        tot = max(1, sum(cae.values()))
        hits = golpes_fuertes(d)
        nombre = os.path.basename(d)[:42]
        print(f"{nombre:42} {bpm_n:7.0f} {bpm_b:6.0f} {f * 100:13.0f} %{nota}  " +
              " ".join(f"{cae[k] * 100 / tot:4.0f}" for k in (1, 2, 3, 4)) +
              f"   {encaje(b, hits):6.0f} % {encaje(bt, hits):6.0f} %")


if __name__ == "__main__":
    main()
