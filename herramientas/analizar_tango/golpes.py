"""Paso 3: golpes de cada instrumento (momento exacto y fuerza) y resumen compás a compás.

Golpe = el volumen de la pista sube de golpe (≥ SUBIDA dB en ~35 ms).
Fuerza = pico de volumen del golpe, en dB respecto a los golpes fuertes de esa pista (0 dB = fuerte habitual).
Violines y voz no se cuentan por golpes (son ligados): se mide cuánto suenan en cada corchea.
"""
import os
import numpy as np, librosa

HOP = 128
SUBIDA = {"contrabajo": 6, "piano": 7, "bandoneones": 7}   # dB de subida en ~35 ms. Contrabajo 6: con «Loca» (1942 y Los Reyes) encuentra 28 de 32 golpes (con 9, 21)
SEMI = ["", "e", "y", "a"]   # 1 e y a: tiempo, semicorchea, corchea, semicorchea


def _db(y, frame=1024):
    r = librosa.feature.rms(y=y, frame_length=frame, hop_length=HOP)[0]
    return 20 * np.log10(r / (r.max() + 1e-12) + 1e-6)


def detectar(y, sr, subida):
    db = _db(y)
    t = librosa.frames_to_time(np.arange(len(db)), sr=sr, hop_length=HOP)
    L = 12
    rise = np.r_[np.zeros(L), db[L:] - db[:-L]]
    out, k, fin_w = [], L, int(0.12 * sr / HOP)
    while k < len(rise):
        if rise[k] >= subida and db[k:k + 40].max() > -35:
            j0 = k - L + int(np.argmax(np.diff(db[k - L:k + 1]) > 0.8))
            fin = min(len(db), k + fin_w)
            out.append((t[j0], db[k:fin].max()))
            k = fin
        else:
            k += 1
    return out


def detectar_flujo(y, sr, delta=0.03, fmin=300):
    """Para el piano: flujo espectral (superflux) en los agudos. Detecta cada nota nueva aunque el volumen
    total no suba (pianitos suaves, notas encima de otras). Probado contra la transcripción del reel de
    «El flete»: con la canción entera encuentra el 87 % de los ataques con un 97 % de aciertos (el detector por volumen, el 56 %)."""
    H = 256
    S = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=H, n_mels=128, fmin=fmin, fmax=8000)
    env = librosa.onset.onset_strength(S=librosa.power_to_db(S), sr=sr, hop_length=H, lag=2, max_size=3)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=H, units="time", delta=delta, wait=4)
    db = _db(y)
    out = []
    for t in on:
        k = int(t * sr / HOP)
        out.append((float(t), float(db[k:k + int(0.1 * sr / HOP)].max()) if k < len(db) else -60.0))
    return out


def posicion(t, beats):
    j = int(np.clip(np.searchsorted(beats, t) - 1, 0, len(beats) - 2))
    return j + (t - beats[j]) / (beats[j + 1] - beats[j])


def calibrar(pistas, sr, P):
    """Mueve la rejilla para que los golpes fuertes del contrabajo caigan en el tiempo.
    (El pulso y los golpes se miden de forma distinta y hay un desfase fijo de unas decenas de ms.)"""
    beats = P["beats"]
    vals = detectar(pistas["contrabajo"], sr, SUBIDA["contrabajo"])
    if not vals:
        return 0.0
    ref = np.percentile([d for _, d in vals], 70)
    dif = []
    for t, d in vals:
        if d < ref:
            continue
        i = int(np.argmin(np.abs(beats - t)))
        per = 60 / P["bpm"]
        if abs(t - beats[i]) < 0.3 * per:
            dif.append(t - beats[i])
    off = float(np.median(dif)) if dif else 0.0
    P["beats"] = beats + off
    if os.environ.get("REAJUSTE", "1") != "0":   # reajuste tramo a tramo (evaluar.py lo compara)
        reajustar_por_tramos(pistas, sr, P)
    return off


