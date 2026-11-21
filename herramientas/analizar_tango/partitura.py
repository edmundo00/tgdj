r"""Partitura en la página de ritmo: cuadra los compases de una partitura MusicXML con los segundos de la grabación.

Uso:  python partitura.py "<carpeta de _ritmo\canción>" "<partitura.mxl>"     (la primera vez: dice qué partitura es)
      python partitura.py "<carpeta de _ritmo\canción>"                        (rehace con la partitura ya apuntada)
      python partitura.py --todas                                              (rehace todas las que tengan partitura)
Opciones: --ancla 5=17.52   el compás 5 de la partitura empieza en el segundo 17,52 (puesto de oído; se pueden poner
                              varias y se guardan en partitura.json). Salen solas de la página: botón «el compás
                              marcado empieza aquí» → texto ANCLAS que Edmundo pega en el chat.
          --sin-anclas        borra las anclas guardadas.

Deja en la carpeta de la canción:
  partitura.json      qué partitura es y las anclas (lo lee también ritmo.py para rehacerla sola tras analizar)
  partitura_datos.js  la partitura (MusicXML) + la tabla compás → segundo. La página ritmo.html la carga sola
                      (con <script>, sin servidor) y muestra el panel «Partitura» solo si existe.
  partitura.txt       la tabla en texto y cuánto se fía de cada compás.

Cómo cuadra (19-11-2026, probado con «El Huracán» de Donato):
1. Lee la partitura (zipfile + xml, Python estándar): compases, y notas de cada parte con su tiempo en negras.
2. Rejilla de pulsos de ritmo.py, arreglada: donde cuenta a medio tiempo mete el pulso del medio, y la alarga
   hasta el principio y el final (Beat This! a veces empieza tarde).
3. Tiempo a tiempo (como comprobar_con_midi.py --alinear-con): notas que EMPIEZAN en cada negra de la partitura
   contra lo que suena al empezar cada pulso, en la mezcla y en las pistas separadas de contrabajo y piano.
4. Compás a compás: cada compás empieza en un pulso y lo normal es que dure lo escrito (4 tiempos en 4/4);
   cada tiempo de más o de menos se paga. Probado: el emparejamiento libre (DTW) daba compases de 0,9 a 3,7 s;
   así salen todos de ~1,84 s y donde la partitura no sigue al disco no se pierde.
5. Comprueba con la pista de contrabajo: ¿suena la nota escrita? (y lo mismo corrido 2 tiempos, «al azar»).
"""
import os, sys, json, glob, zipfile, unicodedata
import xml.etree.ElementTree as ET
from fractions import Fraction
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = r"D:\Dropbox\TDJ\Analisis tangos"
SR = 22050
PENAL = 0.35       # lo que se paga por cada tiempo de más o de menos en un compás (cuadre compás a compás)
SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


# ---------------------------------------------------------------- leer la partitura
def xml_de(ruta):
    """Texto MusicXML de un .mxl (zip) o .musicxml/.xml."""
    if ruta.lower().endswith(".mxl"):
        with zipfile.ZipFile(ruta) as z:
            nombre = None
            if "META-INF/container.xml" in z.namelist():
                rf = ET.fromstring(z.read("META-INF/container.xml")).find(".//{*}rootfile")
                nombre = rf.get("full-path") if rf is not None else None
            nombre = nombre or next(n for n in z.namelist() if n.endswith((".xml", ".musicxml")) and "META-INF" not in n)
            return z.read(nombre).decode("utf-8")
    return open(ruta, encoding="utf-8").read()


def sin_ns(raiz):
    for e in raiz.iter():
        if isinstance(e.tag, str) and "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]
    return raiz


