"""Partitura de piano escaneada (jpg dentro de un .zip/.rar, o imágenes sueltas) → MusicXML + MIDI. APROXIMADA.

Uso:  python piano_escaneado.py <archivo.zip|.rar|carpeta> [más…] --nombre "Bélgica"

Qué hace (lo aprendido con «Bélgica», 19-11-2026):
  1. Saca las páginas del .zip/.rar con 7-Zip (la conversión grande perdía las tildes de los nombres: «B�lgica»).
  2. Las prepara: gris, más contraste y agrandadas a ~300 ppp (los escaneos vienen a 150: Audiveris no los lee).
  3. Las lee TODAS juntas con Audiveris (un solo PDF), para que salga una sola partitura con todas las páginas.
     La portada (página 1 con dibujo) no tiene música: Audiveris la deja de lado.
  4. Arregla lo que Audiveris lee mal en los escaneos: armaduras que cambian sin motivo (se rehacen las
     alteraciones), compás (el que MIDEN los compases), pentagramas fantasma, tempos absurdos, compases que no miden
     lo que deben («compás recortado») y lo que MuseScore no abre («compás quitado»).
Deja en Partituras\\convertidas\\piano\\:  X_piano.mxl + .mid + .txt (informe) + X_original.pdf (las páginas
escaneadas, para comparar). Es APROXIMADA: los escaneos de piano salen peor que los PDF hechos con ordenador.
"""
import copy
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convertir_partituras import AUDIVERIS  # noqa: E402
from cuadrar_partes import (Copia, compas_escrito, leer_mxl, nombre_limpio, terminar, clave_orden,  # noqa: E402
                            PASOS, SOSTENIDOS, BEMOLES, ACCIDENTE, TEMPO, tempo_de_textos)

SIETE = Path(r"C:\Program Files\7-Zip\7z.exe")
SALIDA = Path(r"D:\Dropbox\TDJ\Partituras\convertidas\piano")
IMAGENES = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif")
BAJA = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
OCULTA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def orden_natural(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def sacar_paginas(origen: Path, tmp: Path):
    """Imágenes de un .zip/.rar (con 7-Zip) o de una carpeta, en orden de página."""
    if origen.is_dir():
        return sorted((p for p in origen.iterdir() if p.suffix.lower() in IMAGENES), key=orden_natural)
    destino = tmp / ("z_" + origen.stem)
    destino.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(SIETE), "e", "-y", f"-o{destino}", str(origen)], capture_output=True, creationflags=OCULTA)
    return sorted((p for p in destino.rglob("*") if p.suffix.lower() in IMAGENES), key=orden_natural)


def tiene_pentagramas(img: Path) -> bool:
    """¿Hay pentagramas? (filas casi enteras de negro, en grupos de 5). La portada o la página de la letra, no:
    y si se le pasa a Audiveris una página sin pentagramas, no exporta NADA del libro."""
    from PIL import Image
    im = Image.open(img).convert("L")
    im = im.resize((800, round(im.height * 800 / im.width)))
    ancho, alto = im.size
    px = im.load()
    # en 4 franjas verticales por separado: si el escaneo está algo torcido, una línea entera no cae en una sola fila
    mejor = 0
    for k in range(4):
        x0, x1 = ancho * k // 4, ancho * (k + 1) // 4
        filas = [sum(1 for x in range(x0, x1) if px[x, y] < 150) / (x1 - x0) > 0.6 for y in range(alto)]
        lineas, y = 0, 0
        while y < alto:           # líneas = tramos seguidos de filas negras
            if filas[y]:
                lineas += 1
                while y < alto and filas[y]:
                    y += 1
            y += 1
        mejor = max(mejor, lineas)
    return mejor >= 10


MODOS = ["3300", "x2", "x1.5", "x2_bn"]   # si una página no sale, se reintenta con el siguiente (María, pág. 3)


