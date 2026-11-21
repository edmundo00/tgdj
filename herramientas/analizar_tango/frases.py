"""¿Respira la orquesta al llegar cada frase? (20-11-2026, reel «Bailar la frase»)

En «Vieja calesita» (Típica Victor, 1929) la frase llega en el 1 de cada 8 compases y, justo después, bandoneones y
contrabajo se callan en los tiempos 2-3-4. Esta herramienta mide si pasa lo mismo en otra canción.

Para cada compás: energía de los tiempos que siguen al de llegada (el 1 o, en 4/4, el 3: ritmo.py puede poner el 1
medio compás corrido, y en «Vieja calesita» la frase llega en el 3 y el hueco cruza la raya; en vals, 2-3) en la pista separada de bandoneones y
en la de contrabajo, comparada con los compases vecinos (±3, sin él) → «bajón» en dB (negativo = se calla).
Luego prueba frases de 4, 8 y 16 compases con todos los desfases posibles (la canción puede empezar con una
introducción o con anacrusa) y se queda con el mejor. Para saber si es de verdad o casualidad, hace lo mismo con los
compases barajados (2000 veces): «azar» = lo que sale sin frases; p = cuántas veces el azar lo hace igual de bien.

Uso (python del venv analizar_tango):
  frases.py "<carpeta _ritmo\\canción>"          → frases.txt en esa carpeta
  frases.py --todas                              → todas las que tienen pistas separadas + _ritmo\\_FRASES.txt
Necesita ritmo.json (ritmo.py) y _datos\\<canción>\\pistas\\bandoneones.flac + contrabajo.flac (analizar_tango.py).
"""
import os, sys, json, glob
import numpy as np

RITMO = r"D:\Dropbox\TDJ\Analisis tangos\_ritmo"
DATOS = r"D:\Dropbox\TDJ\Analisis tangos\_datos"
PISTAS = ("bandoneones", "contrabajo")
VECINOS = 3
N_AZAR = 2000


def energia_por_compas(pista, pulsos, llega=1):
    """{compás: (dB del tiempo de llegada, dB de los tiempos que le siguen)} con la energía media de cada tiempo.
    llega = tiempo del compás en que llega la frase (1, o 3 en 4/4: el hueco puede cruzar la raya del compás).
    Los «tiempos que le siguen» son los n−1 siguientes (n = tiempos por compás), sean del mismo compás o del otro."""
    import librosa
    y, sr = librosa.load(pista, sr=22050, mono=True)
    r = librosa.feature.rms(y=y, frame_length=1024, hop_length=220)[0] ** 2
    t = np.arange(len(r)) * 220 / sr
    e = []
    for p, q in zip(pulsos, pulsos[1:]):
        m = (t >= p["seg"]) & (t < q["seg"])
        e.append(float(r[m].mean()) if m.any() else np.nan)
    n = max(p["tiempo"] for p in pulsos)
    out = {}
    for i, p in enumerate(pulsos[:len(e)]):
        if p["tiempo"] == llega and i + n - 1 < len(e):
            resto = e[i + 1:i + n]
            if not np.isnan(e[i]) and not any(np.isnan(resto)):
                out[p["compas"]] = (10 * np.log10(e[i] + 1e-12), 10 * np.log10(np.mean(resto) + 1e-12))
    return out


def bajones(e):
    """bajón de cada compás en «lo que sigue al 1» respecto a sus vecinos (dB)."""
    cs = sorted(e)
    b = {}
    for c in cs:
        vec = [e[x][1] for x in range(c - VECINOS, c + VECINOS + 1) if x != c and x in e]
        if len(vec) >= 3:
            b[c] = e[c][1] - float(np.median(vec))
    return b


def mejor(cs, vals, periodo):
    """mejor desfase: el que tiene el bajón mediano más negativo. Devuelve (bajón, desfase, compases)."""
    res = []
    for o in range(periodo):
        sel = [v for c, v in zip(cs, vals) if c % periodo == o]
        if len(sel) >= 3:
            res.append((float(np.median(sel)), o, [c for c in cs if c % periodo == o]))
    return min(res) if res else (0.0, 0, [])