def normal(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def grupo_de(nombre):
    """A qué grupo de la página pertenece una parte (para «qué partes se ven»)."""
    n = normal(nombre)
    if "bandon" in n: return "bandoneones"
    if "piano" in n: return "piano"
    if any(s in n for s in ("contrab", "bass", "bajo")): return "contrabajo"
    if any(s in n for s in ("viol", "viola", "cello", "chelo", "string", "cuerda")): return "cuerdas"
    if any(s in n for s in ("voz", "voice", "canto", "vocal")): return "voz"
    return "otros"


def leer_partitura(ruta):
    """Devuelve (xml, partes, compases, notas).
    compases = [{n: número escrito, q0: inicio en negras, q: largo en negras}] (orden de la partitura, sin repetir);
    notas = [(q_inicio, midi, parte_índice)]."""
    xml = xml_de(ruta)
    raiz = sin_ns(ET.fromstring(xml.encode("utf-8")))
    nombres = {sp.get("id"): (sp.findtext("part-name") or sp.get("id")).strip() for sp in raiz.iter("score-part")}
    partes, notas, compases = [], [], None
    for ip, part in enumerate(raiz.findall("part")):
        nombre = nombres.get(part.get("id"), part.get("id"))
        partes.append(dict(id=part.get("id"), nombre=nombre, grupo=grupo_de(nombre)))
        div, largo, q0 = 1, Fraction(4), Fraction(0)
        mios = []
        for m in part.findall("measure"):
            pos = Fraction(0); maxpos = Fraction(0); ultimo = Fraction(0)
            for e in m:
                if e.tag == "attributes":
                    if e.findtext("divisions"): div = int(e.findtext("divisions"))
                    t = e.find("time")
                    if t is not None and t.findtext("beats"):
                        try:
                            largo = Fraction(sum(int(x) for x in t.findtext("beats").split("+"))) * 4 / int(t.findtext("beat-type"))
                        except ValueError:
                            pass
                elif e.tag == "backup":
                    pos -= Fraction(int(e.findtext("duration") or 0), div)
                elif e.tag == "forward":
                    pos += Fraction(int(e.findtext("duration") or 0), div); maxpos = max(maxpos, pos)
                elif e.tag == "note":
                    if e.find("grace") is not None:
                        continue
                    dur = Fraction(int(e.findtext("duration") or 0), div)
                    inicio = ultimo if e.find("chord") is not None else pos
                    if e.find("chord") is None:
                        ultimo = pos; pos += dur; maxpos = max(maxpos, pos)
                    p = e.find("pitch")
                    ligada = any(t.get("type") == "stop" for t in e.findall("tie"))
                    if p is not None and not ligada:
                        midi = 12 * (int(p.findtext("octave")) + 1) + SEMI[p.findtext("step")] + int(float(p.findtext("alter") or 0))
                        notas.append((float(q0 + inicio), midi, ip))
            n = m.get("number", str(len(mios) + 1))
            # el largo escrito por el compás manda; un compás de anacrusa (implicit) usa lo que trae
            q = maxpos if (m.get("implicit") == "yes" and maxpos > 0) else largo
            mios.append(dict(n=n, q0=float(q0), q=float(q)))
            q0 += q
        if compases is None or len(mios) > len(compases):
            compases = mios
    return xml, partes, compases, sorted(notas)


# ---------------------------------------------------------------- cuadrar con la grabación
def rejilla_completa(pulsos, dur):
    """Pulsos de ritmo.py arreglados: donde cuenta a medio tiempo (hueco ≈ doble) mete el del medio, y alarga
    la rejilla hasta el principio y el final de la grabación (Beat This! a veces empieza tarde)."""
    pb = np.array(sorted(pulsos), float)
    med = float(np.median(np.diff(pb)))
    out = [pb[0]]
    for a, b in zip(pb[:-1], pb[1:]):
        n = int(round((b - a) / med))
        for k in range(1, max(n, 1)):
            out.append(a + (b - a) * k / n)
        out.append(b)
    pb = np.array(out)
    med = float(np.median(np.diff(pb)))
    antes = np.arange(pb[0] - med, -0.01, -med)[::-1]
    despues = np.arange(pb[-1] + med, dur, med)
    return np.concatenate([antes, pb, despues]), med


def alinear(notas, partes, compases, audio, pistas, pulsos, anclas=None):
    """Como comprobar_con_midi.py --alinear-con: tiempo a tiempo. Cada tiempo (negra) de la partitura → un pulso
    de la grabación, comparando las notas que EMPIEZAN en ese tiempo con lo que suena al empezar el pulso,
    en la mezcla y en las pistas separadas de contrabajo y piano. Luego, compás a compás (ver abajo).
    anclas = {índice de compás: segundo} puestas a mano (de oído en la página): el compás empieza ahí sí o sí."""
    import librosa
    y, _ = librosa.load(audio, sr=SR, mono=True)
    afin = float(librosa.estimate_tuning(y=y, sr=SR))
    pb, med = rejilla_completa(pulsos, len(y) / SR)
    q_total = compases[-1]["q0"] + compases[-1]["q"]
    # ¿el tiempo de la partitura es la negra del pulso, o está escrita al doble / a la mitad?
    dur_musica = pb[-1] - pb[0]
    factor = min((1, 2, 0.5), key=lambda x: abs(np.log(q_total * x * med / dur_musica)))
    if factor != 1:
        notas = [(q * factor, m, ip) for q, m, ip in notas]
        compases = [dict(c, q0=c["q0"] * factor, q=c["q"] * factor) for c in compases]
        q_total *= factor
    nq = int(np.ceil(q_total))
    grupos = {p["grupo"] for p in partes}
    usar = [(audio, None)] + [(pistas[g], {g}) for g in ("contrabajo", "piano") if g in pistas and g in grupos]
    bloquesA, bloquesM = [], []
    for ruta, quien in usar:
        yy = y if ruta == audio else librosa.load(ruta, sr=SR, mono=True)[0]
        Cq = np.abs(librosa.cqt(yy, sr=SR, hop_length=256, fmin=librosa.note_to_hz("C1"), n_bins=84, tuning=afin))
        A = np.zeros((12, len(pb)))
        for j, t in enumerate(pb):
            f = int((t + 0.02) * SR / 256)
            A[:, j] = Cq[:, f:f + 8].mean(1).reshape(7, 12).sum(0) if f + 8 < Cq.shape[1] else 0
        A /= np.linalg.norm(A, axis=0) + 1e-9
        M = np.zeros((12, nq))
        for q, midi, ip in notas:
            if quien and partes[ip]["grupo"] not in quien:
                continue
            i = int(round(q))
            if abs(q - i) <= 0.26 and i < nq:
                M[midi % 12, i] += 1
        llenos = np.linalg.norm(M, axis=0) > 0
        M[:, llenos] /= np.linalg.norm(M[:, llenos], axis=0)
        Cm = 1 - M.T @ A
        Cm[~llenos, :] = 0.5     # tiempos sin nota: ni ayudan ni estorban
        bloquesA.append(Cm)
    C = np.mean(bloquesA, axis=0)
    # compás a compás: cada compás de la partitura empieza en un pulso; lo normal es que dure lo escrito
    # (4 tiempos en 4/4) y cada tiempo de más o de menos se paga (PENAL). Así no se vuelve loco donde
    # la partitura no sigue al disco: sigue al pulso hasta que vuelve a cuadrar.
    nM, nP = len(compases), len(pb)
    largos = [max(1, int(round(c["q"]))) for c in compases]
    Cpad = np.hstack([C, np.full((C.shape[0], 16), 0.6)])
    def encaje(m):
        q0 = int(round(compases[m]["q0"]))
        return np.array([sum(Cpad[min(q0 + k, C.shape[0] - 1), j + k] for k in range(largos[m])) for j in range(nP)]) / largos[m]
    E = np.array([encaje(m) for m in range(nM)])          # coste medio por tiempo de poner el compás m en el pulso j
    INF = 1e9
    D = np.full((nM, nP), INF); B = np.zeros((nM, nP), int)
    fijo = {}
    for m, t in (anclas or {}).items():
        if 0 <= m < nM:
            fijo[m] = int(np.argmin(np.abs(pb - t)))
    def anclar(m):
        if m in fijo:
            v = np.full(nP, INF); v[fijo[m]] = D[m, fijo[m]]; D[m] = v
    D[0] = E[0]; anclar(0)
    for m in range(1, nM):
        L = largos[m - 1]
        for d in range(1, 2 * L + 2):
            pen = PENAL * abs(d - L) ** 1.5
            cand = np.full(nP, INF); cand[d:] = D[m - 1, :-d] + pen
            mejor = cand < D[m]
            D[m][mejor] = cand[mejor]; B[m][mejor] = d
        D[m] += E[m]
        anclar(m)
    j = int(np.argmin(D[-1])); ruta = [j]
    for m in range(nM - 1, 0, -1):
        j -= B[m, j]; ruta.append(j)
    ruta = ruta[::-1]
    jf = ruta[-1] + largos[-1]
    t0 = np.array([pb[j] for j in ruta] + [pb[jf] if jf < nP else pb[-1] + (jf - nP + 1) * med])
    coste = [float(E[m, ruta[m]]) for m in range(nM)]
    return t0, coste, afin, factor


# ---------------------------------------------------------------- comprobar con la pista de contrabajo
def acierto_bajo(notas, partes, compases, t0, ruta_bajo, afin):
    """Por compás: ¿la nota más fuerte de la pista de contrabajo al empezar cada nota escrita del contrabajo es la escrita?"""
    import librosa
    if not ruta_bajo or not os.path.exists(ruta_bajo):
        return None
    yb, _ = librosa.load(ruta_bajo, sr=SR, mono=True)
    Cb = np.abs(librosa.cqt(yb, sr=SR, hop_length=256, fmin=librosa.note_to_hz("E1"), n_bins=48, tuning=afin))
    umbral = np.percentile(Cb, 60)
    q0s = np.array([c["q0"] for c in compases] + [compases[-1]["q0"] + compases[-1]["q"]])

    def seg(q):
        return float(np.interp(q, q0s, t0))
    res = []
    for i, c in enumerate(compases):
        ok = tot = 0
        for q, midi, ip in notas:
            if partes[ip]["grupo"] != "contrabajo" or not (c["q0"] <= q < c["q0"] + c["q"]):
                continue
            f = int((seg(q) + 0.04) * SR / 256)
            if f + 6 >= Cb.shape[1]:
                continue
            spec = Cb[:, f:f + 6].mean(1)
            if spec.max() < umbral:
                continue
            tot += 1
            ok += (np.argmax(spec) + librosa.note_to_midi("E1")) % 12 == midi % 12
        res.append((int(ok), int(tot)))
    return res


# ---------------------------------------------------------------- todo junto
def pistas_de(nombre):
    import pagina_ritmo
    return pagina_ritmo.pistas_de(RAIZ, nombre)


def audio_de(a):
    for r in (a, os.path.join(r"D:\Dropbox\TDJ\MUSICA", a), os.path.join(r"D:\Dropbox\TDJ", a)):
        if r and os.path.exists(r):
            return r
    return None


def ruta_partitura(p):
    for r in (p, os.path.join(r"D:\Dropbox\TDJ\Partituras\convertidas", p), os.path.join(r"D:\Dropbox\TDJ", p)):
        if r and os.path.exists(r):
            return os.path.abspath(r)
    return None


def hacer(carpeta, mxl=None, anclas=None, sin_anclas=False):
    carpeta = os.path.abspath(carpeta.rstrip("\\/"))
    fj = os.path.join(carpeta, "partitura.json")
    conf = json.load(open(fj, encoding="utf-8")) if os.path.exists(fj) else {}
    if mxl:
        conf["partitura"] = mxl
    if sin_anclas:
        conf.pop("anclas", None)
    if anclas:
        conf.setdefault("anclas", {}).update(anclas)
    if not conf.get("partitura"):
        raise SystemExit("Falta la partitura: python partitura.py \"<carpeta>\" \"<x.mxl>\"")
    ruta = ruta_partitura(conf["partitura"])
    if not ruta:
        raise SystemExit(f"No encuentro la partitura: {conf['partitura']}")
    R = json.load(open(os.path.join(carpeta, "ritmo.json"), encoding="utf-8"))
    audio = audio_de(R["meta"]["audio"])
    if not audio:
        raise SystemExit(f"No encuentro el audio: {R['meta']['audio']}")
    print("Partitura:", ruta, flush=True)
    xml, partes, compases, notas = leer_partitura(ruta)
    print(f"  {len(partes)} partes · {len(compases)} compases · {len(notas)} notas", flush=True)
    pistas = pistas_de(R["meta"]["cancion"])
    pulsos = [p["seg"] for p in R["pulsos"]]
    print(f"Cuadrando con la grabación (pistas separadas: {', '.join(pistas) or 'no'})…", flush=True)
    numero = {c["n"]: i for i, c in enumerate(compases)}
    anc = {numero[n]: t for n, t in conf.get("anclas", {}).items() if n in numero}
    if anc:
        print("  anclas puestas a mano (compás = segundo): " + ", ".join(f"{n}={t}" for n, t in conf["anclas"].items()))
    t0, coste, afin, factor = alinear(notas, partes, compases, audio, pistas, pulsos, anc)
    bajo = acierto_bajo(notas, partes, compases, t0, pistas.get("contrabajo"), afin)
    # al azar: lo mismo corrido 2 tiempos (si el bajo no lo supera claramente, el cuadre no vale)
    med = float(np.median(np.diff(t0))) / 4
    azar = acierto_bajo(notas, partes, compases, t0 + 2 * med, pistas.get("contrabajo"), afin)
    if azar:
        print(f"  al azar (corrido 2 tiempos): {sum(b[0] for b in azar) / max(sum(b[1] for b in azar), 1):.0%}")
    tabla = []
    for i, c in enumerate(compases):
        fila = dict(n=c["n"], i=i, t=round(float(t0[i]), 3), fin=round(float(t0[i + 1]), 3), coste=round(coste[i], 3))
        if bajo and bajo[i][1]:
            fila["bajo"] = [bajo[i][0], bajo[i][1]]
        tabla.append(fila)
    # quitar espacios de sangría del XML (más pequeño)
    import re
    xml_corto = re.sub(r">\s+<", "><", xml)
    datos = dict(partitura=os.path.basename(ruta), ruta=ruta, partes=partes, compases=tabla, xml=xml_corto,
                 afinacion=round(afin, 2))
    import pagina_ritmo
    pagina_ritmo.escribir_js(os.path.join(carpeta, "partitura_datos.js"), "PARTITURA", datos)
    conf["hecho"] = __import__("time").strftime("%Y-%m-%d %H:%M")
    json.dump(conf, open(fj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # texto
    L = [f"PARTITURA · {R['meta']['cancion']}", f"Partitura: {ruta}",
         f"{len(partes)} partes: " + ", ".join(p["nombre"] for p in partes),
         f"Compases: {len(compases)}" + ("" if factor == 1 else f" · la partitura va escrita a x{factor} del pulso"),
         "Anclas a mano (compás = segundo): " + (", ".join(f"{n}={t}" for n, t in conf.get("anclas", {}).items()) or "ninguna"),
         f"Afinación del disco: {afin:+.2f} semitonos", "",
         "Coste: 0 = la partitura cuadra perfecto con lo que suena, 1 = nada que ver (> 0,7: dudoso).",
         "Bajo: notas del contrabajo escritas que suenan en la pista separada (al azar sale ~20 %).", "",
         "compás  empieza   dura   coste   bajo"]
    for f in tabla:
        b = f"{f['bajo'][0]}/{f['bajo'][1]}" if "bajo" in f else ""
        L.append(f"{f['n']:>6} {f['t']:8.2f}s {f['fin'] - f['t']:5.2f}s  {f['coste']:5.2f}   {b}")
    if bajo:
        ok = sum(b[0] for b in bajo); tot = sum(b[1] for b in bajo)
        L.insert(5, f"Notas del bajo que suenan: {ok}/{tot} = {ok / max(tot, 1):.0%}")
        print(f"  notas del bajo que suenan: {ok / max(tot, 1):.0%} de {tot}")
    open(os.path.join(carpeta, "partitura.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"  compás 1 en {t0[0]:.2f} s · último acaba en {t0[-1]:.2f} s · coste medio {np.mean(coste):.2f}")
    print("Hecho:", os.path.join(carpeta, "partitura_datos.js"))
    return datos


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe") and r"C:\ffmpeg\bin" not in os.environ["PATH"]:
        os.environ["PATH"] = r"C:\ffmpeg\bin;" + os.environ["PATH"]
    sys.path.insert(0, AQUI)
    a = sys.argv[1:]
    anclas = {}
    while "--ancla" in a:         # --ancla 5=17.52  (el compás 5 empieza en el segundo 17,52)
        i = a.index("--ancla"); n, t = a[i + 1].split("="); anclas[n.strip()] = float(t.replace(",", ".")); del a[i:i + 2]
    sin = "--sin-anclas" in a
    if sin:
        a.remove("--sin-anclas")
    if a and a[0] == "--todas":
        for fj in glob.glob(os.path.join(RAIZ, "_ritmo", "*", "partitura.json")):
            hacer(os.path.dirname(fj))
    else:
        hacer(a[0], a[1] if len(a) > 1 else None, anclas, sin)
