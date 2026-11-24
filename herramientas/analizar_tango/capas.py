"""Capas de un tango: ¿qué instrumento lleva el RITMO y cuál la MELODÍA, y cuánto se separan? (24-11-2026)

Usa las pistas separadas (`_datos\\<canción>\\pistas\\`) y los compases de ritmo.py (`_ritmo\\<canción>\\ritmo.json`).
Para cada pista y cada compás mide:
  - golpeado (G): cuánto sube y baja el volumen dentro del compás y cuánto de esos ataques cae en la rejilla de
    corcheas. Alto = marca el ritmo (contrabajo, piano en marcato, bandoneones en marcato).
  - sostenido (S): qué parte del compás la nota sigue sonando fuerte (sin hueco). Alto = canta (violines, voz,
    bandoneón «cantando»).
Separación del compás = la mejor pareja (una pista muy golpeada + OTRA muy sostenida, las dos sonando).
Da la nota media de la canción y el mejor trozo de 8 compases seguidos (para un reel).

Uso:  python capas.py "<carpeta _ritmo\\canción>"      → capas.txt en esa carpeta
      python capas.py --todas                          → todas las que tengan pistas; resumen en _ritmo\\_CAPAS.txt
Python del venv analizar_tango (librosa).
"""
import json, os, sys, glob
import numpy as np
import librosa

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas
TDJ = rutas.ANALISIS
PISTAS = ["contrabajo", "piano", "bandoneones", "violines", "voz"]
SR, HOP = 22050, 220          # 10 ms


def cargar(ruta):
    y, _ = librosa.load(ruta, sr=SR, mono=True)
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=HOP)[0]
    db = librosa.amplitude_to_db(rms + 1e-9, ref=1.0)
    ons = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    return db, ons


def medir(carpeta):
    rj = json.load(open(os.path.join(carpeta, "ritmo.json"), encoding="utf-8"))
    nombre = rj["meta"]["cancion"]
    pdir = os.path.join(TDJ, "_datos", nombre, "pistas")
    if not os.path.isdir(pdir):
        return None
    pulsos = [p["seg"] for p in rj["pulsos"]]
    comps = [c["seg"] for c in rj["compases"]]
    if len(comps) < 10 or len(pulsos) < 20:
        return None
    paso = float(np.median(np.diff(pulsos)))
    # rejilla de corcheas a partir de los pulsos
    rej = []
    for a, b in zip(pulsos[:-1], pulsos[1:]):
        rej += [a, (a + b) / 2]
    rej = np.array(rej)
    datos = {}
    for n in PISTAS:
        f = os.path.join(pdir, f"{n}.flac")
        if os.path.exists(f):
            datos[n] = cargar(f)
    if not datos:
        return None
    techo = {n: np.percentile(d[0], 98) for n, d in datos.items()}
    alto = max(techo.values())
    fin = [*comps[1:], comps[-1] + (comps[-1] - comps[-2])]
    filas = []
    for k, (a, b) in enumerate(zip(comps, fin)):
        i0, i1 = int(a * SR / HOP), int(b * SR / HOP)
        fila = {"compas": rj["compases"][k]["compas"], "seg": round(a, 2)}
        p90 = {n: float(np.percentile(d[0][i0:i1], 90)) for n, d in datos.items() if i1 - i0 >= 10}
        tope = max(p90.values()) if p90 else 0
        for n, (db, ons) in datos.items():
            seg = db[i0:i1]
            if len(seg) < 10:
                continue
            nivel = p90[n] - techo[n]
            # no cuenta si casi no suena: flojo para lo que suele dar esa pista, o 18 dB por debajo de la más fuerte
            # del compás (la «voz» de un tango instrumental es un resto de la separación y engañaba: 24-11-2026)
            if nivel < -22 or p90[n] < tope - 18 or techo[n] < alto - 25:
                continue
            hondo = float(np.percentile(seg, 90) - np.percentile(seg, 15))      # dB que sube y baja
            sost = float(np.mean(seg > np.percentile(seg, 90) - 8))            # parte del compás «llena»
            o = ons[i0:i1]
            t = (np.arange(i0, i1) * HOP) / SR
            cerca = np.min(np.abs(t[:, None] - rej[None, (rej >= a - 0.1) & (rej < b + 0.1)]), axis=1) < 0.045 \
                if np.any((rej >= a - 0.1) & (rej < b + 0.1)) else np.zeros(len(t), bool)
            en_rejilla = float(o[cerca].sum() / (o.sum() + 1e-9)) / max(cerca.mean(), 1e-3)   # 1 = al azar
            g = min(hondo / 20, 1.5) * min(en_rejilla / 2, 1.5)
            fila[n] = {"G": round(g, 2), "S": round(sost, 2), "nivel": round(float(nivel), 1)}
        # separación: una pista golpeada + otra sostenida
        mejor, par = 0.0, None
        for r in ("contrabajo", "piano", "bandoneones"):
            for m in ("violines", "voz", "bandoneones", "piano"):
                if r == m or r not in fila or m not in fila:
                    continue
                s = (fila[r]["G"] - fila[m]["G"]) + (fila[m]["S"] - fila[r]["S"])
                if s > mejor:
                    mejor, par = s, (r, m)
        fila["sep"] = round(mejor, 2)
        fila["par"] = par
        filas.append(fila)
    seps = np.array([f["sep"] for f in filas])
    v8 = np.convolve(seps, np.ones(8) / 8, mode="valid") if len(seps) >= 8 else seps
    k8 = int(np.argmax(v8))
    pares = {}
    for f in filas[k8:k8 + 8]:
        if f["par"]:
            pares[f["par"]] = pares.get(f["par"], 0) + 1
    resumen = {}
    for n in datos:
        gs = [f[n]["G"] for f in filas if n in f]
        ss = [f[n]["S"] for f in filas if n in f]
        resumen[n] = {"suena_%": round(100 * len(gs) / len(filas)), "G": round(float(np.median(gs)), 2) if gs else None,
                      "S": round(float(np.median(ss)), 2) if ss else None}
    # Avisos: la separación de pistas falla a veces (24-11-2026, «Pensalo bien»: el piano salió mudo y su sonido
    # fue a «violines», que quedó como un bloque plano). Pista sin un solo hueco en todo el tango = sospechosa.
    avisos = []
    for n in ("contrabajo", "piano"):
        if n in datos and techo[n] < alto - 35:
            avisos.append(f"{n} casi mudo")
    for n, d in resumen.items():
        if d["G"] is not None and d["G"] < 0.12 and d["S"] > 0.92:
            avisos.append(f"{n} plano (¿ruido o mezcla mal separada?)")
    return {"cancion": nombre, "avisos": avisos, "bpm": rj["meta"].get("bpm"), "compases": len(filas), "paso": paso,
            "sep_media": round(float(np.median(seps)), 2), "sep_top25": round(float(np.percentile(seps, 75)), 2),
            "mejor8": {"desde_compas": filas[k8]["compas"], "seg": filas[k8]["seg"], "sep": round(float(v8[k8]), 2),
                       "pareja": max(pares, key=pares.get) if pares else None},
            "pistas": resumen, "filas": filas}


