"""Comprueba un TROZO de partitura (pocos compases, sacado de oído) contra el disco, nota a nota.

Uso (python del venv analizar_tango):
    python comprobar_trozo.py <x.mxl | x.musicxml> "<carpeta _ritmo\\canción>" --compas 65 [--melodia P1] [--informe x.txt]

--compas N = el compás de ritmo.py donde empieza el compás 1 de la partitura (en la página: número de la lupa).
Con anacrusa (primer compás «implicit» de MusicXML, el que MuseScore pone a un compás incompleto): N es donde empieza
el primer compás COMPLETO. Vale cualquier compás de partitura (4/4, 2/4…): todo se cuenta en negras.
La partitura se pone en el tiempo del disco con los PULSOS de ritmo.json (si el disco acelera, la partitura también).

Qué mide (23-11-2026, hecho para el solo de bandoneón de «El buey solo»; comprobar_con_midi.py es para canciones
enteras y con 8 compases se pierde):
1. Afinación del disco en ese trozo (cents respecto a la=440): se corrige antes de nombrar notas.
2. MELODÍA (y en sus SILENCIOS, si suena algo con altura clara) (la parte --melodia, por defecto la primera): por cada nota, la altura que suena (pyin) en la mezcla y en
   cada pista separada de _datos\\<canción>\\pistas; ¿es la nota escrita (sin contar octava)? y el ATAQUE: cuándo
   empieza a sonar esa nota en el disco respecto a lo escrito (ms; + = el disco va tarde).
3. «Al azar»: la misma cuenta con la partitura corrida ±1 corchea, ±1 tiempo y ±1 semitono. Si lo escrito no gana
   claramente, el ritmo o las notas no van.
4. ACORDES (las demás partes): croma del disco en ese tiempo y los 3 acordes que mejor encajan (mayor, menor, 7.ª).
5. Golpes: ataques del disco (mezcla) que caen cerca de cada ataque escrito, y ataques fuertes del disco sin nota escrita.
"""
import sys, os, json, zipfile, argparse
import xml.etree.ElementTree as ET
import numpy as np, librosa

SR, HOP = 22050, 256
NOMBRES = "do do# re re# mi fa fa# sol sol# la la# si".split()
INICIOS = {}          # compás de la partitura → negra donde empieza (para escribir «c5 t2½» con cualquier compás)
PASO = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def nombre(m):
    return f"{NOMBRES[int(round(m)) % 12]}{int(round(m)) // 12 - 1}"


def leer_xml(ruta):
    if ruta.lower().endswith(".mxl"):
        z = zipfile.ZipFile(ruta)
        cont = ET.fromstring(z.read("META-INF/container.xml"))
        raiz = [e for e in cont.iter() if e.tag.endswith("rootfile")][0].get("full-path")
        x = z.read(raiz)
    else:
        x = open(ruta, "rb").read()
    r = ET.fromstring(x)
    for e in r.iter():
        e.tag = e.tag.split("}")[-1]
    return r


def notas_de(raiz):
    """{id parte: (nombre, [(compás, inicio en negras desde el compás 1, duración en negras, [midis])])}"""
    nombres = {sp.get("id"): (sp.findtext("part-name") or sp.get("id")) for sp in raiz.iter("score-part")}
    partes = {}
    anacrusa = 0.0
    for p in raiz.findall("part"):
        div, t, ev, inicio_compas = 1, 0.0, [], 0.0
        ligada = {}
        for num, m in enumerate(p.findall("measure"), 1):
            t = inicio_compas
            INICIOS.setdefault(num, inicio_compas)
            largo = 0.0
            ultimo_inicio = t
            for e in m:
                if e.tag == "attributes" and e.find("divisions") is not None:
                    div = float(e.findtext("divisions"))
                elif e.tag == "backup":
                    t -= float(e.findtext("duration")) / div
                elif e.tag == "forward":
                    t += float(e.findtext("duration")) / div
                elif e.tag == "note":
                    if e.find("grace") is not None:
                        continue
                    d = float(e.findtext("duration") or 0) / div
                    acorde = e.find("chord") is not None
                    ini = ultimo_inicio if acorde else t
                    if not acorde:
                        ultimo_inicio = t
                        t += d
                    largo = max(largo, t - inicio_compas)
                    if e.find("rest") is not None:
                        continue
                    pi = e.find("pitch")
                    midi = 12 * (int(pi.findtext("octave")) + 1) + PASO[pi.findtext("step")] + int(float(pi.findtext("alter") or 0))
                    ties = [x.get("type") for x in e.findall("tie")]
                    if "stop" in ties and midi in ligada:           # alarga la nota ligada
                        j = ligada.pop(midi)
                        c, i0, d0, ms = ev[j]
                        ev[j] = (c, i0, d0 + d, ms)
                        if "start" in ties:
                            ligada[midi] = j
                        continue
                    if acorde and ev and abs(ev[-1][1] - ini) < 1e-6 and ev[-1][0] == num:
                        ev[-1][3].append(midi)
                    else:
                        ev.append((num, ini, d, [midi]))
                    if "start" in ties:
                        ligada[midi] = len(ev) - 1
            if num == 1 and m.get("implicit") == "yes":
                anacrusa = largo
            inicio_compas += largo if largo > 0 else 4.0
        partes[p.get("id")] = (nombres.get(p.get("id"), p.get("id")), ev)
    # con anacrusa, el 0 es el compás 1 de verdad: la anacrusa queda en negativo
    if anacrusa:
        partes = {k: (n, [(c - 1, i - anacrusa, d, ms) for c, i, d, ms in ev]) for k, (n, ev) in partes.items()}
        viejos = dict(INICIOS); INICIOS.clear()
        INICIOS.update({c - 1: q - anacrusa for c, q in viejos.items()})
    return partes


