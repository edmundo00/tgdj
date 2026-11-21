"""Busca en qué segundo de una grabación empieza el audio del reel (y si va más rápido o lento).
Compara la «envolvente de golpes» y el croma con correlación por FFT, probando velocidades.
Uso: python alinear.py audio_reel.wav cancion1.flac [cancion2.flac ...] [--json salida.json]
Con varias canciones dice cuál se parece más (para saber qué grabación es).
"""
import sys, json, numpy as np, librosa
from scipy.signal import fftconvolve

SR, HOP = 22050, 256
FPS = SR / HOP


def rasgos(p):
    y, _ = librosa.load(p, sr=SR, mono=True)
    return librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP), librosa.feature.chroma_stft(y=y, sr=SR, hop_length=HOP)


def norm_corr(largo, corto):
    corto = (corto - corto.mean()) / (corto.std() + 1e-9)
    n = len(corto)
    num = fftconvolve(largo, corto[::-1], mode="valid")
    s1 = fftconvolve(largo, np.ones(n), mode="valid")
    s2 = fftconvolve(largo ** 2, np.ones(n), mode="valid")
    sd = np.sqrt(np.maximum(s2 / n - (s1 / n) ** 2, 1e-12))
    return num / (n * sd)


def alinear(ov, cv, oc, cc):
    """Paso 1 (grueso): correlación de todo el vídeo probando velocidades. El vídeo PUEDE salirse de la canción
    (aplausos, presentación, o la canción cortada): la canción se rellena con ceros a los dos lados y basta con
    que se solapen la mitad. Antes (hasta el 20-11-2026) se exigía que el vídeo entero cupiera dentro y, con 9 s de
    aplausos al final, se saltaba la velocidad buena («Vieja calesita», El Taller Tango: salía 0,94 en vez de 1,025).
    Paso 2 (fino): afinar() mide el desfase en trozos de 10 s y ajusta una recta → inicio y velocidad al ms."""
    pad = int(len(ov) * 1.07) + 2
    ocp = np.concatenate([np.zeros(pad), oc, np.zeros(pad)])
    ccp = np.pad(cc, ((0, 0), (pad, pad)))
    mejor = None
    for vel in np.arange(0.94, 1.0601, 0.0025):     # 1 s de vídeo = vel s de canción
        n = int(len(ov) * vel)
        x = np.linspace(0, len(ov) - 1, n)
        tot = norm_corr(ocp, np.interp(x, np.arange(len(ov)), ov))
        for k in range(12):
            tot = tot + norm_corr(ccp[k], np.interp(x, np.arange(cv.shape[1]), cv[k])) / 12
        pos = np.arange(len(tot)) - pad                       # dónde empieza el vídeo en la canción (fotogramas)
        solape = np.minimum(pos + n, len(oc)) - np.maximum(pos, 0)
        tot[solape < 0.5 * min(n, len(oc))] = -np.inf
        i = int(np.argmax(tot))
        if mejor is None or tot[i] > mejor[0]:
            mejor = (float(tot[i]), i - pad, float(vel))
    s, i, vel = mejor
    res = {"inicio_en_cancion": round(i / FPS, 3), "velocidad": round(vel, 4), "parecido": round(s, 3)}
    fino = afinar(ov, oc, i / FPS, vel)
    if fino:
        res.update(fino)
    return res


def afinar(ov, oc, inicio, vel, trozo=10.0, paso=5.0, margen=0.3):
    """Desfase de cada trozo de `trozo` s del vídeo (buscando ±margen s) y recta canción = inicio + vel · vídeo.
    Devuelve None si no hay al menos 3 trozos buenos (correlación ≥ 0,5)."""
    tv_todo = np.arange(len(ov)) / FPS
    if tv_todo[-1] < 3 * trozo:                                 # vídeo corto (un reel de 15 s): trozos más cortos
        trozo = max(3.0, tv_todo[-1] / 3)
        paso = trozo / 2
    lags = np.arange(-margen, margen + 1e-9, 1 / FPS)
    puntos = []
    for t0 in np.arange(0, tv_todo[-1] - trozo, paso):
        tv = np.arange(t0, t0 + trozo, 1 / FPS)
        xs = np.interp(tv * FPS, np.arange(len(ov)), ov)
        tc0 = inicio + tv * vel
        if tc0[0] - margen < 0 or tc0[-1] + margen > len(oc) / FPS:
            continue                                            # trozo fuera de la canción (aplausos…)
        rs = np.array([np.corrcoef(xs, np.interp((tc0 + l) * FPS, np.arange(len(oc)), oc))[0, 1] for l in lags])
        k = int(np.argmax(rs))
        if rs[k] < 0.5:
            continue
        d = 0.0
        if 0 < k < len(rs) - 1:                                 # pico entre dos fotogramas (parábola)
            den = rs[k - 1] - 2 * rs[k] + rs[k + 1]
            d = 0.5 * (rs[k - 1] - rs[k + 1]) / den if den < 0 else 0.0
        c = t0 + trozo / 2
        puntos.append((c, inicio + c * vel + lags[k] + d / FPS, rs[k]))
    if len(puntos) < 3:
        return None
    p = np.array(puntos)
    usar = np.ones(len(p), bool)
    for _ in range(3):                                          # recta, quitando los trozos que se apartan > 40 ms
        b, a = np.polyfit(p[usar, 0], p[usar, 1], 1)
        err = p[:, 1] - (a + b * p[:, 0])
        nuevo = np.abs(err) < 0.04
        if nuevo.sum() < 3 or (nuevo == usar).all():
            break
        usar = nuevo
    return {"inicio_en_cancion": round(float(a), 3), "velocidad": round(float(b), 5),
            "trozos_buenos": f"{int(usar.sum())} de {len(p)}", "error_ms": round(float(np.sqrt(np.mean(err[usar] ** 2)) * 1000), 1),
            "correlacion_trozos": round(float(np.median(p[usar, 2])), 2)}


if __name__ == "__main__":
    args = sys.argv[1:]
    salida = None
    if "--json" in args:
        k = args.index("--json"); salida = args[k + 1]; del args[k:k + 2]
    ov, cv = rasgos(args[0])
    res = []
    for c in args[1:]:
        r = alinear(ov, cv, *rasgos(c)); r["cancion"] = c
        res.append(r)
        print(f"{r['parecido']:.3f}  desde {r['inicio_en_cancion']:7.3f} s  vel {r['velocidad']:.5f}"
              f"  fino: {r.get('trozos_buenos', 'no')} trozos, error {r.get('error_ms', '-')} ms  {c}", flush=True)
    mejor = max(res, key=lambda r: r["parecido"])
    print("MEJOR:", mejor)
    if salida:
        json.dump(mejor, open(salida, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
