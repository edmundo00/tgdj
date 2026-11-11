"""Comprueba el pulso y los compases del programa con un MIDI de referencia de la misma obra.

El MIDI se alinea con la grabación por armonía (croma + DTW, probando las 12 transposiciones,
porque los arreglos suelen estar en otro tono). Después se mira en qué tiempo de nuestra rejilla
cae cada inicio de compás del MIDI.

Uso: python comprobar_con_midi.py <archivo.mid> <audio original> <carpeta del análisis>
"""
import sys, csv, os
import numpy as np, librosa, pretty_midi

FPS = 20


def croma_audio(audio):
    y, sr = librosa.load(audio, sr=22050, mono=True)
    c = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=sr // FPS)
    return librosa.util.normalize(c, axis=0)


def croma_midi(m):
    c = m.get_chroma(fs=FPS)
    c = c + 1e-3
    return librosa.util.normalize(c, axis=0)


def main(mid, audio, carpeta):
    m = pretty_midi.PrettyMIDI(mid)
    A, Mc = croma_audio(audio), croma_midi(m)
    mejor = None
    for k in range(12):
        Mk = np.roll(Mc, k, axis=0)
        D, wp = librosa.sequence.dtw(X=Mk, Y=A, metric="cosine", subseq=True)
        coste = D[-1, :].min() / Mk.shape[1]
        if mejor is None or coste < mejor[0]:
            mejor = (coste, k, wp)
    coste, k, wp = mejor
    wp = wp[::-1]
    t_midi, t_audio = wp[:, 0] / FPS, wp[:, 1] / FPS
    print(f"Transposición del MIDI: {k} semitonos · coste medio {coste:.3f} (0 = idéntico)")
    print(f"El MIDI cubre de {t_audio[0]:.1f} s a {t_audio[-1]:.1f} s de la grabación")

    pul = list(csv.DictReader(open(os.path.join(carpeta, "pulsos.csv"), encoding="utf-8-sig"), delimiter=";"))
    b = np.array([float(r["seg"]) for r in pul]); tiempo = np.array([int(r["tiempo"]) for r in pul])
    per = np.median(np.diff(b))

    db = m.get_downbeats()
    filas, cuenta, errores = [], {}, []
    for i, d in enumerate(db):
        if d > t_midi[-1]:
            break
        ta = float(np.interp(d, t_midi, t_audio))
        j = int(np.argmin(np.abs(b - ta)))
        err = (ta - b[j]) / per
        errores.append(err)
        cuenta[tiempo[j]] = cuenta.get(tiempo[j], 0) + 1
        filas.append((i + 1, round(ta, 2), int(tiempo[j]), round(err, 2)))

    n = len(filas)
    print(f"\nInicios de compás del MIDI (2/4) comparados: {n}")
    print(f"Pulsos nuestros por compás del MIDI: {np.median(np.diff([np.interp(d, t_midi, t_audio) for d in db[:n]])) / per:.2f}  (lo esperado: 2)")
    print("En qué tiempo nuestro caen:", {t: cuenta.get(t, 0) for t in (1, 2, 3, 4)})
    impares = [f for f in filas if f[0] % 2 == 1]
    pares = [f for f in filas if f[0] % 2 == 0]
    print(f"Compases impares del MIDI (deberían ser nuestro 1): en el 1 {sum(f[2] == 1 for f in impares)}/{len(impares)}, en el 3 {sum(f[2] == 3 for f in impares)}/{len(impares)}")
    print(f"Compases pares del MIDI   (deberían ser nuestro 3): en el 3 {sum(f[2] == 3 for f in pares)}/{len(pares)}, en el 1 {sum(f[2] == 1 for f in pares)}/{len(pares)}")
    print(f"Distancia media al pulso más cercano: {np.median(np.abs(errores)) * per * 1000:.0f} ms (incluye la imprecisión de la alineación)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
