"""Análisis de ritmo general: compás (2/4, 3/4, 4/4), dónde está el 1, cada golpe en su casilla
(semicorcheas o tresillos), sucesos (tresillos, 3+3+2, síncopas, silencios) y búsqueda de dibujos de golpes.

Uso:
    ritmo.bat "ruta\\cancion.flac"
    ritmo.bat "cancion.flac" --compas 3/4          (si no acierta el compás)
    ritmo.bat "cancion.flac" --uno 12.34           (un segundo donde cae un 1, si no acierta el 1)
    ritmo.bat "cancion.flac" --pulso doble|mitad   (si cuenta el pulso a la mitad o al doble)
Las ayudas se guardan en ayudas.json y se vuelven a usar solas la próxima vez.

Fuentes de golpes:
- Si el tango ya tiene pistas separadas por analizar_tango (Analisis tangos\\...\\pistas) se usan:
  contrabajo, piano y bandoneones.
- Si no, se usan bandas de frecuencia de la mezcla: graves (contrabajo, mano izquierda), medios, agudos.

Salida (Analisis tangos\\_ritmo\\<canción>\\):
    ritmo.txt    resumen para leer: compás, el 1 y su seguridad, compás a compás, dibujos encontrados
    ritmo.html   la página para escuchar y comprobarlo (se abre sola al terminar)
    ritmo.json   todo, para la página y para los vídeos (mapa de golpes)
    ayudas.json  las ayudas manuales
Los dibujos que se buscan están en dibujos.txt (junto a este archivo): se pueden añadir más.
"""
import os, sys, json, argparse, time
import numpy as np, librosa, soundfile as sf
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golpes as golpes_mod

# ffmpeg: si no está en el PATH (p. ej. el PC del trabajo), buscarlo en las carpetas de siempre
import shutil, rutas
rutas.preparar_ffmpeg()

SR = 44100
SALIDA_DEF = rutas.ANALISIS
AQUI = os.path.dirname(os.path.abspath(__file__))
BANDAS = {"graves": (35, 200), "medios": (200, 2000), "agudos": (2000, 10000)}
SUB_BIN = {0: "", 1: "e", 2: "y", 3: "a"}          # 1 e y a
TOL = 0.085                                          # tolerancia para casar un golpe con su casilla (en tiempos)


# ---------------------------------------------------------------- cargar cualquier audio o vídeo
def cargar_audio(ruta, sr=SR, duracion=None):
    """librosa no abre vídeos (mp4) ni algunos formatos: entonces se descodifica con ffmpeg."""
    try:
        return librosa.load(ruta, sr=sr, mono=True, duration=duracion)[0]
    except Exception:
        import subprocess
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", ruta, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
        if duracion:
            cmd[4:4] = ["-t", str(duracion)]
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        return np.frombuffer(raw, dtype=np.float32).copy()


# ---------------------------------------------------------------- pulso, compás y el 1
_BT = None


def beat_this(y):
    """Pulsos y unos de Beat This! tal cual (sin forzar el tempo del tango)."""
    global _BT
    from beat_this.inference import Audio2Beats
    if _BT is None:
        _BT = Audio2Beats(checkpoint_path="final0", device="cpu", dbn=False)
    b, d = _BT(y.astype(np.float32), SR)
    return np.asarray(b, float), np.asarray(d, float)


def fuerza_en(env, tf, t, w=0.035):
    i0, i1 = np.searchsorted(tf, t - w), np.searchsorted(tf, t + w)
    return float(env[i0:max(i1, i0 + 1)].max()) if i0 < len(env) else 0.0