def reajustar_por_tramos(pistas, sr, P, vecinos=4, vueltas=3):
    """Corrige la rejilla poco a poco: cada pulso se mueve según dónde caen los golpes fuertes
    (de contrabajo, piano y bandoneones) en los pulsos de alrededor. Los golpes se comparan con el
    tiempo o la «y» más cercanos, así una corchea no arrastra la rejilla medio pulso."""
    hits, pesos = [], []
    for nombre, y in (("contrabajo", pistas["contrabajo"]), ("piano", pistas["piano"]), ("bandoneones", pistas["resto"])):
        v = detectar(y, sr, SUBIDA[nombre])
        if not v:
            continue
        ref = np.percentile([d for _, d in v], 60)
        for t, d in v:
            if d >= ref - 6:
                hits.append(t); pesos.append(10 ** ((d - ref) / 20) * (2 if nombre == "contrabajo" else 1))
    if not hits:
        return
    hits, pesos = np.array(hits), np.array(pesos)
    b = P["beats"].copy()
    for _ in range(vueltas):
        per = np.gradient(b)
        j = np.clip(np.searchsorted(b, hits), 1, len(b) - 1)
        i = np.where(hits - b[j - 1] < b[j] - hits, j - 1, j)           # pulso más cercano
        ph = (hits - b[i]) / per[i]                                      # en pulsos
        dev = ((ph + 0.25) % 0.5) - 0.25                                 # respecto a tiempo o «y»
        ok = np.abs(dev) < 0.2
        nuevo = b.copy()
        for k in range(len(b)):
            m = ok & (np.abs(i - k) <= vecinos)
            if m.sum() >= 3:
                o = np.argsort(dev[m]); cw = np.cumsum(pesos[m][o])
                med = dev[m][o][np.searchsorted(cw, cw[-1] / 2)]         # mediana ponderada
                nuevo[k] = b[k] + med * per[k]
        if np.any(np.diff(nuevo) <= 0.5 * np.median(np.diff(b))):       # no romper el orden
            break
        b = nuevo
    P["beats"] = b


def analizar(pistas, sr, P):
    P["desfase_ms"] = round(calibrar(pistas, sr, P) * 1000)
    beats = P["beats"]
    golpes = []
    for nombre in ["contrabajo", "piano", "bandoneones"]:
        # los ataques de bandoneón se miden en «resto» (más nítido); los violines ligados casi no dan subidas bruscas
        y = pistas["resto"] if nombre == "bandoneones" else pistas[nombre]
        det = detectar_flujo(y, sr) if nombre == "piano" else detectar(y, sr, SUBIDA[nombre])
        vals = [(t, d) for t, d in det if beats[0] - 0.1 <= t <= beats[-1]]
        if not vals:
            continue
        ref = np.percentile([d for _, d in vals], 90)
        for t, d in vals:
            p = posicion(t, beats)
            sub = max(round(p * 4) / 4, 0.0)
            ib = min(int(sub), len(beats) - 1)
            j = min(int(p), len(beats) - 2)
            golpes.append(dict(pista=nombre, seg=round(float(t), 3), compas=int(P["compas"][ib]),
                               tiempo=int(P["tiempo"][ib]), semi=SEMI[int(round((sub % 1) * 4)) % 4],
                               pos=round(float(sub), 2),
                               desvio_ms=int(round((p - sub) * (beats[j + 1] - beats[j]) * 1000)),
                               fuerza_db=round(float(min(d - ref, 6)), 1)))

    # niveles por corchea (violines, voz y la mezcla entera)
    niveles = {}
    for nombre in ["violines", "voz", "mezcla"]:
        db = _db(pistas[nombre], 2048)
        tt = librosa.frames_to_time(np.arange(len(db)), sr=sr, hop_length=HOP)
        v = []
        for k in range(len(beats) - 1):
            for h in (0, 1):
                a0 = beats[k] + h * (beats[k + 1] - beats[k]) / 2
                a1 = a0 + (beats[k + 1] - beats[k]) / 2
                m = (tt >= a0) & (tt < a1)
                v.append(float(db[m].mean()) if m.any() else -60.0)
        niveles[nombre] = np.array(v)
    return golpes, niveles