def preparar(img: Path, tmp: Path, k: int, modo: str = "3300") -> Path:
    from PIL import Image, ImageOps
    im = Image.open(img)
    im = ImageOps.exif_transpose(im).convert("L")
    if modo == "3300":
        f = 3300 / im.height if im.height < 3000 else 1
    elif modo == "x1.5":
        f = 1.5 if im.height < 3000 else 1
    else:
        f = 2 if im.height < 3000 else 1
    if f != 1:
        im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=1)
    if modo == "x2_bn":
        im = im.point(lambda p: 255 if p > 170 else 0)
    out = tmp / f"p{k:03d}_{modo.replace('.', '')}.png"
    im.save(out, dpi=(300, 300))
    return out


def audiveris(pdf: Path, sal: Path, log: Path):
    env = dict(os.environ, JAVA_TOOL_OPTIONS="-Djava.util.Arrays.useLegacyMergeSort=true",
               TESSDATA_PREFIX=str(Path(__file__).parent / "audiveris" / "tessdata"))
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([str(AUDIVERIS), "-batch", "-export", "-output", str(sal),
                        "-constant", "org.audiveris.omr.Main.sheetStepTimeOut=1200", "--", str(pdf)],
                       stdout=f, stderr=subprocess.STDOUT, env=env, creationflags=BAJA | OCULTA, timeout=3600)


def juntar_trozos(mxls):
    """Audiveris parte el libro en trozos (.mvt2…) cuando cambia algo raro: se pegan seguidos."""
    raiz = leer_mxl(mxls[0])
    for m in mxls[1:]:
        otra = leer_mxl(m)
        for p1, p2 in zip(raiz.findall("part"), otra.findall("part")):
            for c in p2.findall("measure"):
                p1.append(c)
    return raiz


def juntar_paginas(paginas):
    """Pega las páginas leídas una a una. En cada página: el PIANO es la parte de 2 pentagramas (o la de más
    notas) y la VOZ / melodía, la otra de un pentagrama con más notas (si la hay). Lo demás (fantasmas), fuera."""
    def n_notas(p):
        return sum(1 for n in p.iter("note") if n.find("pitch") is not None)

    def repartir(raiz):
        def invisible(p):
            sd = p.find("measure/attributes/staff-details")
            return sd is not None and sd.get("print-object") == "no"
        partes = [p for p in raiz.findall("part") if n_notas(p) > 0 and not invisible(p)] or \
                 [p for p in raiz.findall("part") if n_notas(p) > 0]
        if not partes:
            return None, None
        dos = [p for p in partes if p.find("measure/attributes/staves") is not None]
        piano = max(dos or partes, key=n_notas)
        resto = [p for p in partes if p is not piano and p.find("measure/attributes/staves") is None]
        voz = max(resto, key=n_notas) if resto and n_notas(max(resto, key=n_notas)) >= 0.1 * n_notas(piano) else None
        return piano, voz

    general = ET.Element("score-partwise", version="4.0")
    lista = ET.SubElement(general, "part-list")
    for pid, nombre in (("P1", "Voz / melodía"), ("P2", "Piano")):
        sp = ET.SubElement(lista, "score-part", id=pid)
        ET.SubElement(sp, "part-name").text = nombre
    pv, pp = ET.SubElement(general, "part", id="P1"), ET.SubElement(general, "part", id="P2")
    hay_voz = False
    for raiz in paginas:
        piano, voz = repartir(raiz)
        if piano is None:
            continue
        compases = piano.findall("measure")
        for m in compases:
            pp.append(copy.deepcopy(m))
        vcomp = voz.findall("measure") if voz is not None else []
        hay_voz |= bool(vcomp)
        for i in range(len(compases)):
            pv.append(copy.deepcopy(vcomp[i]) if i < len(vcomp) else ET.Element("measure"))
    if not hay_voz:
        general.remove(pv)
        lista.remove(lista.find("score-part"))
    return general