def elegir_compas_y_uno(beats, unos_bt, envs, tf, ayuda):
    """Prueba compases de 2, 3 y 4 tiempos y todas las posiciones del 1. Vota cada fuente por separado."""
    votos = {}
    # Beat This!: cuántos tiempos hay entre sus unos y en qué tiempo caen
    idx = [int(np.argmin(np.abs(beats - x))) for x in unos_bt if np.min(np.abs(beats - x)) < 0.08]
    if len(idx) >= 4:
        gaps = np.diff(idx)
        vals, cnt = np.unique(gaps[(gaps >= 2) & (gaps <= 4)], return_counts=True)
        m_bt = int(vals[np.argmax(cnt)]) if len(vals) else 4
        f_bt = np.bincount(np.array(idx) % m_bt, minlength=m_bt)
        votos["Beat This!"] = (m_bt, int(np.argmax(f_bt)), float(f_bt.max() / f_bt.sum()))
    # cada fuente: el 1 es el tiempo con más golpe de media (y con más diferencia sobre los demás)
    puntos = {}
    for nombre, env in envs.items():
        f = np.array([fuerza_en(env, tf, t) for t in beats])
        f = f / (np.median(f) + 1e-9)
        mejor = None
        for m in (2, 3, 4):
            medias = np.array([f[k::m].mean() for k in range(m)])
            contraste = medias.max() / (np.mean(np.delete(medias, medias.argmax())) + 1e-9)
            if mejor is None or contraste > mejor[2] * 1.08:      # preferir compases cortos si empatan
                mejor = (m, int(medias.argmax()), float(contraste))
        puntos[nombre] = mejor
        votos[nombre] = (mejor[0], mejor[1], min(1.0, (mejor[2] - 1) * 2))
    # compás: lo que diga la ayuda; si no, Beat This! si está; si no, mayoría de las fuentes
    if ayuda.get("compas"):
        m = int(ayuda["compas"].split("/")[0]); de_m = "ayuda"
    elif "Beat This!" in votos:
        m = votos["Beat This!"][0]; de_m = "Beat This!"
    else:
        ms = [v[0] for v in votos.values()]; m = max(set(ms), key=ms.count); de_m = "fuentes"
    # el 1: ayuda > acuerdo de fuentes
    if ayuda.get("uno") is not None:
        k = int(np.argmin(np.abs(beats - float(ayuda["uno"])))) % m
        return m, k, de_m, "ayuda", votos, "seguro (ayuda)"
    # Cada fuente vota por las posiciones del 1 que son compatibles con lo que ha visto.
    # Una fuente que ve 2/4 dentro de un 4/4 vota a la vez por el 1 y el 3 (no sabe cuál de los dos es el 1).
    cand, quien = {}, {}
    for nombre, (mv, kv, conf) in votos.items():
        if mv == m:
            opciones = [kv % m]
        elif m == 4 and mv == 2:
            opciones = [kv % 2, kv % 2 + 2]
        elif m == 2 and mv == 4:
            opciones = [kv % 2]
        else:
            continue
        peso = conf * (1.5 if nombre == "Beat This!" else 1.0) / len(opciones)
        for kk in opciones:
            cand[kk] = cand.get(kk, 0) + peso
            if conf >= 0.2:
                quien.setdefault(kk, set()).add(nombre)
    if not cand:
        return m, 0, de_m, "sin datos", votos, "dudoso"
    k = max(cand, key=cand.get)
    total = sum(cand.values())
    seg = cand[k] / total if total else 0
    n_ok = len(quien.get(k, ()))
    if seg >= 0.6 and n_ok >= 2:
        estado = "seguro"
    elif seg >= 0.5 and n_ok >= 1:
        estado = "probable"
    else:
        estado = "dudoso"
    return m, k, de_m, "votación", votos, f"{estado} ({seg:.0%} de los votos; de acuerdo: {', '.join(sorted(quien.get(k, ()))) or 'nadie'})"


