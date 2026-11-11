"""Banco de pruebas: mide el analizador contra lo que sabemos con certeza. Úsalo después de cada cambio.

Referencias:
  - «El flete» (reel): el segundo 16,045 de la canción es un 1.
  - «Loca» 1942 y «Loca» de Los Reyes del Tango: compases 1-8 de la partitura de Gorczynski
    (contrabajo 1 2 3 4 en c1, c2, c7, c8; piano y marcato 1 2 3 4 en c7, c8; el compás 7 empieza el Si7 marcato).
  - Todos: qué parte de los golpes fuertes cae en el tiempo o en la «y» (±40 ms).

Reutiliza las pistas ya separadas (no separa nada). No escribe resultados: solo mide.
Uso: python evaluar.py
"""
import os, sys, glob
import numpy as np, librosa

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import separar, pulso, golpes as G

RAIZ = r"D:\Dropbox\TDJ\Analisis tangos"
SR = separar.SR
LOCA = {"Juan D'arienzo - Loca 69681_rp", "Los Reyes del Tango - loca"}
PARTITURA = {"contrabajo": {1: [1, 2, 3, 4], 2: [1, 2, 3, 4], 7: [1, 2, 3, 4], 8: [1, 2, 3, 4]},
             "piano": {7: [1, 2, 3, 4], 8: [1, 2, 3, 4]},
             "bandoneones": {7: [1, 2, 3, 4], 8: [1, 2, 3, 4]}}


def carpetas():
    ds = glob.glob(os.path.join(RAIZ, "*", "pistas", "contrabajo.flac")) + \
         glob.glob(os.path.join(RAIZ, "_datos", "*", "pistas", "contrabajo.flac"))
    return sorted(os.path.dirname(os.path.dirname(p)) for p in ds)


def encaje(beats, golpes):
    hits = np.array([g["seg"] for g in golpes if g["fuerza_db"] > -8])
    sub = np.sort(np.r_[beats, (beats[:-1] + beats[1:]) / 2])
    h = hits[(hits > sub[0]) & (hits < sub[-1])]
    j = np.clip(np.searchsorted(sub, h), 1, len(sub) - 1)
    a, c = h - sub[j - 1], h - sub[j]
    sd = np.where(np.abs(a) < np.abs(c), a, c)
    return float(np.mean(np.abs(sd) < 0.04) * 100)


def partitura(golpes, P):
    """Golpes de la partitura encontrados (en su tiempo, ±1/4 de pulso)."""
    ok, tot = 0, 0
    for pista, comps in PARTITURA.items():
        for c, ts in comps.items():
            for t in ts:
                tot += 1
                ok += any(g["pista"] == pista and g["compas"] == c and g["tiempo"] == t and g["semi"] == "" for g in golpes)
    return ok, tot


def main():
    print(f"{'tango':40} {'pulso':>9} {'el 1 según':>18} {'golpes en su sitio':>19} {'referencia':>22}")
    tot_enc = []
    for d in carpetas():
        nombre = os.path.basename(d)
        pistas = separar.separar(None, os.path.join(d, "pistas"), None)
        pistas.pop("_contrabajo_aprox", None)
        pistas["mezcla"] = librosa.load(os.path.join(d, "pistas", "mezcla.flac"), sr=SR, mono=True)[0]
        P = pulso.compases(pistas["mezcla"], pistas["contrabajo"], SR)
        g, niv = G.analizar(pistas, SR, P)
        e = encaje(P["beats"], g); tot_enc.append(e)
        ref = ""
        if nombre in LOCA:
            ok, tot = partitura(g, P)
            ref = f"partitura {ok}/{tot}"
        if "El Flete" in nombre:
            i = int(np.argmin(np.abs(P["beats"] - 16.045)))
            ref = "el 1 del reel " + ("✓" if P["tiempo"][i] == 1 else f"✗ (sale tiempo {P['tiempo'][i]})")
        print(f"{nombre[:40]:40} {P.get('fuente_pulso', '?'):>9} {P.get('fuente_1', '?'):>18} {e:17.0f} %  {ref:>22}", flush=True)
    print(f"\nMedia de golpes en su sitio: {np.mean(tot_enc):.1f} %")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