def elegir_compas(raiz):
    """En los escaneos Audiveris pierde notas y muchos compases miden de menos: el largo más repetido engaña
    («María», un tango, salía 3/4). Se mira también el compás ESCRITO que leyó: si su largo es de los dos más
    repetidos, manda el escrito. Se apunta lo medido en el informe."""
    from fractions import Fraction
    escritos = Counter()
    for t in raiz.iter("time"):
        b, bt = t.findtext("beats"), t.findtext("beat-type")
        if b and bt and b.isdigit() and bt.isdigit() and (int(b), int(bt)) in ((2, 4), (4, 4), (3, 4), (2, 2), (6, 8)):
            escritos[(int(b), int(bt))] += 1
    largos = Counter()
    for parte in raiz.findall("part"):
        div = 1
        for m in parte.findall("measure"):
            for a in m.findall("attributes"):
                if a.findtext("divisions"):
                    div = int(float(a.findtext("divisions"))) or 1
            d = 0
            for e in m:
                if e.tag == "backup":
                    break
                if e.tag in ("note", "forward") and e.find("chord") is None and e.find("grace") is None:
                    d += int(float(e.findtext("duration") or 0))
            if d:
                largos[Fraction(d, div)] += 1
    total = sum(largos.values()) or 1
    print("  compases medidos: " + ", ".join(f"{float(k):g} negras {v / total:.0%}" for k, v in largos.most_common(4))
          + (" · compás escrito: " + ", ".join(f"{b}/{bt}" for (b, bt), _ in escritos.most_common(2)) if escritos else ""))
    arriba = [k for k, _ in largos.most_common(2)]
    eleg = None
    for (b, bt), _ in escritos.most_common():
        if Fraction(4 * b, bt) in arriba:
            eleg = (b, bt)
            break
    if eleg is None:
        eleg = compas_escrito([(None, raiz, None)])
    # calidad de la lectura: cuántos compases medían ya lo que deben (antes de arreglar nada)
    global CALIDAD
    CALIDAD = largos[Fraction(4 * eleg[0], eleg[1])] / total
    return eleg


CALIDAD = 0.0


def nota_calidad():
    if CALIDAD >= 0.6:
        return "buena", "aproximada"
    if CALIDAD >= 0.35:
        return "regular", "aproximada, regular"
    return "MALA", "MAL LEÍDA, no fiarse"


def alteracion_armadura(paso, quintas):
    if quintas > 0 and paso in SOSTENIDOS[:quintas]:
        return 1
    if quintas < 0 and paso in BEMOLES[:-quintas]:
        return -1
    return 0


def arreglar_armaduras(parte: ET.Element, minimo=8):
    """Audiveris lee mal la armadura en algunas líneas del escaneo (cambia y vuelve). Un cambio de tonalidad que dura
    menos de `minimo` compases se toma como mal leído: se quita y se rehacen las alteraciones de las notas que no
    llevan accidente escrito. Devuelve cuántos cambios se quitaron."""
    compases = parte.findall("measure")
    leida = []
    q = 0
    for m in compases:
        k = m.find("attributes/key/fifths")
        if k is not None:
            q = int(k.text)
        leida.append(q)
    # tonalidad buena: los tramos cortos se funden con el anterior
    buena = list(leida)
    i = 0
    while i < len(buena):
        j = i
        while j < len(buena) and leida[j] == leida[i]:
            j += 1
        if i > 0 and j - i < minimo and j < len(buena) + 1:
            for x in range(i, j):
                buena[x] = buena[i - 1]
        i = j
    quitados = sum(1 for i in range(1, len(leida)) if leida[i] != leida[i - 1] and buena[i] == buena[i - 1])
    if not quitados:
        return 0
    anterior = None
    for idx, m in enumerate(compases):
        for a in m.findall("attributes"):
            for k in a.findall("key"):
                a.remove(k)
        if buena[idx] != anterior:
            a = m.find("attributes")
            if a is None:
                a = ET.Element("attributes")
                m.insert(0, a)
            key = ET.Element("key")
            ET.SubElement(key, "fifths").text = str(buena[idx])
            hijos = list(a)
            pos = next((n for n, h in enumerate(hijos) if h.tag not in ("footnote", "level", "divisions")), len(hijos))
            a.insert(pos, key)
            anterior = buena[idx]
        if buena[idx] == leida[idx]:
            continue
        llevadas = {}
        for n in m.findall("note"):
            p = n.find("pitch")
            if p is None:
                continue
            paso, octava = p.findtext("step"), p.findtext("octave")
            acc = ACCIDENTE.get((n.findtext("accidental") or "").strip())
            if acc is not None:
                llevadas[(paso, octava)] = acc
                continue
            alt = llevadas.get((paso, octava), alteracion_armadura(paso, buena[idx]))
            a = p.find("alter")
            if alt:
                if a is None:
                    a = ET.Element("alter")
                    p.insert(1, a)
                a.text = str(alt)
            elif a is not None:
                p.remove(a)
    return quitados