# ---------------------------------------------------------------- golpes de cada fuente
def fuentes(y, nombre, audio=None, separar_ya=False):
    """Busca pistas separadas de analizar_tango; si no hay y se pide --separar, separa ahora (unos minutos);
    si no, bandas de frecuencia."""
    for base in (os.path.join(SALIDA_DEF, nombre), os.path.join(SALIDA_DEF, "_datos", nombre)):
        p = os.path.join(base, "pistas")
        if all(os.path.exists(os.path.join(p, f"{n}.flac")) for n in ("contrabajo", "piano", "resto")):
            carga = lambda n: librosa.load(os.path.join(p, f"{n}.flac"), sr=SR, mono=True)[0]
            return {"contrabajo": carga("contrabajo"), "piano": carga("piano"), "bandoneones": carga("resto")}, "pistas separadas"
    if separar_ya and audio:
        import separar
        dir_p = os.path.join(SALIDA_DEF, "_datos", nombre, "pistas")
        print("    separando instrumentos (unos minutos la primera vez)…", flush=True)
        p = separar.separar(audio, dir_p, os.path.join(rutas.VENVS, "modelos_separador"))
        return {"contrabajo": p["contrabajo"], "piano": p["piano"], "bandoneones": p["resto"]}, "pistas separadas"
    _, perc = librosa.effects.hpss(y, margin=2.0)
    out = {}
    for n, (lo, hi) in BANDAS.items():
        sos = butter(4, [lo, hi], btype="band", fs=SR, output="sos")
        out[n] = sosfiltfilt(sos, perc if n != "graves" else y)
    return out, "bandas de frecuencia"


def detectar_golpes(nombre, x):
    if nombre == "contrabajo":
        return golpes_mod.detectar(x, SR, golpes_mod.SUBIDA["contrabajo"])
    if nombre == "piano":
        return golpes_mod.detectar_flujo(x, SR)
    if nombre == "bandoneones":
        return golpes_mod.detectar(x, SR, golpes_mod.SUBIDA["bandoneones"])
    H = 256
    env = librosa.onset.onset_strength(y=x, sr=SR, hop_length=H)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=H, units="frames", delta=0.06, wait=5)
    if not len(on):
        return []
    v = env[on] / (np.percentile(env[on], 90) + 1e-9)
    tt = afinar(x, librosa.frames_to_time(on, sr=SR, hop_length=H))
    return [(float(t), float(20 * np.log10(max(a, 1e-3)))) for t, a in zip(tt, v)]


def cambios_nota(x):
    """Notas por cambio de ALTURA, no por golpe: instantes en que aparece una frecuencia nueva (flujo del CQT).
    Ve también las notas ligadas, que casi no dan golpe (bandoneón, violín). Devuelve [(seg, fuerza dB, midi)].
    Nombrar la nota no es fiable con la orquesta entera (octavas, acordes); el instante sí (18-11-2026)."""
    sr2, hop = 22050, 128                                    # ~5,8 ms
    z = librosa.resample(x, orig_sr=SR, target_sr=sr2)
    C = np.abs(librosa.cqt(z, sr=sr2, hop_length=hop, fmin=librosa.note_to_hz("C2"), n_bins=72, bins_per_octave=12))
    L = np.log1p(30 * C / (C.max() + 1e-9))
    D = np.maximum(0, L[:, 2:] - L[:, :-2])
    fl = np.r_[0, D.sum(0), 0]
    fl = np.convolve(fl, np.ones(3) / 3, "same")
    # cada trozo comparado con lo que suena alrededor (~2 s): así salen las notas flojas de un pasaje suave
    from scipy.ndimage import maximum_filter1d
    fl = fl / (maximum_filter1d(fl, size=int(2.0 * sr2 / hop)) + 1e-9)
    pk = librosa.util.peak_pick(fl, pre_max=6, post_max=6, pre_avg=12, post_avg=12, delta=0.08, wait=12)
    if not len(pk):
        return []
    ref = np.percentile(fl[pk], 90) + 1e-9
    out = []
    for i in pk:
        j = int(np.clip(i - 1, 0, D.shape[1] - 1))
        out.append((float(i * hop / sr2), float(20 * np.log10(max(fl[i] / ref, 1e-3))), int(36 + np.argmax(D[:, j]))))
    return out


def afinar(x, tiempos):
    """Lleva cada golpe al instante en que más deprisa sube el sonido (el ataque), con 1,5 ms de precisión.
    El detector de librosa da el pico de su envolvente, que llega unos 40-50 ms tarde: con la habanera
    eso descuadraba la rejilla (lo notó el usuario de oído)."""
    H = 64
    r = librosa.feature.rms(y=x, frame_length=256, hop_length=H, center=True)[0]
    d = np.diff(r, prepend=r[0])
    out = []
    for t in tiempos:
        a, b = int((t - 0.06) * SR / H), int((t + 0.02) * SR / H)
        a, b = max(0, a), min(len(d), max(b, a + 1))
        out.append((a + int(np.argmax(d[a:b]))) * H / SR if b > a else t)
    return out