def orquesta(mezcla, sr, P, umbral=0.3):
    """Grandes golpes de la orquesta entera, sin separar instrumentos (sirve para ver la síncopa).
    En cada corchea del compás (1, 1y, 2, 2y…) se mira cuánto sonido nuevo arranca en la mezcla
    (envolvente de ataques) y se compara con el golpe más fuerte de ese mismo compás:
    fuerza 0 dB = el golpe más fuerte del compás; -10 dB = un tercio. Se guardan los de al menos `umbral`.
    Probado en los ejemplos de síncopa del reel: Nada más (c. 10), El Yaguarón, Te busco."""
    H = 256
    env = librosa.onset.onset_strength(y=mezcla, sr=sr, hop_length=H)
    tf = librosa.frames_to_time(np.arange(len(env)), sr=sr, hop_length=H)
    w = int(0.035 * sr / H)
    beats, comp, tiem = P["beats"], P["compas"], P["tiempo"]

    def pico(t):
        f = int(np.argmin(np.abs(tf - t)))
        return float(env[max(0, f - w):f + w + 1].max())

    golpes = []
    for i in range(len(beats) - 4):
        if tiem[i] != 1 or comp[i] < 1:
            continue
        pos, ts = [], []
        for k in range(4):
            a, b = beats[i + k], beats[i + k + 1]
            for h in (0, 1):
                pos.append(i + k + h / 2)
                ts.append(a + h * (b - a) / 2)
        v = np.array([pico(t) for t in ts])
        v = v / (v.max() + 1e-9)
        for p, t, x in zip(pos, ts, v):
            if x >= umbral:
                ib = int(p)
                golpes.append(dict(pista="orquesta", seg=round(float(t), 3), compas=int(comp[ib]), tiempo=int(tiem[ib]),
                                   semi="" if p % 1 == 0 else "y", pos=round(float(p), 2), desvio_ms=0,
                                   fuerza_db=round(float(20 * np.log10(x)), 1)))
    return golpes


def resumen_compases(golpes, niveles, P):
    """Una fila por compás: dibujo de cada instrumento en 16 semicorcheas y sucesos destacados."""
    comp, tiem = P["compas"], P["tiempo"]
    filas = []
    ref_mezcla = np.median(niveles["mezcla"])
    for c in sorted(set(comp.tolist())):
        if c < 1:
            continue
        idx = [i for i in range(len(comp)) if comp[i] == c]
        if len(idx) < 4 or idx[0] * 2 + 7 >= len(niveles["mezcla"]):
            continue
        fila = dict(compas=c, seg=round(float(P["beats"][idx[0]]), 2))
        for n in ["contrabajo", "piano", "bandoneones"]:
            dib = ["·"] * 16
            for g in golpes:
                if g["pista"] == n and g["compas"] == c:
                    k = (g["tiempo"] - 1) * 4 + SEMI.index(g["semi"])
                    s = "X" if g["fuerza_db"] > -4 else ("x" if g["fuerza_db"] > -12 else "-")
                    if dib[k] == "·" or s == "X": dib[k] = s
            fila[n] = "".join(dib[:4]) + " " + "".join(dib[4:8]) + " " + "".join(dib[8:12]) + " " + "".join(dib[12:])
        cor = slice(idx[0] * 2, idx[0] * 2 + 8)
        fila["violines"] = "".join("=" if v > -14 else ("~" if v > -24 else "·") for v in niveles["violines"][cor])
        fila["voz"] = "sí" if np.mean(niveles["voz"][cor] > -30) >= 0.5 else ""   # canta en al menos media corchea de cada dos

        suc = []
        mz = niveles["mezcla"][cor]
        for b in range(4):
            if np.mean(mz[b * 2:b * 2 + 2]) < ref_mezcla - 12:
                suc.append(f"silencio en el {b + 1}")
        g_c = [g for g in golpes if g["compas"] == c]
        pia = [g for g in g_c if g["pista"] == "piano" and g["fuerza_db"] > -10]
        otros_mismo = {(g["tiempo"], g["semi"]) for g in g_c if g["pista"] != "piano" and g["fuerza_db"] > -12}
        solos = [g for g in pia if (g["tiempo"], g["semi"]) not in otros_mismo]
        if len(solos) >= 2:
            suc.append("pianitos: " + " ".join(f"{g['tiempo']}{g['semi']}" for g in solos))
        sinc = [g for g in g_c if g["pista"] in ("bandoneones", "contrabajo") and g["semi"] in ("e", "a") and g["fuerza_db"] > -6]
        if sinc:
            suc.append("síncopa: " + " ".join(f"{'marcato' if g['pista'] == 'bandoneones' else g['pista']} {g['tiempo']}{g['semi']}" for g in sinc))
        if not any(g["pista"] == "contrabajo" and g["tiempo"] == 1 and g["semi"] == "" for g in g_c):
            suc.append("el contrabajo no marca el 1")
        if fila["violines"].count("=") >= 5:
            suc.append("ligado largo")
        fila["sucesos"] = "; ".join(suc)
        filas.append(fila)
    # un compás suelto «con voz» sin vecinos con voz es sangrado de otro instrumento, no canto
    v = [bool(f["voz"]) for f in filas]
    for k, f in enumerate(filas):
        if v[k] and not ((k > 0 and v[k - 1]) or (k + 1 < len(v) and v[k + 1])):
            f["voz"] = ""
    return filas
