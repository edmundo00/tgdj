"""Paso 2: pulso y compases automáticos.

Se cuenta como el bailarín: 4 tiempos por compás (1 y 2 y 3 y 4 y).
- Pulso: seguimiento de pulso de librosa sobre la mezcla + el contrabajo, muy rígido
  (D'Arienzo no cambia de tempo), y luego cada pulso se ajusta al golpe real más cercano.
- Dónde está el 1: el tiempo en que más cambia la armonía y más pesa el contrabajo.
"""
import numpy as np, librosa

HOP = 256
TIGHT = 300   # cuánto se resiste el pulso a cambiar de tempo


def _env(y, sr):
    return librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP, aggregate=np.median)


def pulsos(mezcla, contrabajo, sr):
    e_mix, e_bajo = _env(mezcla, sr), _env(contrabajo, sr)
    n = min(len(e_mix), len(e_bajo))
    env = e_mix[:n] / (e_mix.max() + 1e-9) + e_bajo[:n] / (e_bajo.max() + 1e-9)

    tempo = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=env, sr=sr, hop_length=HOP, start_bpm=125))[0])
    while tempo < 95: tempo *= 2
    while tempo > 165: tempo /= 2
    _, fr = librosa.beat.beat_track(onset_envelope=env, sr=sr, hop_length=HOP, bpm=tempo,
                                    tightness=TIGHT, trim=True)
    t = librosa.frames_to_time(fr, sr=sr, hop_length=HOP)

    # ajustar cada pulso al pico de golpe más cercano (±60 ms)
    tf = librosa.frames_to_time(np.arange(n), sr=sr, hop_length=HOP)
    w = int(0.06 * sr / HOP)
    aj = []
    for f in fr:
        a, b = max(0, f - w), min(n, f + w + 1)
        aj.append(tf[a + int(np.argmax(env[a:b]))])
    aj = np.array(aj)
    # si el ajuste rompe la regularidad (golpe fuera de sitio), quedarse con el original
    d = np.abs(aj - t)
    aj[d > 0.05] = t[d > 0.05]
    return aj, 60.0 * (len(aj) - 1) / (aj[-1] - aj[0])


def donde_esta_el_1(beats, mezcla, contrabajo, sr):
    """Devuelve 0..3: índice del primer pulso que es un 1."""
    # cambio de armonía al llegar a cada pulso (comparando el tramo que empieza en él con el anterior)
    croma = librosa.feature.chroma_cqt(y=mezcla, sr=sr, hop_length=512)
    fc = np.clip(librosa.time_to_frames(beats, sr=sr, hop_length=512), 0, croma.shape[1] - 1)
    tramos = np.array([np.median(croma[:, fc[i]:max(fc[i + 1], fc[i] + 1)], axis=1) for i in range(len(beats) - 1)]).T
    cambio = np.r_[0, np.linalg.norm(np.diff(tramos, axis=1), axis=0), 0]
    # volumen justo después de cada pulso (el 1 es el más fuerte)
    rms = librosa.feature.rms(y=mezcla, hop_length=HOP)[0]
    fb = np.clip(librosa.time_to_frames(beats, sr=sr, hop_length=HOP), 0, len(rms) - 1)
    vol = np.array([rms[f:f + 20].mean() for f in fb])
    punt = []
    for k in range(4):
        punt.append(float(np.mean(cambio[k::4]) / (np.mean(cambio) + 1e-9) + np.mean(vol[k::4]) / (np.mean(vol) + 1e-9)))
    return int(np.argmax(punt)), punt


def compases(mezcla, contrabajo, sr):
    beats, bpm = pulsos(mezcla, contrabajo, sr)
    fase, punt = donde_esta_el_1(beats, mezcla, contrabajo, sr)
    # compás 1 = el primer 1 completo; los pulsos anteriores son anacrusa (compás 0)
    num = np.array([(i - fase) // 4 + 1 for i in range(len(beats))])
    tiempo = np.array([(i - fase) % 4 + 1 for i in range(len(beats))])
    return dict(beats=beats, compas=num, tiempo=tiempo, bpm=bpm, fase=fase, puntuacion_fase=punt)