def envolvente(x):
    H = 256
    env = librosa.onset.onset_strength(y=x, sr=SR, hop_length=H)
    return env, librosa.frames_to_time(np.arange(len(env)), sr=SR, hop_length=H)


def casilla(f):
    """f = fracción del tiempo (0..1). Devuelve (tipo, índice, distancia): binaria (1 e y a) o tresillo (⅓ ⅔)."""
    db = min(range(5), key=lambda k: abs(f - k / 4)); eb = abs(f - db / 4)
    dt = min(range(4), key=lambda k: abs(f - k / 3)); et = abs(f - dt / 3)
    if dt in (1, 2) and et < eb and et < TOL:
        return "tresillo", dt, et
    return ("binaria", db % 4, eb) if eb < TOL else ("libre", db % 4, eb)


def nombre_casilla(tiempo, tipo, k):
    if tipo == "tresillo":
        return f"{tiempo}{'⅓' if k == 1 else '⅔'}"
    return f"{tiempo}{SUB_BIN[k]}"


# ---------------------------------------------------------------- dibujos
def leer_dibujos(ruta):
    out = []
    for linea in open(ruta, encoding="utf-8"):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        p = [s.strip() for s in linea.split("|")]
        if len(p) != 5:
            continue
        out.append(dict(nombre=p[0], fuente=p[1], casillas=int(p[2]), tiempos=int(p[3]), golpes=[int(g) - 1 for g in p[4].split()]))
    return out


def buscar_dibujo(d, golpes, beats, m, k1, nombres_fuentes):
    """Ventanas de `tiempos` tiempos alineadas con el compás. Nota = golpes en sus casillas − golpes de sobra."""
    T = d["tiempos"]; N = d["casillas"]
    srcs = nombres_fuentes if d["fuente"] == "cualquiera" else [d["fuente"]]
    res = []
    starts = [i for i in range(k1 % T if T <= m else k1, len(beats) - T - 1, T if T <= m else m)]
    for i in starts:
        a, b = beats[i], beats[i + T]
        mejor = None
        for s in srcs:
            gs = [g for g in golpes if g["fuente"] == s and a - 0.04 <= g["seg"] < b - 0.02]
            if not gs:
                continue
            pos = np.array([(g["seg"] - a) / (b - a) * N for g in gs])
            fz = np.array([g["s"] for g in gs])
            # tolerancia: un cuarto de casilla, y nunca más de 45 ms
            tol = min(0.25, 0.045 / ((b - a) / N))
            dentro, usado = [], np.zeros(len(gs), bool)
            for c in d["golpes"]:
                cerca = np.abs(pos - c) < tol
                dentro.append(fz[cerca].max() if cerca.any() else 0.0)
                usado |= cerca
            # de sobra: todo golpe que no cae en una casilla del dibujo (esté donde esté, no solo en la rejilla)
            fuera = fz[~usado & (pos > -tol) & (pos < N - tol)]
            sobra = float(np.sum(fuera[fuera >= 0.3]))
            nota = float(np.mean(dentro) - 0.5 * sobra / len(d["golpes"]))
            if mejor is None or nota > mejor[0]:
                mejor = (nota, s)
        if mejor:
            res.append(dict(i=i, seg=float(a), nota=mejor[0], fuente=mejor[1]))
    # tramos: ventanas seguidas con nota ≥ 0,55
    tramos, cur = [], []
    for r in res:
        if r["nota"] >= 0.55 and (not cur or r["i"] == cur[-1]["i"] + (T if T <= m else m)):
            cur.append(r)
        else:
            if len(cur) >= 2: tramos.append(cur)
            cur = [r] if r["nota"] >= 0.55 else []
    if len(cur) >= 2: tramos.append(cur)
    out = [dict(desde_seg=round(t[0]["seg"], 3), hasta_seg=round(float(beats[t[-1]["i"] + T]), 3), ventanas=len(t),
                nota=round(float(np.mean([x["nota"] for x in t])), 2), fuente=max(set(x["fuente"] for x in t), key=[x["fuente"] for x in t].count),
                primer_tiempo=int(t[0]["i"]))
           for t in tramos]
    out.sort(key=lambda x: -x["ventanas"] * x["nota"])
    return out, res


