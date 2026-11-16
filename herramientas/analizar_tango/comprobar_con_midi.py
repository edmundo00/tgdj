"""Compara un MIDI (o partitura pasada a MIDI) con el análisis de la grabación.

Uso: python comprobar_con_midi.py <archivo.mid> <audio original> <carpeta del análisis> [--desplaz N]

Cómo empareja (cambiado el 16-11-2026: la versión anterior alineaba por croma + DTW en segundos
y con «Paciencia» de Omar Benítez se perdía por completo):
1. Pone el MIDI y la grabación en la misma rejilla: un valor de armonía por TIEMPO
   (tiempos del MIDI y pulsos.csv del análisis). Prueba el MIDI con su tiempo tal cual,
   el doble (si está escrito «a medio tiempo») y la mitad, y se queda con el que mejor cuadra.
2. DTW tiempo a tiempo → qué pulso nuestro corresponde a cada tiempo del MIDI
   (aguanta repeticiones, cortes y que el disco acelere).
3. Afina el emparejamiento corriéndolo de -3 a +3 tiempos y elige el que da más notas
   del bajo iguales (la armonía sola no distingue un tiempo de otro, el bajo sí).
4. Mide: golpes por instrumento, dónde cae el 1 del MIDI, armonía por compás,
   notas del bajo (pista contrabajo separada) y melodía (pista de voz separada).
Las cifras «al azar» (MIDI corrido 5 tiempos) dicen cuánto vale cada número.
"""
import sys, csv, os, collections
import numpy as np, librosa, pretty_midi
from scipy.ndimage import uniform_filter1d

SR, HOP, TOL = 22050, 512, 0.07


def leer_analisis(carpeta):
    pul = list(csv.DictReader(open(os.path.join(carpeta, "pulsos.csv"), encoding="utf-8-sig"), delimiter=";"))
    pb = np.array([float(r["seg"]) for r in pul])
    pt = np.array([int(r["tiempo"]) for r in pul])
    pc = np.array([int(r["compas"]) for r in pul])
    golpes = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(carpeta, "golpes.csv"), encoding="utf-8-sig"), delimiter=";"):
        golpes[r["pista"]].append(float(r["seg"]))
    return pb, pt, pc, {k: np.array(sorted(v)) for k, v in golpes.items()}


def tipo(ins):
    """Qué instrumento es una pista del MIDI, por nombre o por programa General MIDI."""
    n, p = ins.name.lower(), ins.program
    if ins.is_drum:
        return None
    if any(s in n for s in ("canto", "voz", "voice", "vocal", "melod")):
        return "voz"
    if any(s in n for s in ("bajo", "contrab", "bass")) or 32 <= p <= 39 or p == 43:
        return "contrabajo"
    if "bandon" in n or "acorde" in n or p in (21, 22, 23):
        return "bandoneones"
    if "piano" in n or p <= 7:
        return "piano"
    if any(s in n for s in ("viol", "chelo", "cello", "viola", "string", "cuerda")) or 40 <= p <= 51:
        return "violines"
    return None


def rejilla_midi(m, factor):
    b = np.array(m.get_beats())
    if factor == 2:
        b = np.sort(np.concatenate([b, (b[:-1] + b[1:]) / 2]))
    elif factor == 0.5:
        b = b[::2]
    return b


def croma_por_tiempo(C, tiempos, fps):
    fr = np.clip((tiempos * fps).astype(int), 0, C.shape[1] - 1)
    S = librosa.util.sync(C, list(np.unique(fr)), aggregate=np.mean)
    return librosa.util.normalize(uniform_filter1d(S, 4, axis=1) + 1e-6, axis=0, norm=2)


def acierto(ref, est):
    ref = ref[~np.isnan(ref)]
    if len(ref) == 0 or len(est) == 0:
        return np.nan, np.nan
    est = est[(est >= ref.min() - TOL) & (est <= ref.max() + TOL)]
    if len(est) == 0:
        return 0.0, 0.0
    enc = np.mean([np.min(np.abs(est - x)) <= TOL for x in ref])
    cor = np.mean([np.min(np.abs(ref - x)) <= TOL for x in est])
    return enc, cor