def poner_compas(parte: ET.Element, beats, beat_type):
    compases = parte.findall("measure")
    for i, m in enumerate(compases, 1):
        m.set("number", str(i))
        m.attrib.pop("implicit", None)
        for a in m.findall("attributes"):
            for t in a.findall("time"):
                a.remove(t)
    a = compases[0].find("attributes")
    if a is None:
        a = ET.Element("attributes")
        compases[0].insert(0, a)
    t = ET.Element("time")
    ET.SubElement(t, "beats").text = str(beats)
    ET.SubElement(t, "beat-type").text = str(beat_type)
    hijos = list(a)
    pos = next((i for i, h in enumerate(hijos) if h.tag in ("staves", "part-symbol", "instruments", "clef")), len(hijos))
    a.insert(pos, t)


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help") or "--nombre" not in a:
        print(__doc__)
        return
    titulo = a[a.index("--nombre") + 1]
    origenes = [Path(x) for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--nombre", "--paginas"))]
    SALIDA.mkdir(parents=True, exist_ok=True)
    base = SALIDA / titulo.replace(" ", "_")
    copia = sys.stdout = Copia(sys.stdout)
    print(f"Partitura de piano escaneada → MusicXML (APROXIMADA). Origen:\n  " + "\n  ".join(map(str, origenes)) + "\n")
    tmp = Path(tempfile.mkdtemp(prefix="piano_"))
    try:
        from PIL import Image
        paginas = []
        for o in origenes:
            paginas += sacar_paginas(o, tmp)
        if not paginas:
            sys.exit("No hay imágenes.")
        print(f"{len(paginas)} páginas: " + ", ".join(p.name for p in paginas))
        if "--paginas" in a:
            # «--paginas 1-3»: el archivo trae otra canción u otra edición (el .rar de «Chiqué» trae también
            # «Chuzas»; el .zip de «Julián», tres ediciones seguidas). Números de página del archivo, desde 1.
            elegidas = set()
            for trozo in a[a.index("--paginas") + 1].split(","):
                x, _, y = trozo.partition("-")
                elegidas |= set(range(int(x), int(y or x) + 1))
            paginas = [p for k, p in enumerate(paginas, 1) if k in elegidas]
            print("Solo las páginas " + a[a.index("--paginas") + 1] + ": " + ", ".join(p.name for p in paginas))
        # copia de las páginas tal cual, para comparar
        orig = [Image.open(p).convert("RGB") for p in paginas]
        orig[0].save(base.with_name(base.name + "_original.pdf"), save_all=True, append_images=orig[1:], resolution=150)
        con_musica = [p for p in paginas if tiene_pentagramas(p)]
        sin = [p.name for p in paginas if p not in con_musica]
        if sin:
            print("Sin pentagramas (portada, letra…), no se leen:", ", ".join(sin))
        if not con_musica:
            sys.exit("Ninguna página tiene pentagramas.")
        # CADA PÁGINA POR SEPARADO: si en un libro de varias páginas una sola falla, Audiveris no exporta nada
        print("Leyendo con Audiveris página a página (1–2 min cada una)...")
        paginas_leidas = []
        for k, original in enumerate(con_musica, 1):
            mxls = []
            for modo in MODOS:
                img = preparar(original, tmp, k, modo)
                sal = tmp / f"sal{k}_{modo.replace('.', '')}"
                sal.mkdir()
                audiveris(img, sal, sal / "audiveris.log")
                mxls = sorted(sal.glob("*.mxl"), key=orden_natural)
                if mxls:   # (una portada falla en segundos: reintentar cuesta poco)
                    break
            if mxls:
                if modo != MODOS[0]:
                    print(f"  página {original.name}: leída al reintentar ({modo})")
                paginas_leidas.append(juntar_trozos(mxls))
            else:
                print(f"  página {original.name}: Audiveris no sacó nada (portada o página sin música, o ilegible)")
        if not paginas_leidas:
            print("Audiveris no sacó nada de ninguna página.")
            return
        raiz = juntar_paginas(paginas_leidas)
        print(f"Páginas leídas: {len(paginas_leidas)} de {len(con_musica)}")
    finally:
        sys.stdout = copia
    nombres = {sp.get("id"): (sp.findtext("part-name") or "") for sp in raiz.iter("score-part")}
    partes_crudas = raiz.findall("part")

    def n_notas(p):
        return sum(1 for n in p.iter("note") if n.find("pitch") is not None)
    mayor = max(n_notas(p) for p in partes_crudas)
    partes = []
    for p in partes_crudas:
        sd = p.find("measure/attributes/staff-details")
        if n_notas(p) < 0.1 * mayor:   # (los fantasmas ya los quitó juntar_paginas, página a página)
            print(f"  pentagrama fantasma o casi vacío quitado ({nombres.get(p.get('id'))}, {n_notas(p)} notas)")
            continue
        crudo = nombres.get(p.get("id"), "")
        dos = p.find("measure/attributes/staves") is not None
        nombre = "Piano" if dos else (nombre_limpio(crudo) if nombre_limpio(crudo) != crudo else "Voz / melodía")
        while any(n == nombre for n, _ in partes):
            nombre += " 2"
        partes.append((nombre, copy.deepcopy(p)))
    beats, beat_type = elegir_compas(raiz)
    print(f"{titulo}: {max(len(p.findall('measure')) for _, p in partes)} compases, compás {beats}/{beat_type}")
    print(f"CALIDAD DE LA LECTURA: {nota_calidad()[0]} ({CALIDAD:.0%} de los compases medían ya lo que deben)")
    for nombre, p in partes:
        poner_compas(p, beats, beat_type)
        k = arreglar_armaduras(p)
        if k:
            print(f"  {nombre}: {k} cambios de armadura mal leídos quitados (alteraciones rehechas)")
    # todas las partes con el mismo nº de compases (si Audiveris dio uno de más o de menos a alguna)
    largo = max(len(p.findall("measure")) for _, p in partes)
    for nombre, p in partes:
        while len(p.findall("measure")) < largo:
            ET.SubElement(p, "measure")
    partes.sort(key=lambda x: clave_orden(x[0]))
    general = ET.Element("score-partwise", version="4.0")
    ET.SubElement(ET.SubElement(general, "work"), "work-title").text = f"{titulo} (piano, {nota_calidad()[1]})"
    esc = ET.SubElement(ET.SubElement(general, "defaults"), "scaling")
    ET.SubElement(esc, "millimeters").text = "6"
    ET.SubElement(esc, "tenths").text = "40"
    lista = ET.SubElement(general, "part-list")
    sys.stdout = copia
    terminar(general, lista, partes, beats, beat_type, tempo_de_textos([(None, raiz, None)]) or TEMPO,
             base.with_name(base.name + "_piano.mxl"), min_calderon=1)
    print("Original escaneado:", base.with_name(base.name + "_original.pdf").as_uri())
    print("APROXIMADA: comparar con el original antes de fiarse de una nota concreta.")
    sys.stdout = copia.salida
    base.with_name(base.name + "_piano.txt").write_text("".join(copia.texto), encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