def analizar(carpeta, rng):
    nombre = os.path.basename(carpeta.rstrip("\\/"))
    rj = os.path.join(carpeta, "ritmo.json")
    pis = os.path.join(DATOS, nombre, "pistas")
    if not os.path.exists(rj) or not all(os.path.exists(os.path.join(pis, k + ".flac")) for k in PISTAS):
        return None
    d = json.load(open(rj, encoding="utf-8"))
    pulsos = d["pulsos"]
    if max(p["tiempo"] for p in pulsos) == 2:
        # en 2/4 se juntan los compases de dos en dos (= un compás de 4 tiempos, como en las demás); se prueban las
        # dos maneras de emparejarlos y se queda con la que da más bajón
        res = []
        for par in (0, 1):
            pp = [dict(p, compas=(p["compas"] - 1 + par) // 2 + 1, tiempo=((p["compas"] - 1 + par) % 2) * 2 + p["tiempo"])
                  for p in pulsos]
            x = medir(pp, pis, d, nombre, rng)
            x["compas"] = f"2/4 juntado de 2 en 2 ({'empezando en el compás 1' if par == 0 else 'desplazado un compás'})"
            res.append(x)
        return min(res, key=lambda x: x[8]["bajon"])
    return medir(pulsos, pis, d, nombre, rng)


def medir(pulsos, pis, d, nombre, rng):
    """prueba la llegada en el 1 y (en 4/4) en el 3 y se queda con la que da más bajón."""
    llegadas = (1, 3) if max(p["tiempo"] for p in pulsos) == 4 else (1,)
    res = [medir_llegada(pulsos, pis, d, nombre, rng, a) for a in llegadas]
    return min(res, key=lambda x: x[8]["bajon"])


def medir_llegada(pulsos, pis, d, nombre, rng, llega):
    E = {k: energia_por_compas(os.path.join(pis, k + ".flac"), pulsos, llega) for k in PISTAS}
    B = {k: bajones(E[k]) for k in PISTAS}
    # juntos: media de las dos pistas (los compases que tengan las dos)
    comunes = sorted(set(B["bandoneones"]) & set(B["contrabajo"]))
    B["los dos"] = {c: (B["bandoneones"][c] + B["contrabajo"][c]) / 2 for c in comunes}
    res = {"cancion": nombre, "compas": d["meta"].get("compas"), "bpm": d["meta"].get("bpm"), "n": len(comunes), "llega": llega}
    for periodo in (8, 4, 16):
        cs = comunes
        v = np.array([B["los dos"][c] for c in cs])
        obs, o, sel = mejor(cs, v, periodo)
        azar = []
        for _ in range(N_AZAR):
            azar.append(mejor(cs, rng.permutation(v), periodo)[0])
        azar = np.array(azar)
        p = float((azar <= obs).mean())
        por_pista = {}
        for k in PISTAS:
            vals = [B[k][c] for c in sel if c in B[k]]
            por_pista[k] = (float(np.median(vals)), float(np.mean(np.array(vals) < -3))) if vals else (0.0, 0.0)
        # el 1 de esos compases: ¿se toca? (dB del 1 respecto a los vecinos, bandoneones)
        e1 = E["bandoneones"]
        uno = [e1[c][0] - np.median([e1[x][0] for x in range(c - VECINOS, c + VECINOS + 1) if x != c and x in e1])
               for c in sel if c in e1]
        res[periodo] = dict(bajon=round(obs, 1), desfase=o, compases=sel, p=round(p, 4),
                            azar=round(float(np.median(azar)), 1),
                            por_pista={k: (round(a, 1), round(b * 100)) for k, (a, b) in por_pista.items()},
                            uno=round(float(np.median(uno)), 1) if uno else 0.0,
                            cada=[round(B["los dos"][c], 1) for c in sel])
        if periodo == 8:   # la mitad de la frase (4 compases después): si también baja, las frases son de 4
            mit = [B["los dos"][c] for c in cs if c % 8 == (o + 4) % 8]
            res[8]["mitad"] = round(float(np.median(mit)), 1) if mit else 0.0
    # la MEZCLA entera (todo el disco, con la voz y la melodía): ¿se nota también el hueco? (20-11-2026)
    # el audio original con el que ritmo.py sacó los tiempos; si no está, la mezcla.flac de las pistas
    mz = d["meta"].get("audio") or ""
    if not os.path.exists(mz):
        mz = os.path.join(pis, "mezcla.flac")
    if os.path.exists(mz):
        Bm = bajones(energia_por_compas(mz, pulsos, llega))
        res["mezcla"] = {pe: estadistica(Bm, pe, rng) for pe in (8, 4)}
        res["mezcla"]["mismo_sitio"] = res["mezcla"][8]["desfase"] == res[8]["desfase"]
    return res


def estadistica(B1, periodo, rng):
    """mejor desfase de una serie de bajones y su p contra los compases barajados."""
    cs = sorted(B1)
    v = np.array([B1[c] for c in cs])
    obs, o, sel = mejor(cs, v, periodo)
    azar = np.array([mejor(cs, rng.permutation(v), periodo)[0] for _ in range(N_AZAR)])
    mit = [B1[c] for c in cs if c % 8 == (o + 4) % 8]
    return dict(bajon=round(obs, 1), desfase=o, compases=sel, p=round(float((azar <= obs).mean()), 4),
                azar=round(float(np.median(azar)), 1), mitad=round(float(np.median(mit)), 1) if mit else 0.0,
                cada=[round(B1[c], 1) for c in sel])


def veredicto(r):
    x = r[8]
    if x["p"] < 0.01 and x["bajon"] <= -3:
        return "sí, cada 4 (también en la mitad)" if x["mitad"] <= -3 else "SÍ, cada 8"
    if r[4]["p"] < 0.01 and r[4]["bajon"] <= -3:
        return "sí, cada 4 (también en la mitad)"
    if x["p"] < 0.05 and x["bajon"] <= -2:
        return "flojo"
    return "no"


def texto(r):
    l = [f"{r['cancion']}  ·  {r['compas']}  ·  {r['bpm']} bpm  ·  {r['n']} compases  →  {veredicto(r)}"
         f"  (la frase llega en el {r.get('llega', 1)}; hueco = los {3 if '4' in str(r['compas']) or '2/4' in str(r['compas']) else 2} tiempos siguientes)"]
    for periodo in (8, 4, 16):
        x = r[periodo]
        l.append(f"  cada {periodo:2d}: bajón {x['bajon']:+5.1f} dB (azar {x['azar']:+.1f}, p={x['p']:.3f})  "
                 f"en los compases {', '.join(map(str, x['compases'][:2]))}, … · bandoneones {x['por_pista']['bandoneones'][0]:+.1f} dB "
                 f"({x['por_pista']['bandoneones'][1]} % bajan >3 dB) · contrabajo {x['por_pista']['contrabajo'][0]:+.1f} dB "
                 f"({x['por_pista']['contrabajo'][1]} %) · el tiempo de llegada: {x['uno']:+.1f} dB")
    l.append(f"  en la mitad de la frase (4 compases después): {r[8]['mitad']:+.1f} dB")
    l.append("  cada frase (cada 8, los dos): " + " ".join(f"{v:+.0f}" for v in r[8]["cada"]))
    if "mezcla" in r:
        m = r["mezcla"][8]
        l.append(f"  MEZCLA ENTERA → {veredicto(r['mezcla'])}: cada 8 bajón {m['bajon']:+.1f} dB (azar {m['azar']:+.1f}, "
                 f"p={m['p']:.3f}) en los compases {', '.join(map(str, m['compases'][:2]))}, … "
                 f"({'el mismo sitio' if r['mezcla']['mismo_sitio'] else 'OTRO sitio'} que bandoneones+contrabajo) · "
                 f"mitad {m['mitad']:+.1f} dB")
        l.append("  cada frase (mezcla): " + " ".join(f"{v:+.0f}" for v in m["cada"]))
    return "\n".join(l)


def main():
    rng = np.random.default_rng(1)
    if len(sys.argv) > 1 and sys.argv[1] == "--todas":
        res = []
        for c in sorted(glob.glob(os.path.join(RITMO, "*", ""))):
            nombre = os.path.basename(c.rstrip("\\/"))
            if not os.path.exists(os.path.join(DATOS, nombre, "pistas", "bandoneones.flac")):
                continue
            print("…", nombre, flush=True)
            r = analizar(c, rng)
            if r:
                res.append(r)
                open(os.path.join(c, "frases.txt"), "w", encoding="utf-8").write(texto(r) + "\n")
        res.sort(key=lambda r: r[8]["bajon"])
        cab = ("¿RESPIRA LA ORQUESTA AL LLEGAR CADA FRASE? (frases.py)\n"
               "bajón = cuánto bajan bandoneones + contrabajo en los tiempos que siguen al 1 del compás de llegada,\n"
               "respecto a los compases vecinos. azar = lo mismo con los compases barajados. p < 0,01 = no es casualidad.\n\n")
        cuenta, cm = {}, {}
        for r in res:
            cuenta[veredicto(r)] = cuenta.get(veredicto(r), 0) + 1
            if "mezcla" in r:
                cm[veredicto(r["mezcla"])] = cm.get(veredicto(r["mezcla"]), 0) + 1
        resumen = ("RESUMEN bandoneones + contrabajo: " + " · ".join(f"{k}: {v}" for k, v in cuenta.items())
                   + f"  (de {len(res)})\nRESUMEN mezcla entera:           " + " · ".join(f"{k}: {v}" for k, v in cm.items()) + "\n\n")
        sal = cab + resumen + "\n\n".join(texto(r) for r in res) + "\n"
        open(os.path.join(RITMO, "_FRASES.txt"), "w", encoding="utf-8").write(sal)
        json.dump(res, open(os.path.join(RITMO, "_FRASES.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(sal)
    else:
        r = analizar(sys.argv[1], rng)
        if not r:
            raise SystemExit("falta ritmo.json o las pistas separadas (bandoneones/contrabajo)")
        open(os.path.join(sys.argv[1], "frases.txt"), "w", encoding="utf-8").write(texto(r) + "\n")
        print(texto(r))


if __name__ == "__main__":
    main()