def main(mid, audio, carpeta, desplaz_fijo=None):
    m = pretty_midi.PrettyMIDI(mid)
    pb, pt, pc, golpes = leer_analisis(carpeta)
    pistas = collections.defaultdict(list)
    for ins in m.instruments:
        t = tipo(ins)
        if t:
            pistas[t].extend(ins.notes)
    for t in pistas:  # quitar notas repetidas (p. ej. «Bajo» y «bajo II» iguales)
        vistas = {}
        for n in pistas[t]:
            vistas.setdefault((round(n.start, 2), n.pitch), n)
        pistas[t] = sorted(vistas.values(), key=lambda n: n.start)
    print("Pistas del MIDI:", {k: len(v) for k, v in pistas.items()})

    y, _ = librosa.load(audio, sr=SR, mono=True)
    A = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    Ac = croma_por_tiempo(A, pb, SR / HOP)
    Mfull = m.get_chroma(fs=SR / HOP)

    # 1. transposición: con la armonía media de toda la canción (más fiable que el DTW)
    ha, hm = A.sum(1), Mfull.sum(1)
    k = int(np.argmax([np.dot(ha, np.roll(hm, kk)) / (np.linalg.norm(ha) * np.linalg.norm(hm)) for kk in range(12)]))
    # 2. rejilla del MIDI (tal cual / doble / mitad): la que tenga un número de tiempos más
    #    parecido al de pulsos del disco (el coste del DTW no sirve para elegir: premia rejillas
    #    gruesas). Después, DTW tiempo a tiempo.
    factor = min((1, 2, 0.5), key=lambda f: abs(np.log(len(rejilla_midi(m, f)) / len(pb))))
    mb = rejilla_midi(m, factor)
    Mc = np.roll(croma_por_tiempo(Mfull, mb, SR / HOP), k, axis=0)
    D, wp = librosa.sequence.dtw(X=Mc, Y=Ac, metric="cosine")
    coste, wp = D[-1, -1] / len(wp), wp[::-1]
    print(f"Tiempos del MIDI: {len(mb)} (rejilla x{factor}) · pulsos del análisis: {len(pb)}")
    print(f"Transposición del MIDI: {k} semitonos · coste {coste:.3f} (0 = idéntico)")

    # tiempo MIDI i -> pulso j (primera pareja de la ruta para cada i)
    base = {}
    for i, j in wp:
        base.setdefault(int(i), int(j))
    ib = np.array(sorted(base)); jb = np.array([base[i] for i in ib], float)

    def a_grabacion(t, s):
        bf = np.interp(t, mb, np.arange(len(mb)), left=np.nan, right=np.nan)
        pj = np.interp(bf, ib, jb) + s
        return np.interp(pj, np.arange(len(pb)), pb, left=np.nan, right=np.nan)

    # notas del bajo en la pista separada
    ruta_bajo = os.path.join(carpeta, "pistas", "contrabajo.flac")
    Cb = None
    if os.path.exists(ruta_bajo):
        yb, _ = librosa.load(ruta_bajo, sr=SR, mono=True)
        Cb = np.abs(librosa.cqt(yb, sr=SR, hop_length=256, fmin=librosa.note_to_hz("E1"), n_bins=48))
        umbral = np.percentile(Cb, 60)

    def notas_bajo(s):
        if Cb is None or not pistas["contrabajo"]:
            return np.nan, 0
        ok = tot = 0
        for n in pistas["contrabajo"]:
            ta = a_grabacion(np.array([n.start]), s)[0]
            if np.isnan(ta):
                continue
            f = int((ta + 0.05) * SR / 256)
            if f + 6 >= Cb.shape[1]:
                continue
            spec = Cb[:, f:f + 6].mean(1)
            if spec.max() < umbral:
                continue
            tot += 1
            ok += (np.argmax(spec) + librosa.note_to_midi("E1")) % 12 == (n.pitch + k) % 12
        return ok / max(tot, 1), tot

    # 3. afinar el desplazamiento
    if desplaz_fijo is None:
        tabla = []
        for s in range(-3, 4):
            nb, _ = notas_bajo(s)
            gb = acierto(a_grabacion(np.array([n.start for n in pistas["contrabajo"]]), s), golpes.get("contrabajo", np.array([])))[0] if pistas["contrabajo"] else np.nan
            tabla.append((np.nan_to_num(nb) + 0.5 * np.nan_to_num(gb), s, nb, gb))
        print("\nAfinar (corrido s tiempos):  " + "  ".join(f"s={s:+d}: bajo {nb:.0%}/{gb:.0%}" for _, s, nb, gb in tabla))
        s = max(tabla)[1]
    else:
        s = desplaz_fijo
    print(f"Desplazamiento elegido: {s:+d} tiempos")

    def informe(s, titulo):
        print(f"\n== {titulo} ==")
        db = np.array(m.get_downbeats())
        ta = a_grabacion(db, s)
        idx = [int(np.argmin(np.abs(pb - x))) for x in ta if not np.isnan(x)]
        print("El 1 de cada compás del MIDI cae en nuestro tiempo:", dict(sorted(collections.Counter(int(pt[i]) for i in idx).items())))
        print("Golpes (±70 ms): instrumento | notas MIDI | golpes análisis | encontrados | correctos")
        for nombre in ("contrabajo", "piano", "bandoneones", "violines"):
            if not pistas[nombre]:
                continue
            if nombre not in golpes:
                print(f"   {nombre:12} | {len(pistas[nombre]):4} | el análisis no da golpes de esta pista")
                continue
            r = a_grabacion(np.array(sorted({round(n.start, 3) for n in pistas[nombre]})), s)
            e, c = acierto(r, golpes[nombre])
            print(f"   {nombre:12} | {np.sum(~np.isnan(r)):4} | {len(golpes[nombre]):4} | {e:4.0%} | {c:4.0%}")
        # armonía por compás
        sims = []
        tg = a_grabacion(mb, s); ok_ = ~np.isnan(tg)
        for cc in sorted(set(pc)):
            w = np.where(pc == cc)[0]
            if len(w) < 2:
                continue
            t0, t1 = pb[w[0]], pb[w[-1]] + np.median(np.diff(pb))
            a = A[:, int(t0 * SR / HOP):int(t1 * SR / HOP)].sum(1)
            # trozo del MIDI que corresponde a ese compás de la grabación
            f0m, f1m = (int(np.interp(x, tg[ok_], mb[ok_]) * SR / HOP) for x in (t0, t1))
            mm = np.roll(Mfull[:, f0m:max(f1m, f0m + 1)].sum(1), k)
            if a.sum() > 0 and mm.sum() > 0:
                sims.append(np.dot(a, mm) / (np.linalg.norm(a) * np.linalg.norm(mm)))
        print(f"Armonía por compás: parecido medio {np.mean(sims):.2f}")
        nb, tot = notas_bajo(s)
        if tot:
            print(f"Notas del bajo iguales (sin contar octava): {nb:.0%} de {tot}")
        ruta_voz = os.path.join(carpeta, "pistas", "voz.flac")
        if pistas["voz"] and os.path.exists(ruta_voz):
            yv, _ = librosa.load(ruta_voz, sr=SR, mono=True)
            f0, vf, _ = librosa.pyin(yv, fmin=150, fmax=700, sr=SR, hop_length=256)
            tf = np.arange(len(f0)) * 256 / SR
            ok = tot = 0
            for n in pistas["voz"]:
                a0, a1 = a_grabacion(np.array([n.start, n.end]), s)
                if np.isnan(a0) or np.isnan(a1):
                    continue
                sel = (tf >= a0) & (tf < a1) & vf
                if sel.sum() < 3:
                    continue
                d = ((np.median(librosa.hz_to_midi(f0[sel])) - (n.pitch + k)) + 6) % 12 - 6
                tot += 1; ok += abs(d) <= 0.75
            print(f"Melodía (pista de voz) igual (±¾ semitono): {ok / max(tot, 1):.0%} de {tot}")

    informe(s, "MIDI emparejado")
    informe(s + 5, "Al azar (MIDI corrido 5 tiempos), para comparar")


if __name__ == "__main__":
    args = sys.argv[1:]
    d = None
    if "--desplaz" in args:
        i = args.index("--desplaz"); d = int(args[i + 1]); del args[i:i + 2]
    main(*args[:3], desplaz_fijo=d)