def donde(q):
    """negra q → (compás de la partitura, tiempo dentro del compás)"""
    c = max([c for c, i in INICIOS.items() if i <= q + 1e-9] or [min(INICIOS)])
    return c, 1 + q - INICIOS[c]


def reloj(pulsos, compas):
    """negras desde el compás 1 de la partitura → segundo del disco (interpolando entre pulsos)."""
    i0 = next(i for i, p in enumerate(pulsos) if p["compas"] == compas and p["tiempo"] == 1)
    seg = np.array([p["seg"] for p in pulsos], float)
    def f(q):                                     # q puede ser negativo (anacrusa: antes del compás 1)
        q = np.asarray(q, float) + i0
        k = np.clip(np.floor(q).astype(int), 0, len(seg) - 2)
        return seg[k] + (q - k) * (seg[k + 1] - seg[k])
    return f


def pitch_track(y, sr):
    f, v, _ = librosa.pyin(y, fmin=librosa.note_to_hz("A2"), fmax=librosa.note_to_hz("C6"), sr=sr,
                           frame_length=2048, hop_length=HOP)
    m = librosa.hz_to_midi(np.where(v, f, np.nan))
    m[m < librosa.note_to_midi("B2")] = np.nan      # pegado al límite de abajo = ruido (salía «do3» en los silencios)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("partitura"); ap.add_argument("carpeta")
    ap.add_argument("--compas", type=int, required=True)
    ap.add_argument("--melodia"); ap.add_argument("--informe")
    a = ap.parse_args()

    out = []
    def di(s=""):
        print(s); out.append(s)

    rj = json.load(open(os.path.join(a.carpeta, "ritmo.json"), encoding="utf-8"))
    audio = rj["meta"]["audio"]
    cancion = rj["meta"]["cancion"]
    dirpistas = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(a.carpeta))), "_datos", cancion, "pistas")
    partes = notas_de(leer_xml(a.partitura))
    pm = a.melodia or list(partes)[0]
    nom_mel, mel = partes[pm]
    T = reloj(rj["pulsos"], a.compas)
    fin_q = max(i + d for _, ev in partes.values() for _, i, d, _ in ev) if mel else 0
    ini_q = min(0.0, min(i for _, ev in partes.values() for _, i, _, _ in ev))
    t0, t1 = float(T(ini_q)) - 1.0, float(T(fin_q)) + 1.0
    di(f"COMPROBAR TROZO · {os.path.basename(a.partitura)} contra «{cancion}»")
    di(f"compás 1 de la partitura = compás {a.compas} del disco = {float(T(0)):.3f} s · acaba en {float(T(fin_q)):.3f} s")

    # audio: mezcla + pistas
    fuentes = {"mezcla": audio}
    if os.path.isdir(dirpistas):
        for n in ("bandoneones", "resto", "violines", "piano"):
            pth = os.path.join(dirpistas, n + ".flac")
            if os.path.exists(pth):
                fuentes[n] = pth
    pist = {}
    for n, pth in fuentes.items():
        y, sr = librosa.load(pth, sr=SR, mono=True, offset=t0, duration=t1 - t0)
        pist[n] = (y, pitch_track(y, sr))
    tt = librosa.times_like(pist["mezcla"][1], sr=SR, hop_length=HOP) + t0

    # 1. afinación
    m = pist["mezcla"][1]; mm = m[~np.isnan(m)]
    desaf = float(np.median(((mm - np.round(mm)) + 0.5) % 1 - 0.5)) if len(mm) else 0.0
    di(f"afinación del disco en el trozo: {desaf * 100:+.0f} cents (corregida)")
    for n in pist:
        pist[n] = (pist[n][0], pist[n][1] - desaf)

    def altura(track, s, e):
        k = (tt >= s) & (tt < e)
        v = track[k]; v = v[~np.isnan(v)]
        if len(v) < 3:
            return None, 0.0
        r = np.round(v)
        vals, cnt = np.unique(r % 12, return_counts=True)
        pc = vals[np.argmax(cnt)]
        oct_ = np.median(r[r % 12 == pc])
        return float(oct_), float(cnt.max() / k.sum())

    def acierto(desp_q=0.0, transp=0, fuente="mejor"):
        bien, total = 0, 0
        for c, i, d, ms in mel:
            s, e = float(T(i + desp_q)), float(T(i + d + desp_q))
            s2, e2 = s + 0.2 * (e - s), e - 0.2 * (e - s)
            esc = (ms[-1] + transp) % 12
            total += 1
            srcs = list(pist) if fuente == "mejor" else [fuente]
            if any((h := altura(pist[n][1], s2, e2)[0]) is not None and int(h) % 12 == esc for n in srcs):
                bien += 1
        return bien, total

    # 2. melodía nota a nota
    di(""); di(f"MELODÍA · {nom_mel} ({len(mel)} notas). Por nota: lo escrito → lo que suena en cada pista (% del tiempo de la nota)")
    di("  y el ataque: cuándo empieza a sonar esa altura en el disco respecto a lo escrito (+ = tarde).")
    ataques = []
    for c, i, d, ms in mel:
        s, e = float(T(i)), float(T(i + d))
        s2, e2 = s + 0.2 * (e - s), e - 0.2 * (e - s)
        esc = ms[-1]
        res, ok = [], False
        for n in pist:
            h, frac = altura(pist[n][1], s2, e2)
            if h is None:
                res.append(f"{n[:4]} ·"); continue
            igual = int(h) % 12 == esc % 12
            ok |= igual
            res.append(f"{n[:4]} {nombre(h)}{'✓' if igual else '✗'}{frac * 100:3.0f}%")
        # ataque: primer cuadro en ±250 ms (sobre la mezcla y la mejor pista) con esa altura
        mejor = None
        for n in pist:
            tr = pist[n][1]
            k = np.where((tt > s - 0.25) & (tt < s + 0.25))[0]
            hit = [j for j in k if not np.isnan(tr[j]) and int(np.round(tr[j])) % 12 == esc % 12
                   and (j == 0 or np.isnan(tr[j - 1]) or int(np.round(tr[j - 1])) % 12 != esc % 12)]
            if hit:
                dt = min((tt[j] - s for j in hit), key=abs)
                if mejor is None or abs(dt) < abs(mejor):
                    mejor = dt
        if mejor is not None:
            ataques.append(mejor)
        c, tpo = donde(i)
        di(f"  c{c} t{tpo:<5.4g} {nombre(esc):5s} {'BIEN' if ok else 'NO  '} "
           f"ataque {'   ?  ' if mejor is None else f'{mejor * 1000:+5.0f} ms'} · " + " · ".join(res))
    b, tot = acierto()
    di(f"  → notas que suenan como están escritas (en alguna pista): {b} de {tot} ({100 * b / max(tot, 1):.0f} %)")
    if ataques:
        ar = np.array(ataques)
        di(f"  → ataques: mediana {np.median(ar) * 1000:+.0f} ms · a ±60 ms: {np.mean(np.abs(ar) < 0.06) * 100:.0f} % "
           f"· a ±120 ms: {np.mean(np.abs(ar) < 0.12) * 100:.0f} %")

    # 2b. silencios de la melodía: ¿suena algo con altura clara?
    huecos, q = [], ini_q
    for c, i, d, ms in sorted(mel, key=lambda x: x[1]):
        if i - q >= 0.5:
            huecos.append((q, i))
        q = max(q, i + d)
    if fin_q - q >= 0.5:
        huecos.append((q, fin_q))
    di(""); di("SILENCIOS DE LA MELODÍA: ¿suena ahí una altura clara en el disco? (por corchea, nota más repetida)")
    for h0, h1 in huecos:
        trozos = []
        for x in np.arange(h0, h1 - 0.01, 0.5):
            s, e = float(T(x)), float(T(x + 0.5))
            mejor = None
            for n in pist:
                h, frac = altura(pist[n][1], s, e)
                if h is not None and frac >= 0.6 and (mejor is None or frac > mejor[1]):
                    mejor = (h, frac, n)
            c, tp = donde(x)
            trozos.append(f"c{c}t{tp:g} " + ("·" if mejor is None else f"{nombre(mejor[0])}({mejor[2][:4]})"))
        di("  " + " | ".join(trozos))

    # 3. al azar
    di(""); di("AL AZAR (¿gana lo escrito?): % de notas que suenan como escritas")
    pruebas = [("tal cual", 0, 0), ("corrida +1 corchea", 0.5, 0), ("corrida −1 corchea", -0.5, 0),
               ("corrida +1 tiempo", 1, 0), ("corrida −1 tiempo", -1, 0), ("+1 semitono", 0, 1), ("−1 semitono", 0, -1)]
    for txt, dq, tr in pruebas:
        b, tot = acierto(dq, tr)
        di(f"  {txt:20s} {100 * b / max(tot, 1):4.0f} %")

    # 4. acordes
    yb = pist["mezcla"][0]
    ch = librosa.feature.chroma_cqt(y=yb, sr=SR, hop_length=HOP, fmin=librosa.note_to_hz("C2"), n_octaves=6,
                                    tuning=desaf)
    tch = librosa.times_like(ch, sr=SR, hop_length=HOP) + t0
    plantillas = {}
    for r in range(12):
        for tipo, iv in (("", (0, 4, 7)), ("m", (0, 3, 7)), ("7", (0, 4, 7, 10))):
            v = np.zeros(12); v[[(r + x) % 12 for x in iv]] = 1
            plantillas[NOMBRES[r].capitalize() + tipo] = v / np.linalg.norm(v)
    for pid, (nom, ev) in partes.items():
        if pid == pm:
            continue
        di(""); di(f"ACORDES · {nom}")
        for c, i, d, ms in ev:
            s, e = float(T(i)), float(T(i + max(d, 1.0)))
            k = (tch >= s) & (tch < e)
            v = ch[:, k].mean(1); v = v / (np.linalg.norm(v) + 1e-9)
            punt = sorted(((float(v @ p), n) for n, p in plantillas.items()), reverse=True)
            esc = "-".join(nombre(x) for x in ms)
            pcs = sorted({x % 12 for x in ms})
            pe = np.zeros(12); pe[pcs] = 1; pe /= np.linalg.norm(pe)
            pos = 1 + [n for _, n in punt].index(punt[0][1])
            fuertes = " ".join(f"{NOMBRES[j]}" for j in np.argsort(v)[::-1][:4])
            di(f"  c{c} t{donde(i)[1]:g}: escrito {esc} (encaja {float(v @ pe):.2f}) · el disco: "
               + ", ".join(f"{n} {p:.2f}" for p, n in punt[:3]) + f" · notas más fuertes: {fuertes}")

    # 5. golpes
    on = librosa.onset.onset_detect(y=yb, sr=SR, hop_length=HOP, units="time", backtrack=False) + t0
    env = librosa.onset.onset_strength(y=yb, sr=SR, hop_length=HOP)
    tenv = librosa.times_like(env, sr=SR, hop_length=HOP) + t0
    fuerza = {float(o): float(env[np.argmin(np.abs(tenv - o))]) for o in on}
    escritos = sorted({float(T(i)) for _, ev in partes.values() for _, i, _, _ in ev})
    umbral = np.percentile(list(fuerza.values()), 80) if fuerza else 0
    di(""); di("GOLPES FUERTES DEL DISCO SIN NADA ESCRITO (dentro del trozo, el 20 % más fuerte):")
    nada = True
    for o, fz in fuerza.items():
        if T(ini_q) - 0.1 <= o <= T(fin_q) and fz >= umbral and min(abs(o - x) for x in escritos) > 0.12:
            q = None
            # en qué compás/tiempo cae
            qs = np.linspace(ini_q, fin_q, int((fin_q - ini_q) * 8) + 1)
            q = qs[np.argmin(np.abs(T(qs) - o))]
            c, tp = donde(q)
            di(f"  {o:7.2f} s · compás {c} tiempo {tp:g} · fuerza {fz:.1f}")
            nada = False
    if nada:
        di("  ninguno")

    if a.informe:
        open(a.informe, "w", encoding="utf-8").write("\n".join(out) + "\n")
        print("Informe:", a.informe)


if __name__ == "__main__":
    main()