def texto(r):
    L = [f"CAPAS · {r['cancion']}", "",
         "G = golpeado (marca el ritmo) · S = sostenido (canta) · de 0 a ~1,5. Medido por compás con las pistas separadas.", ""]
    L.append(f"{'pista':12} {'suena':>6} {'G':>5} {'S':>5}")
    for n, d in r["pistas"].items():
        L.append(f"{n:12} {d['suena_%']:>5}% {d['G'] if d['G'] is not None else '-':>5} {d['S'] if d['S'] is not None else '-':>5}")
    m = r["mejor8"]
    L += ["", f"Separación ritmo/melodía: media {r['sep_media']} · el 25 % mejor ≥ {r['sep_top25']}",
          f"Mejor trozo de 8 compases: desde el compás {m['desde_compas']} ({m['seg']} s), separación {m['sep']},"
          f" ritmo = {m['pareja'][0] if m['pareja'] else '?'}, melodía = {m['pareja'][1] if m['pareja'] else '?'}", "",
          ("AVISO: " + "; ".join(r["avisos"]) + " → la separación de esta canción no es fiable" if r["avisos"] else ""),
          "compás   seg    sep  pareja"]
    for f in r["filas"]:
        L.append(f"{f['compas']:>5} {f['seg']:>7} {f['sep']:>5}  {'/'.join(f['par']) if f['par'] else ''}")
    return "\n".join(L) + "\n"


def guardar(carpeta, r):
    """capas.txt (para leer) + capas.json (compás a compás, para dibujar)."""
    open(os.path.join(carpeta, "capas.txt"), "w", encoding="utf-8").write(texto(r))
    json.dump(r, open(os.path.join(carpeta, "capas.json"), "w", encoding="utf-8"), ensure_ascii=False)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--todas":
        res = []
        for c in sorted(glob.glob(os.path.join(TDJ, "_ritmo", "*", "ritmo.json"))):
            carpeta = os.path.dirname(c)
            try:
                r = medir(carpeta)
            except Exception as e:
                print("FALLA", carpeta, e)
                continue
            if not r:
                continue
            guardar(carpeta, r)
            res.append(r)
            print(f"{r['sep_media']:5} {r['mejor8']['sep']:5}  {r['cancion']}", flush=True)
        res.sort(key=lambda r: (bool(r["avisos"]), -r["sep_media"]))   # las dudosas, al final
        L = ["CAPAS · todas las canciones con pistas separadas (de más a menos separación ritmo/melodía)", "",
             "media = separación típica del tango · mejor8 = su mejor trozo de 8 compases · pistas: G/S (golpeado/sostenido)",
             "⚠ = pistas mal separadas (pista muda o plana): no fiarse; van al final.", ""]
        for r in res:
            m = r["mejor8"]
            ps = " · ".join(f"{n[:5]} {d['G']}/{d['S']}" for n, d in r["pistas"].items() if d["G"] is not None)
            L.append(f"{r['sep_media']:5} {m['sep']:5}  {'⚠ ' if r['avisos'] else ''}{r['cancion']}  [c.{m['desde_compas']}, {m['seg']} s, "
                     f"{'/'.join(m['pareja']) if m['pareja'] else '?'}]  {ps}")
        open(os.path.join(TDJ, "_ritmo", "_CAPAS.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
        json.dump([{k: v for k, v in r.items() if k != "filas"} for r in res],
                  open(os.path.join(TDJ, "_ritmo", "_CAPAS.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    else:
        r = medir(sys.argv[1])
        if not r:
            sys.exit("Sin pistas separadas o sin ritmo.json")
        guardar(sys.argv[1], r)
        print(texto(r)[:1500])


if __name__ == "__main__":
    main()