# ---------------------------------------------------------------- sucesos por compás
def sucesos(bar_golpes, tiempos_bar, m):
    s = []
    por_fuente = {}
    for g in bar_golpes:
        por_fuente.setdefault(g["fuente"], []).append(g)
    for f, gs in por_fuente.items():
        # fuerza en cada casilla (la mayor si hay varios golpes)
        F = {}
        for g in gs:
            if g["tipo"] != "libre":
                key = (g["tiempo"], g["tipo"], g["k"])
                F[key] = max(F.get(key, 0), g["s"])
        on = lambda t, tipo, k, u=0.4: F.get((t, tipo, k), 0) >= u
        off = lambda t, tipo, k: F.get((t, tipo, k), 0) < 0.3
        # tresillo de corcheas dentro de un tiempo, limpio (sin semicorcheas en medio)
        for t in range(1, m + 1):
            if on(t, "binaria", 0) and on(t, "tresillo", 1) and on(t, "tresillo", 2) and all(off(t, "binaria", k) for k in (1, 2, 3)):
                s.append(f"tresillo en el {t} ({f})")
        # 3+3+2 limpio en pares de tiempos: casillas 1, 4 y 7 de 8 semicorcheas, y vacías la 2, 3, 6 y 8
        for t in range(1, m, 2):
            if (on(t, "binaria", 0) and on(t, "binaria", 3) and on(t + 1, "binaria", 2)
                    and all(off(*c) for c in [(t, "binaria", 1), (t, "binaria", 2), (t + 1, "binaria", 1), (t + 1, "binaria", 3)])):
                extra = " con el 5 (1·4·5·7)" if on(t + 1, "binaria", 0) else ""
                s.append(f"3+3+2 en {t}-{t + 1}{extra} ({f})")
        # síncopa: golpe fuerte a contratiempo y el tiempo siguiente vacío
        for g in gs:
            if g["s"] >= 0.7 and (g["tipo"] == "binaria" and g["k"] in (1, 2, 3)):
                sig = g["tiempo"] + 1
                if sig <= m and not any(h["tiempo"] == sig and h["s"] >= 0.3 and (h["tipo"] != "binaria" or h["k"] == 0) for h in gs):
                    s.append(f"síncopa en {g['casilla']} ({f})")
    # silencio: tiempos sin ningún golpe
    vacios = [t for t in range(1, m + 1) if not any(g["tiempo"] == t for g in bar_golpes)]
    if vacios and len(vacios) < m:
        s.append("silencio en el " + ", ".join(map(str, vacios)))
    elif len(vacios) == m:
        s.append("compás en silencio")
    return sorted(set(s), key=s.index)


def dibujo_bar(gs, m, fuente):
    """Texto por tiempos: · nada, x golpe, X fuerte; los tresillos con 3 casillas."""
    out = []
    for t in range(1, m + 1):
        gt = [g for g in gs if g["fuente"] == fuente and g["tiempo"] == t]
        ter = any(g["tipo"] == "tresillo" for g in gt)
        n = 3 if ter else 4
        cel = ["·"] * n
        for g in gt:
            k = g["k"] if (g["tipo"] == "tresillo" or not ter) else (0 if g["k"] == 0 else None)
            if g["tipo"] == "binaria" and ter and g["k"] != 0:
                continue
            if k is None or g["tipo"] == "libre":
                continue
            if g["s"] < 0.3: continue
            c = "X" if g["s"] >= 0.7 else "x"
            if cel[k] != "X": cel[k] = c
        out.append(("³" if ter else "") + "".join(cel))
    return " ".join(out)


# ---------------------------------------------------------------- principal
def analizar(audio, ayuda_cli):
    nombre = os.path.splitext(os.path.basename(audio))[0]
    out = os.path.join(SALIDA_DEF, "_ritmo", nombre)
    os.makedirs(out, exist_ok=True)
    f_ay = os.path.join(out, "ayudas.json")
    ayuda = json.load(open(f_ay, encoding="utf-8")) if os.path.exists(f_ay) else {}
    ayuda.update({k: v for k, v in ayuda_cli.items() if v is not None and k not in ("separar", "abrir")})
    json.dump(ayuda, open(f_ay, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    t0 = time.time()

    print("1/4 Pulso (Beat This!)…", flush=True)
    y = cargar_audio(audio)
    beats, unos_bt = beat_this(y)
    if ayuda.get("pulso") == "doble":
        beats = np.sort(np.r_[beats, (beats[:-1] + beats[1:]) / 2])
    elif ayuda.get("pulso") == "mitad":
        k = int(np.argmax([sum(np.min(np.abs(beats[i::2] - x)) < 0.05 for x in unos_bt) for i in (0, 1)]))
        beats = beats[k::2]

    print("2/4 Golpes de cada fuente…", flush=True)
    src, tipo_src = fuentes(y, nombre, audio, ayuda_cli.get("separar"))
    golpes = []
    for n, x in src.items():
        det = [(t, d) for t, d in detectar_golpes(n, x) if beats[0] - 0.1 <= t < beats[-1]]
        if not det:
            continue
        ref = np.percentile([d for _, d in det], 90)
        for t, d in det:
            golpes.append(dict(fuente=n, seg=float(t), s=float(np.clip(1 + (d - ref) / 24, 0, 1))))
    # desfase fijo entre el pulso y los golpes: se corrige con los golpes fuertes cerca del tiempo
    per = np.median(np.diff(beats))
    dif = [g["seg"] - beats[np.argmin(np.abs(beats - g["seg"]))] for g in golpes if g["s"] >= 0.6]
    dif = [d for d in dif if abs(d) < 0.12 * per]
    off = float(np.median(dif)) if len(dif) >= 8 else 0.0
    beats = beats + off

    print("3/4 Compás y el 1…", flush=True)
    envs = {}
    tf = None
    for n, x in src.items():
        e, tf_n = envolvente(x)
        envs[n] = e; tf = tf_n
    m, k1, de_m, de_1, votos, seguridad = elegir_compas_y_uno(beats, unos_bt, envs, tf, ayuda)
    comp = np.array([(i - k1) // m + 1 for i in range(len(beats))])
    tiem = np.array([(i - k1) % m + 1 for i in range(len(beats))])

    # cada golpe en su casilla
    for g in golpes:
        j = int(np.clip(np.searchsorted(beats, g["seg"]) - 1, 0, len(beats) - 2))
        f = (g["seg"] - beats[j]) / (beats[j + 1] - beats[j])
        tipo, k, err = casilla(f)
        if tipo == "binaria" and k == 0 and f > 0.5:    # cae justo antes del tiempo siguiente
            j = min(j + 1, len(beats) - 2); f -= 1
        g.update(compas=int(comp[j]), tiempo=int(tiem[j]), tipo=tipo, k=int(k),
                 desvio_ms=int(round((f - (k / 3 if tipo == "tresillo" else k / 4)) * (beats[j + 1] - beats[j]) * 1000)),
                 casilla=nombre_casilla(int(tiem[j]), tipo, k))

    # cambios de nota (por altura) de cada fuente, colocados en su casilla como los golpes
    notas = []
    for n, x in src.items():
        det = [(t, d, mi) for t, d, mi in cambios_nota(x) if beats[0] - 0.1 <= t < beats[-1]]
        gs = np.array(sorted(g["seg"] for g in golpes if g["fuente"] == n))
        # el flujo de altura llega un poco tarde: se corrige con los golpes de la misma fuente que caen cerca
        if len(gs):
            dif = [t - gs[np.argmin(np.abs(gs - t))] for t, _, _ in det]
            dif = [d for d in dif if abs(d) < 0.04]
            corr = float(np.median(dif)) if len(dif) >= 8 else 0.0
        else:
            corr = 0.0
        for t, d, mi in det:
            t -= corr
            j = int(np.clip(np.searchsorted(beats, t) - 1, 0, len(beats) - 2))
            f = (t - beats[j]) / (beats[j + 1] - beats[j])
            tipo, k, _ = casilla(f)
            if tipo == "binaria" and k == 0 and f > 0.5:
                j = min(j + 1, len(beats) - 2)
            notas.append(dict(fuente=n, seg=round(float(t), 3), compas=int(comp[j]), tiempo=int(tiem[j]), tipo=tipo,
                              casilla=nombre_casilla(int(tiem[j]), tipo, k), fuerza=round(float(np.clip(1 + d / 24, 0, 1)), 2), midi=mi))

    print("4/4 Dibujos y sucesos…", flush=True)
    dibujos = leer_dibujos(os.path.join(AQUI, "dibujos.txt"))
    nombres_f = list(src)
    encontrados = []
    for d in dibujos:
        if d["fuente"] != "cualquiera" and d["fuente"] not in src:
            # «graves» y «contrabajo» son lo mismo según haya pistas o no
            alias = {"graves": "contrabajo", "contrabajo": "graves", "medios": "piano", "piano": "medios"}
            if alias.get(d["fuente"]) in src:
                d = dict(d, fuente=alias[d["fuente"]])
            else:
                continue
        # Beat This! a veces cuenta el pulso al doble (como el bailarín de milonga): se busca en las dos escalas
        for esc in (1, 2):
            de = dict(d, tiempos=d["tiempos"] * esc)
            tr, _ = buscar_dibujo(de, golpes, beats, m, k1, nombres_f)
            for t in tr:
                t["escala"] = "normal" if esc == 1 else "pulso al doble"
            encontrados.append(dict(nombre=d["nombre"] + ("" if esc == 1 else " · en el doble de tiempos"), fuente=de["fuente"],
                                    casillas=d["casillas"], tiempos=de["tiempos"], golpes=[g + 1 for g in d["golpes"]], tramos=tr[:12]))

    compases = []
    tern_total = bin_total = 0
    for c in range(1, int(comp.max()) + 1):
        ib = np.where(comp == c)[0]
        if len(ib) < m or ib[-1] + 1 >= len(beats):
            continue
        gs = [g for g in golpes if g["compas"] == c]
        tern = sum(g["tipo"] == "tresillo" and g["s"] >= 0.5 for g in gs)
        bina = sum(g["tipo"] == "binaria" and g["k"] in (1, 3) and g["s"] >= 0.5 for g in gs)
        tern_total += tern; bin_total += bina
        compases.append(dict(compas=c, seg=round(float(beats[ib[0]]), 3),
                             dibujo={n: dibujo_bar(gs, m, n) for n in nombres_f},
                             sensacion="tresillos" if tern > bina and tern >= 2 else ("binaria" if bina > tern else ""),
                             sucesos=sucesos(gs, None, m)))

    meta = dict(cancion=nombre, audio=audio, compas=f"{m}/4", compas_de=de_m, uno_de=de_1, seguridad_1=seguridad,
                bpm=round(60 / np.median(np.diff(beats)), 1), desfase_corregido_ms=round(off * 1000),
                fuentes=tipo_src, votos={k: dict(compas=f"{v[0]}/4", uno_en_tiempo=v[1] + 1, confianza=round(v[2], 2)) for k, v in votos.items()},
                subdivision="sobre todo tresillos" if tern_total > bin_total else "sobre todo binaria (semicorcheas)",
                ayudas=ayuda, primer_uno_seg=round(float(beats[k1]), 3))
    datos = dict(meta=meta,
                 pulsos=[dict(seg=round(float(b), 3), compas=int(c), tiempo=int(t)) for b, c, t in zip(beats, comp, tiem)],
                 golpes=[dict(fuente=g["fuente"], seg=round(g["seg"], 3), compas=g["compas"], tiempo=g["tiempo"], casilla=g["casilla"],
                              tipo=g["tipo"], desvio_ms=g["desvio_ms"], fuerza=round(g["s"], 2)) for g in golpes],
                 compases=compases, dibujos=encontrados, notas=notas)
    json.dump(datos, open(os.path.join(out, "ritmo.json"), "w", encoding="utf-8"), ensure_ascii=False)
    escribir_txt(os.path.join(out, "ritmo.txt"), datos, nombres_f)
    import pagina_ritmo
    url = pagina_ritmo.generar(out, datos, audio, SALIDA_DEF)
    if os.path.exists(os.path.join(out, "partitura.json")):   # tiene partitura: cuadrarla otra vez con los pulsos nuevos
        try:
            import partitura
            partitura.hacer(out)
        except BaseException as e:
            print("  (no se pudo rehacer la partitura:", e, ")")
    pagina_ritmo.actualizar_indice(SALIDA_DEF)
    print(f"Página: {url}")
    if ayuda_cli.get("abrir") and os.name == "nt":
        pagina_ritmo.abrir(url)
    print(f"Hecho en {time.time() - t0:.0f} s → {out}")
    return datos


def escribir_txt(ruta, D, nombres_f):
    M = D["meta"]
    L = [f"RITMO · {M['cancion']}", "",
         f"Compás: {M['compas']} (según {M['compas_de']}) · {M['bpm']} pulsos/min · {M['subdivision']}",
         f"El 1: primer 1 en {M['primer_uno_seg']} s · {M['seguridad_1']} · decidido por {M['uno_de']}",
         f"Golpes medidos en: {M['fuentes']} · desfase corregido: {M['desfase_corregido_ms']} ms",
         "Votos: " + " · ".join(f"{k}: {v['compas']}, 1 en el tiempo {v['uno_en_tiempo']} ({v['confianza']:.0%})" for k, v in M["votos"].items()),
         "Si el compás o el 1 están mal: ritmo.bat \"canción\" --compas 3/4  o  --uno <segundo de un 1>", "",
         "DIBUJOS ENCONTRADOS (tramos seguidos que lo tocan limpio)"]
    for d in D["dibujos"]:
        if not d["tramos"]:
            L.append(f"  {d['nombre']}: no aparece")
            continue
        L.append(f"  {d['nombre']} ({d['fuente']}, casillas {' '.join(map(str, d['golpes']))} de {d['casillas']} en {d['tiempos']} tiempos):")
        for t in d["tramos"][:5]:
            L.append(f"     {t['desde_seg']:7.2f}–{t['hasta_seg']:7.2f} s · {t['ventanas']} veces seguidas · nota {t['nota']:.2f} · {t['fuente']}")
    L += ["", "COMPÁS A COMPÁS  (· nada, x golpe, X fuerte; ³ = tiempo en tresillos)", "  " + "  |  ".join(nombres_f)]
    for c in D["compases"]:
        L.append(f"{c['compas']:4d} {c['seg']:7.2f}s  " + "  |  ".join(c["dibujo"][n] for n in nombres_f)
                 + (f"   ← {'; '.join(c['sucesos'])}" if c["sucesos"] else ""))
    open(ruta, "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Análisis de ritmo")
    ap.add_argument("audio", nargs="+")
    ap.add_argument("--compas", help="2/4, 3/4 o 4/4")
    ap.add_argument("--uno", type=float, help="segundo en el que cae un 1")
    ap.add_argument("--pulso", choices=["doble", "mitad"], help="si cuenta el pulso a la mitad o al doble")
    ap.add_argument("--separar", action="store_true", help="separar instrumentos si aún no lo están (más lento, más fino)")
    ap.add_argument("--abrir", action="store_true", help="abrir la página al terminar (solo lo pone el .bat; Claude nunca)")
    ap.add_argument("--no-abrir", action="store_true", help="(obsoleto: ya no se abre salvo con --abrir)")
    a = ap.parse_args()
    for f in a.audio:
        analizar(f, dict(compas=a.compas, uno=a.uno, pulso=a.pulso, separar=a.separar or None, abrir=a.abrir and len(a.audio) == 1))


if __name__ == "__main__":
    main()
