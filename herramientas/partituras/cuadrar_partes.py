"""Cuadra las partes sueltas que sacó Audiveris y las junta en una partitura general.

Uso:  python cuadrar_partes.py <carpeta de los PDF de las partes> [--compas 4/4] [--nombre "El Huracán"]

Problema: Audiveris pierde o inventa compases (trémolos, notas ligadas largas, barras mal leídas), así que cada
parte sale con un número distinto de compases y no se pueden poner una encima de otra.
Arreglo: los PDF hechos con ordenador llevan escrito el número del primer compás de cada línea (sistema).
Para cada línea se compara cuántos compases debería tener con cuántos sacó Audiveris:
  - si faltan, se añaden compases vacíos al final de esa línea (con el texto «compás añadido»);
  - si sobran, se juntan los dos compases seguidos más cortos.
Así todas las partes coinciden al principio de cada línea (el error queda dentro de una línea, 2–7 compases).
También pone el mismo compás (p. ej. 4/4) a todo, porque Audiveris se lo inventa si no está escrito.

Lee  convertidas\\<nombre del PDF>_audiveris.mxl  (hechos con convertir_partituras.py --pdf)
Deja convertidas\\<nombre>_general.mxl (todas las partes juntas, compases numerados igual) + .mid,
y escribe qué tocó en cada parte.
"""
import copy
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convertir_partituras import SALIDA, con_musescore  # noqa: E402
from comprobar_general import notas_por_compas  # noqa: E402


class Copia:
    """Lo que se escribe en pantalla se guarda también, para el informe X_general.txt."""
    def __init__(self, salida):
        self.salida, self.texto = salida, []

    def write(self, s):
        self.salida.write(s)
        self.texto.append(s)

    def flush(self):
        self.salida.flush()

ORDEN = ["flaut", "flut", "clar", "trompet", "trump", "saxo", "sax", "bandone", "band", "violin 1", "violin 2",
         "violin 3", "violin 4", "violin", "viola", "violonch", "violoncel", "cello", "guitar", "vibr", "glock",
         "piano", "contrab", "bass", "voz", "voice"]


def leer_mxl(ruta: Path) -> ET.Element:
    with zipfile.ZipFile(ruta) as z:
        n = [x for x in z.namelist() if x.endswith(".xml") and "META-INF" not in x][0]
        return ET.fromstring(z.read(n))


def escribir_mxl(raiz: ET.Element, ruta: Path):
    xml = ET.tostring(raiz, encoding="unicode")
    cab = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 '
           'Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n')
    cont = ('<?xml version="1.0" encoding="UTF-8"?><container><rootfiles><rootfile full-path="score.xml" '
            'media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>')
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/vnd.recordare.musicxml")
        z.writestr("META-INF/container.xml", cont)
        z.writestr("score.xml", cab + xml)


TODAS = Path(r"D:\Dropbox\TDJ\Partituras\convertidas\todas")   # lo que dejó convertir_todas.py
ORIGEN_TODAS = Path(r"D:\Dropbox\TDJ\Partituras\pdf")
NO_PARTES = ("score", "full", "conductor", "lead sheet", "leadsheet", "general", "partitura")


def buscar_mxl(pdf: Path):
    """El MusicXML de una parte: el de convertir_partituras.py --pdf o, si no, el de convertir_todas.py.
    Si Audiveris lo partió en trozos (.mvt2.mxl, .mvt3.mxl…), los pega seguidos."""
    uno = SALIDA / (pdf.stem + "_audiveris.mxl")
    if uno.exists():
        return leer_mxl(uno)
    try:
        base = TODAS / pdf.resolve().relative_to(ORIGEN_TODAS.resolve()).with_suffix(".mxl")
    except ValueError:
        return None
    if not base.exists():
        return None
    raiz = leer_mxl(base)
    k = 2
    while (trozo := base.with_name(base.stem + f".mvt{k}.mxl")).exists():
        otra = leer_mxl(trozo)
        for p1, p2 in zip(raiz.findall("part"), otra.findall("part")):
            compases = p2.findall("measure")
            if compases:   # el trozo empieza en línea nueva
                pr = compases[0].find("print")
                if pr is None:
                    pr = ET.Element("print")
                    compases[0].insert(0, pr)
                pr.set("new-system", "yes")
            for m in compases:
                p1.append(m)
        k += 1
    return raiz


def compas_escrito(datos):
    """El compás que más aparece escrito en las partes (si no hay ninguno, 4/4)."""
    vistos = Counter()
    for _, raiz, _ in datos:
        for t in raiz.iter("time"):
            b, bt = t.findtext("beats"), t.findtext("beat-type")
            if b and bt and b.isdigit() and bt.isdigit():
                vistos[(int(b), int(bt))] += 1
    # lo que manda es lo que MIDEN los compases (Audiveris lee mal el compás escrito: en «Derecho viejo» salía 3/4)
    largos = Counter()
    for _, raiz, _ in datos:
        for parte in raiz.findall("part"):
            div = 1
            for m in parte.findall("measure"):
                for a in m.findall("attributes"):
                    if a.findtext("divisions"):
                        div = int(float(a.findtext("divisions"))) or 1
                d = duracion(m)
                if d:
                    largos[Fraction(d, div)] += 1
    negras = largos.most_common(1)[0][0] if largos else Fraction(4)
    if negras == 4:
        return (2, 2) if vistos[(2, 2)] > vistos[(4, 4)] else (4, 4)
    if negras == 2:
        return (2, 4)
    if negras == 3:
        return (3, 4)
    buenos = [(c, n) for c, n in vistos.most_common() if c in ((4, 4), (2, 4), (3, 4), (2, 2))]
    return buenos[0][0] if buenos else (4, 4)


def inicios_de_linea(pdf: Path):
    """Número de compás escrito al principio de cada línea (la primera de la partitura es la 1).
    Si una línea no lleva número (pasa cuando empieza con un silencio de varios compases), se nota porque
    el hueco entre líneas es mayor: luego esa línea se cuenta junto con la anterior.
    Devuelve una lista de entradas: un número, o ("hueco", tamaño) donde PUEDE haber una línea sin número.
    Cuáles de esos huecos son líneas de verdad lo decide ajustar(), según cuántas líneas vio Audiveris."""
    import pymupdf
    doc = pymupdf.open(pdf)
    # columna de los números: donde hay más números DISTINTOS en el margen izquierdo (cambia según el PDF:
    # x≈53 en unos, 43 o 101 en otros; el «4 4» del compás también cae ahí, pero siempre es el mismo número)
    columnas = {}
    for pagina in doc:
        for x0, y0, x1, y1, txt, *_ in pagina.get_text("words"):
            if re.fullmatch(r"\d{1,3}", txt) and x0 < pagina.rect.width * 0.25 and int(txt) > 1:
                columnas.setdefault(round(x0 / 4), set()).add(int(txt))
    if not columnas:
        return [1]
    col = 4 * max(columnas, key=lambda c: len(columnas[c]))
    entradas = [1]
    for pagina in doc:
        alto = pagina.rect.height
        nums = []
        for x0, y0, x1, y1, txt, *_ in pagina.get_text("words"):
            # (y > 50: el nº de página va arriba del todo)
            if re.fullmatch(r"\d{1,3}", txt) and abs(x0 - col) <= 6 and 50 < y0 < alto - 40:
                nums.append((y0, int(txt)))
        nums = [(y, n) for y, n in sorted(nums) if n > 1]
        huecos = [nums[i + 1][0] - nums[i][0] for i in range(len(nums) - 1)]
        normal = sorted(huecos)[len(huecos) // 2] if huecos else 0
        for i, (y, n) in enumerate(nums):
            if i > 0 and normal and y - nums[i - 1][0] > 1.3 * normal:
                tam = (y - nums[i - 1][0]) / normal
                for k in range(max(1, round(tam) - 1)):
                    entradas.append(("hueco", tam - k))
            ultimo = max((e for e in entradas if isinstance(e, int)), default=0)
            if n > ultimo:
                entradas.append(n)
    return entradas


def ajustar(entradas, n_lineas):
    """Inicios de línea (con None = línea sin número) para que salgan n_lineas, usando los huecos más grandes.
    Devuelve None si no se puede (Audiveris vio menos líneas que números hay escritos)."""
    numeros = [e for e in entradas if isinstance(e, int)]
    faltan = n_lineas - len(numeros)
    huecos = sorted((e[1], i) for i, e in enumerate(entradas) if not isinstance(e, int))
    if faltan < 0 or faltan > len(huecos):
        return None
    elegidos = {i for _, i in huecos[len(huecos) - faltan:]} if faltan else set()
    return [None if i in elegidos else e for i, e in enumerate(entradas)
            if isinstance(e, int) or i in elegidos]


def lineas_de(parte: ET.Element):
    """Compases de la parte, agrupados por línea (Audiveris marca new-system / new-page)."""
    lineas = []
    for i, m in enumerate(parte.findall("measure")):
        nueva = any(p.get("new-system") == "yes" or p.get("new-page") == "yes" for p in m.findall("print"))
        if i == 0 or nueva:
            lineas.append([])
        lineas[-1].append(m)
    return lineas


def duracion(m: ET.Element):
    d = 0
    for e in m:
        if e.tag == "note" and e.find("chord") is None and e.find("grace") is None:
            d += int(float(e.findtext("duration") or 0))
        elif e.tag == "backup":
            break  # solo la primera voz
    return d


def vacio(ref: ET.Element, divisiones: int, beats: int, beat_type: int):
    """Compás de silencio. OJO: la duración va en las «divisiones» vigentes en ese punto (cambian)."""
    m = ET.Element("measure")
    d = ET.SubElement(m, "direction", placement="above")
    t = ET.SubElement(ET.SubElement(d, "direction-type"), "words")
    t.text = "compás añadido"
    n = ET.SubElement(m, "note")
    ET.SubElement(n, "rest", measure="yes")
    ET.SubElement(n, "duration").text = str(divisiones * beats * 4 // beat_type)
    ET.SubElement(n, "voice").text = "1"
    ET.SubElement(n, "type").text = "whole"    # sin <type>, MuseScore no abre el archivo
    return m


def juntar(a: ET.Element, b: ET.Element):
    for e in list(b):
        if e.tag in ("print",):
            continue
        a.append(e)


FIG = {"whole": Fraction(4), "half": Fraction(2), "quarter": Fraction(1), "eighth": Fraction(1, 2),
       "16th": Fraction(1, 4), "32nd": Fraction(1, 8), "64th": Fraction(1, 16)}


def largo_escrito(n: ET.Element):
    base = FIG.get(n.findtext("type") or "", Fraction(0))
    puntos = len(n.findall("dot"))
    return base * (2 - Fraction(1, 2 ** puntos))


def arreglar_grupillos(m: ET.Element, div: int):
    """Audiveris a veces mete en un grupillo (tresillo, seisillo…) notas que no caben: MuseScore no abre el
    archivo. Si un grupillo no cuadra, se quita y cada nota vale lo que dice su figura."""
    grupo, arreglados = [], 0
    for n in m.findall("note"):
        tm = n.find("time-modification")
        if tm is None:
            continue
        grupo.append(n)
        fin = any(t.get("type") == "stop" for t in n.iter("tuplet"))
        if not fin:
            continue
        actual = int(tm.findtext("actual-notes") or 3)

        tipo = grupo[0].find("time-modification").findtext("normal-type") or grupo[0].findtext("type")
        unidad = FIG.get(tipo or "", Fraction(0))
        escrito = sum((largo_escrito(x) for x in grupo if x.find("chord") is None), Fraction(0))
        if unidad and escrito != actual * unidad:
            for x in grupo:
                x.remove(x.find("time-modification"))
                for no in x.findall("notations"):
                    for t in no.findall("tuplet"):
                        no.remove(t)
                x.find("duration").text = str(int(largo_escrito(x) * div))
            arreglados += 1
        grupo = []
    return arreglados


def partir(m: ET.Element, largo: int):
    """Si Audiveris no vio una barra, un compás sale el doble de largo: se parte en dos donde se llega a «largo».
    Solo con una voz (sin <backup>) y si el corte cae justo entre dos notas. Devuelve el compás nuevo o None."""
    if m.find("backup") is not None or duracion(m) < 1.5 * largo:
        return None
    hijos = list(m)
    acum, corte = 0, None
    for i, e in enumerate(hijos):
        if e.tag == "note" and e.find("chord") is None and e.find("grace") is None:
            if acum == largo:
                corte = i
                break
            acum += int(float(e.findtext("duration") or 0))
            if acum > largo:
                return None
    if corte is None:
        return None
    nuevo = ET.Element("measure")
    for e in hijos[corte:]:
        m.remove(e)
        nuevo.append(e)
    return nuevo


def solo_silencio(m: ET.Element):
    notas = m.findall("note")
    return bool(notas) and all(n.find("rest") is not None for n in notas)


def cuadrar(parte: ET.Element, entradas, total, beats, beat_type, informe):
    lineas = lineas_de(parte)
    inicios = ajustar(entradas, len(lineas))
    if inicios is None:
        n = sum(isinstance(e, int) for e in entradas)
        informe.append(f"  ¡ojo! {len(lineas)} líneas en Audiveris y {n} con número en el PDF: "
                       f"solo se iguala el total (APROXIMADA)")
        lineas = [[m for linea in lineas for m in linea]]
        inicios = [1]
    # divisiones vigentes en cada compás (Audiveris las cambia a mitad de partitura)
    div_de = {}
    div = 1
    for m in parte.findall("measure"):
        for a in m.findall("attributes"):
            if a.findtext("divisions"):
                div = int(float(a.findtext("divisions"))) or 1
        div_de[id(m)] = div
    # líneas sin número: se juntan con la anterior en un solo bloque
    bloques = []
    for k, linea in enumerate(lineas):
        if inicios[k] is None:
            bloques[-1][1].extend(linea)
        else:
            bloques.append([inicios[k], list(linea)])
    nuevos = []
    cambios = []
    for k, (inicio, linea) in enumerate(bloques):
        fin = bloques[k + 1][0] if k + 1 < len(bloques) else total + 1
        quiere = fin - inicio
        while len(linea) > quiere:          # sobran: juntar los dos seguidos más cortos
            j = min(range(len(linea) - 1), key=lambda i: duracion(linea[i]) + duracion(linea[i + 1]))
            juntar(linea[j], linea[j + 1])
            del linea[j + 1]
            cambios.append(f"c.{inicio + j}: juntados 2")
        while len(linea) < quiere:
            # faltan: primero, ¿hay un compás que mide el doble (barra no vista)? → partirlo
            partido = False
            for j in sorted(range(len(linea)), key=lambda i: -duracion(linea[i]) / max(1, div_de.get(id(linea[i]), 1))):
                d = div_de.get(id(linea[j]), 1)
                nuevo = partir(linea[j], d * beats * 4 // beat_type)
                if nuevo is not None:
                    div_de[id(nuevo)] = d
                    linea.insert(j + 1, nuevo)
                    cambios.append(f"c.{inicio + j}: partido en 2")
                    partido = True
                    break
            if partido:
                continue
            # si no: casi siempre es un silencio de varios compases leído como uno → se añaden detrás
            # del último compás de silencio de la línea; si no hay ninguno, al final de la línea
            silencios = [i for i, m in enumerate(linea) if solo_silencio(m)]
            j = (silencios[-1] if silencios else len(linea) - 1)
            ref = linea[j]
            nuevo = vacio(ref, div_de.get(id(ref), 1), beats, beat_type)
            div_de[id(nuevo)] = div_de.get(id(ref), 1)
            linea.insert(j + 1, nuevo)
            cambios.append(f"c.{inicio + j + 1}: añadido")
        nuevos += linea
    for m in parte.findall("measure"):
        parte.remove(m)
    for i, m in enumerate(nuevos, 1):
        # silencios de compás entero sin <type> (Audiveris los pone en líneas que no se ven, con duraciones
        # raras como 100): MuseScore no abre el archivo → compás entero bien medido
        hijos = list(m)
        for k, n in enumerate(hijos):
            if n.tag == "note" and n.find("rest") is not None and n.find("type") is None:
                n.find("rest").set("measure", "yes")
                viejo = n.findtext("duration")
                nuevo = str(div_de.get(id(m), 1) * beats * 4 // beat_type)
                n.find("duration").text = nuevo
                ET.SubElement(n, "type").text = "whole"
                # el <backup> de detrás debe volver lo mismo (si no, MuseScore no abre el archivo)
                if k + 1 < len(hijos) and hijos[k + 1].tag == "backup" and hijos[k + 1].findtext("duration") == viejo:
                    hijos[k + 1].find("duration").text = nuevo
        if arreglar_grupillos(m, div_de.get(id(m), 1)):
            cambios.append(f"c.{i}: grupillo imposible quitado")
        m.set("number", str(i))
        m.attrib.pop("implicit", None)
        for a in m.findall("attributes"):          # quitar los compases inventados
            for t in a.findall("time"):
                a.remove(t)
        parte.append(m)
    # compás bueno en el primer compás
    a = nuevos[0].find("attributes")
    if a is None:
        a = ET.Element("attributes")
        nuevos[0].insert(0, a)
    t = ET.Element("time")
    ET.SubElement(t, "beats").text = str(beats)
    ET.SubElement(t, "beat-type").text = str(beat_type)
    # el orden en <attributes> importa: divisions, key, time, staves, clef
    hijos = list(a)
    pos = next((i for i, h in enumerate(hijos) if h.tag in ("staves", "part-symbol", "instruments", "clef")), len(hijos))
    a.insert(pos, t)
    informe.append("  " + (", ".join(cambios) if cambios else "sin cambios"))
    return parte


def abre_musescore(raiz: ET.Element) -> bool:
    import subprocess
    import tempfile
    from convertir_partituras import buscar_musescore
    with tempfile.TemporaryDirectory() as t:
        f, o = Path(t) / "p.mxl", Path(t) / "p.mid"
        escribir_mxl(raiz, f)
        try:
            subprocess.run([str(buscar_musescore()), "-o", str(o), str(f)], capture_output=True, timeout=300,
                           creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
        except subprocess.TimeoutExpired:
            return False
        return o.exists()


def reparar_para_musescore(general: ET.Element, parte: ET.Element):
    """Si MuseScore no abre esta parte sola, busca (por mitades) el primer compás que lo rompe y lo cambia por
    un compás de silencio con el texto «compás quitado»; repite hasta que la abra. Devuelve los compases cambiados."""
    def sola(hasta=None):
        r = ET.Element("score-partwise", version="4.0")
        pl = ET.SubElement(r, "part-list")
        for sp in general.iter("score-part"):
            if sp.get("id") == parte.get("id"):
                pl.append(copy.deepcopy(sp))
        p = copy.deepcopy(parte)
        if hasta is not None:
            for m in p.findall("measure")[hasta:]:
                p.remove(m)
        r.append(p)
        return r
    cambiados = []
    while not abre_musescore(sola()) and len(cambiados) < 10:
        compases = parte.findall("measure")
        lo, hi = 1, len(compases)
        while lo < hi:
            mid = (lo + hi) // 2
            if abre_musescore(sola(mid)):
                lo = mid + 1
            else:
                hi = mid
        m = compases[lo - 1]
        div = 1
        for c in compases[:lo]:
            for a in c.findall("attributes"):
                if a.findtext("divisions"):
                    div = int(float(a.findtext("divisions"))) or 1
        t = parte.find("measure/attributes/time")
        beats, bt = (int(t.findtext("beats")), int(t.findtext("beat-type"))) if t is not None else (4, 4)
        for e in list(m):
            if e.tag not in ("attributes", "print", "barline"):
                m.remove(e)
        nuevo = vacio(m, div, beats, bt)
        for e in list(nuevo):
            m.append(e)
        m.find("direction/direction-type/words").text = "compás quitado"
        cambiados.append(lo)
    return cambiados


PASOS = "CDEFGAB"
SOSTENIDOS, BEMOLES = "FCGDAEB", "BEADGCF"
ACCIDENTE = {"sharp": 1, "flat": -1, "natural": 0, "double-sharp": 2, "sharp-sharp": 2, "flat-flat": -2}


def es_viola(nombre):
    n = nombre.lower()
    return ("viola" in n or "vla" in n) and "cello" not in n


def arreglar_viola(parte: ET.Element):
    """Audiveris lee la clave de do de la viola como clave de fa (en 4ª o 3ª): todas las notas salen 6 (o 4)
    notas más graves. Se cambia la clave a do en 3ª y cada nota se sube a su sitio, rehaciendo las alteraciones
    con la armadura y los accidentes del compás. La clave de sol (la viola la usa en lo agudo) se deja.
    Devuelve cuántas notas se movieron."""
    subir = {("F", "4"): 6, ("F", "3"): 4}
    clave, quintas, movidas = None, 0, 0
    for m in parte.findall("measure"):
        llevadas = {}
        for e in m:
            if e.tag == "attributes":
                f = e.findtext("key/fifths")
                if f is not None:
                    quintas = int(f)
                for c in e.findall("clef"):
                    clave = (c.findtext("sign"), c.findtext("line"))
                    if clave in subir:
                        c.find("sign").text, c.find("line").text = "C", "3"
            elif e.tag == "note" and e.find("pitch") is not None and clave in subir:
                p = e.find("pitch")
                idx = 7 * int(p.findtext("octave")) + PASOS.index(p.findtext("step")) + subir[clave]
                paso, octava = PASOS[idx % 7], idx // 7
                acc = ACCIDENTE.get((e.findtext("accidental") or "").strip())
                if acc is not None:
                    alt = llevadas[(paso, octava)] = acc
                elif (paso, octava) in llevadas:
                    alt = llevadas[(paso, octava)]
                elif quintas > 0 and paso in SOSTENIDOS[:quintas]:
                    alt = 1
                elif quintas < 0 and paso in BEMOLES[:-quintas]:
                    alt = -1
                else:
                    alt = 0
                p.find("step").text, p.find("octave").text = paso, str(octava)
                a = p.find("alter")
                if alt:
                    if a is None:
                        a = ET.Element("alter")
                        p.insert(1, a)
                    a.text = str(alt)
                elif a is not None:
                    p.remove(a)
                movidas += 1
    return movidas


# instrumentos que se escriben en otro tono: (diatónico, cromático) para pasar de lo escrito a lo que suena
TRANSPOSITORES = [(("alto sax", "alto saxophone", "sax alto", "saxo alto"), (-5, -9)),
                  (("tenor sax", "tenor saxophone", "saxo tenor"), (-8, -14)),
                  ((" in a ", " en la"), (-2, -3)),
                  ((" in bb", " in b♭", " in b ", " in si", "clar", "klarin", "clarinete", "trumpet", "trompet", "tpta"), (-1, -2))]


def poner_transposicion(parte: ET.Element, nombre: str):
    """Para que el MIDI suene en su tono real (Audiveris no lo pone). Devuelve el texto de lo hecho o ''."""
    n = " " + nombre.lower() + " "
    for claves, (dia, cro) in TRANSPOSITORES:
        if any(c in n for c in claves):
            if parte.find("measure/attributes/transpose") is not None:
                return ""
            a = parte.find("measure/attributes")
            if a is None:
                return ""
            t = ET.Element("transpose")
            ET.SubElement(t, "diatonic").text = str(dia)
            ET.SubElement(t, "chromatic").text = str(cro)
            hijos = list(a)   # va después de divisions/key/time/staves/part-symbol/instruments/clef/staff-details
            pos = next((i for i, h in enumerate(hijos) if h.tag in ("directive", "measure-style")), len(hijos))
            a.insert(pos, t)
            return f"suena {-cro} semitonos más grave de lo escrito"
    return ""


TEMPO = 120   # negras por minuto: más o menos el de un tango bailable en 4/4

# programa General MIDI (1–128) según el nombre de la parte; sin esto, el MIDI sale todo con piano
PROGRAMAS = [(("bandone", "band.", "bandoneon"), 24), (("acorde", "accordion"), 22),
             (("violonc", "cello", "vc"), 43), (("contrab", "bass", "cb"), 44), (("viola", "vla"), 42),
             (("violin", "violín", "vl"), 41), (("piano", "pno"), 1), (("flaut", "flute"), 74),
             (("clar",), 72), (("trump", "trompet", "tpta"), 57), (("alto sax", "alto saxophone", "sax alto", "saxo alto"), 66),
             (("tenor sax", "tenor saxophone", "saxo tenor"), 67), (("vibr",), 12), (("glock",), 10), (("guit", "gtr"), 25), (("voice", "voz", "vocal", "tenor", "alto", "canto"), 53)]


def poner_instrumento(sp: ET.Element, pid: str, nombre: str, k: int):
    n = nombre.lower()
    programa = next((p for claves, p in PROGRAMAS if any(c in n for c in claves)), 1)
    si = ET.SubElement(sp, "score-instrument", id=f"{pid}-I1")
    ET.SubElement(si, "instrument-name").text = nombre
    mi = ET.SubElement(sp, "midi-instrument", id=f"{pid}-I1")
    canal = (k - 1) % 15 + 1
    ET.SubElement(mi, "midi-channel").text = str(canal + 1 if canal >= 10 else canal)   # el 10 es de batería
    ET.SubElement(mi, "midi-program").text = str(programa)


def quitar_tempos(parte: ET.Element):
    """Audiveris lee mal las marcas de metrónomo: fuera todas (se pone un tempo al principio)."""
    for m in parte.findall("measure"):
        for d in m.findall("direction"):
            for dt in d.findall("direction-type"):
                if dt.find("metronome") is not None:
                    d.remove(dt)
            for s in d.findall("sound"):
                s.attrib.pop("tempo", None)
            if d.find("direction-type") is None:
                m.remove(d)
        for s in m.findall("sound"):
            s.attrib.pop("tempo", None)


def figura_de(duracion: int, div: int):
    """(tipo, puntillos) de una duración, si es una figura normal (sin grupillo); si no, None."""
    for tipo, negras in FIG.items():
        for puntos in (0, 1, 2):
            if negras * (2 - Fraction(1, 2 ** puntos)) * div == duracion:
                return tipo, puntos
    return None


def ajustar_figura(n: ET.Element, tipo: str, puntos: int):
    if n.find("type") is None:
        ET.SubElement(n, "type")
    n.find("type").text = tipo
    for d in n.findall("dot"):
        n.remove(d)
    tm = n.find("time-modification")
    if tm is not None:
        n.remove(tm)
    pos = list(n).index(n.find("type")) + 1
    for _ in range(puntos):
        n.insert(pos, ET.Element("dot"))


def medir_bien(parte: ET.Element, beats: int, beat_type: int) -> int:
    """Que cada compás mida exactamente lo que dice el compás. Audiveris pierde tresillos (9 corcheas en un 4/4)
    y notas: si una voz se pasa, sus duraciones se encogen en proporción (lo normal es un tresillo no leído);
    si el compás se queda corto, se completa con un avance (silencio). Devuelve cuántos compases se tocaron."""
    div, tocados = 1, 0
    for m in parte.findall("measure"):
        for a in m.findall("attributes"):
            if a.findtext("divisions"):
                div = int(float(a.findtext("divisions"))) or 1
        largo = div * beats * 4 // beat_type
        if m.find("note") is None:   # compás vacío (o solo avances): silencio de compás
            for f in m.findall("forward"):
                m.remove(f)
            for b in m.findall("backup"):
                m.remove(b)
            for e in list(vacio(m, div, beats, beat_type)):
                if e.tag == "note":
                    m.append(e)
            tocados += 1
            continue
        hijos = list(m)
        # trozos de voz: lo que va entre un <backup> y el siguiente
        trozos, actual, pos, inicio = [], [], 0, 0
        for e in hijos:
            if e.tag == "backup":
                trozos.append((inicio, actual))
                pos -= int(float(e.findtext("duration") or 0))
                inicio, actual = max(pos, 0), []
                pos = inicio
            elif e.tag in ("note", "forward"):
                actual.append(e)
                if e.tag == "forward" or (e.find("chord") is None and e.find("grace") is None):
                    pos += int(float(e.findtext("duration") or 0))
        trozos.append((inicio, actual))
        cambiado = False
        nuevos_fin = []
        for inicio, elems in trozos:
            pasos = [e for e in elems if e.tag == "forward" or (e.find("chord") is None and e.find("grace") is None)]
            total = sum(int(float(e.findtext("duration") or 0)) for e in pasos)
            cabe = largo - inicio
            if total > cabe > 0:
                # se pasa: se corta lo que sobra al final (encoger en proporción da figuras que no existen y
                # MuseScore no abre el archivo). La nota que cruza la barra se acorta si queda una figura normal.
                pos_v, quitar_acorde, acortar = inicio, False, None
                for e in elems:
                    principal = e.tag == "forward" or (e.find("chord") is None and e.find("grace") is None)
                    if not principal:
                        if quitar_acorde and e in list(m):
                            m.remove(e)
                        elif acortar and e.find("chord") is not None and e in list(m):
                            e.find("duration").text = str(acortar[0])
                            ajustar_figura(e, *acortar[1])
                        continue
                    acortar = None
                    d = int(float(e.findtext("duration") or 0))
                    quitar_acorde = False
                    if pos_v >= largo:
                        m.remove(e)
                        quitar_acorde = True
                    elif pos_v + d > largo:
                        resto = largo - pos_v
                        figura = figura_de(resto, div)
                        if e.tag == "note" and figura:
                            e.find("duration").text = str(resto)
                            ajustar_figura(e, *figura)
                            acortar = (resto, figura)
                        else:
                            f = ET.Element("forward")
                            ET.SubElement(f, "duration").text = str(resto)
                            m.insert(list(m).index(e), f)
                            m.remove(e)
                            quitar_acorde = True
                    pos_v += d
                if not any((w.text or "") == "compás recortado" for w in m.iter("words")):   # una sola marca
                    marca = ET.Element("direction", placement="above")
                    ET.SubElement(ET.SubElement(marca, "direction-type"), "words").text = "compás recortado"
                    # detrás de <attributes>/<print>/<barline> del principio (delante, MuseScore no abre el archivo)
                    hijos = list(m)
                    pos = 0
                    while pos < len(hijos) and hijos[pos].tag in ("attributes", "print", "barline"):
                        pos += 1
                    m.insert(pos, marca)
                cambiado = True
                nuevos_fin.append(largo)
            else:
                nuevos_fin.append(inicio + total)
        # notas que se quedaron en 0 (muy cortas tras encoger): fuera
        for e in list(m):
            if e.tag in ("note", "forward") and e.find("grace") is None and (e.findtext("duration") or "1") == "0":
                m.remove(e)
                cambiado = True
        # si la primera voz se queda corta: avance (silencio) hasta el final del compás
        if trozos and trozos[0][1] and nuevos_fin and nuevos_fin[0] < largo:
            f = ET.Element("forward")
            ET.SubElement(f, "duration").text = str(largo - nuevos_fin[0])
            vivos = [e for e in trozos[0][1] if e in list(m)]
            if vivos:
                m.insert(list(m).index(vivos[-1]) + 1, f)
                cambiado = True
        # rehacer los <backup> con las nuevas posiciones (cada uno vuelve al principio de su trozo)
        k = 0
        pos = 0
        for e in list(m):
            if e.tag == "backup":
                destino = trozos[k + 1][0] if k + 1 < len(trozos) else 0
                atras = pos - destino
                if atras > 0:
                    e.find("duration").text = str(atras)
                    pos = destino
                else:
                    m.remove(e)
                k += 1
            elif e.tag == "forward" or (e.tag == "note" and e.find("chord") is None and e.find("grace") is None):
                pos += int(float(e.findtext("duration") or 0))
        tocados += cambiado
    return tocados


def clave_orden(nombre):
    n = sin_acentos(nombre.lower())
    for i, o in enumerate(ORDEN):
        if o in n:
            return (i, n)
    return (len(ORDEN), n)


INSTRUMENTOS = [  # (palabras del nombre del archivo, nombre en español) — el orden importa
    (("alto sax", "alto saxophone", "sax alto", "saxo alto"), "Saxo alto"),
    (("tenor sax", "tenor saxophone", "saxo tenor"), "Saxo tenor"),
    (("bandone", "bando", "bnd", "band"), "Bandoneón"),
    (("violoncel", "violonch", "cello", "vcllo"), "Violonchelo"),
    (("contrab", "double bass", "bass", "cbj"), "Contrabajo"),
    (("viola", "vla"), "Viola"),
    (("violin", "violín", "violine", "vl"), "Violín"),
    (("piano", "klavier", "pno", "pn"), "Piano"),
    (("flute", "flauta", "flöte", "flut"), "Flauta"),
    (("clar", "klarin"), "Clarinete"),
    (("trump", "trompet", "tpta"), "Trompeta"),
    (("guit", "gtr"), "Guitarra"),
    (("vibes", "vibraph", "vibraf"), "Vibráfono"),
    (("glock",), "Glockenspiel"),
    (("vocal", "voice", "voz", "tenor", "canto"), "Voz"),
]
ROMANOS = {"i": "1", "ii": "2", "iii": "3", "iv": "4"}


def sin_acentos(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def nombre_limpio(crudo: str) -> str:
    """«TigreViejo Tigre Viejo-Muertos Violin 1» → «Violín 1»; «Ventarron KI - Violín III» → «Violín 3»;
    «Poema-Bnd1-rev» → «Bandoneón 1»; «Humillacion-inst. clar» → «Clarinete». Si no reconoce nada, lo deja."""
    n = sin_acentos(crudo.lower())
    for claves, nombre in INSTRUMENTOS:
        for c in claves:
            m = re.search(re.escape(sin_acentos(c)) + r"[a-z]*[\s\-_.]*(\d|iv|iii|ii|i)?(?![a-z0-9])", n)
            if m:
                num = ROMANOS.get(m.group(1), m.group(1)) if m.group(1) else ""
                extra = ""
                if nombre == "Clarinete" or nombre == "Trompeta":
                    if re.search(r"\bin a\b|\ben la\b", n):
                        extra = " en La"
                    elif re.search(r"\bin (bb|b|b♭)\b|\ben si", n):
                        extra = " en Si♭"
                if nombre == "Violín" and "solo" in n:
                    extra = " solo"
                return f"{nombre}{' ' + num if num else ''}{extra}"
    return crudo


def tempo_de_textos(datos):
    """Si el PDF no da el tempo, lo que leyó Audiveris como texto: «Milonga J 92», «♩ = 110»."""
    vistos = Counter()
    for _, raiz, _ in datos:
        for w in raiz.iter("words"):
            m = re.search(r"[J♩q]\s*=?\s*[—\-]?\s*(\d{2,3})(?!\d)", w.text or "")
            if m and 40 <= int(m.group(1)) <= 240:
                vistos[int(m.group(1))] += 1
    return vistos.most_common(1)[0][0] if vistos else None


def tempo_del_pdf(pdfs):
    """El tempo escrito arriba en las partes («♩=125»): el que más se repite en las primeras páginas."""
    import pymupdf
    vistos = Counter()
    for pdf in pdfs:
        try:
            pagina = pymupdf.open(pdf)[0]
        except Exception:  # noqa: BLE001
            continue
        alto = pagina.rect.height
        for x0, y0, x1, y1, txt, *_ in pagina.get_text("words"):
            # «q=125» (la «q» es la negra en la letra de música), «=125», «h=60» (blanca)
            m = re.fullmatch(r"([qhe♩]?)\s*=\s*(\d{2,3})", txt)
            if m and y0 < alto * 0.3:
                t = int(m.group(2)) * {"h": 2, "e": 0.5}.get(m.group(1), 1)
                if 40 <= t <= 240:
                    vistos[int(t)] += 1
    return vistos.most_common(1)[0][0] if vistos else None


def veredicto(nombre, notas):
    """Lo mismo que comprobar_general.py, para una parte frente a las demás (notas = {nombre: [Counter por compás]})."""
    from comprobar_general import coincidencia
    mia = notas[nombre]
    otras = []
    for i in range(len(mia)):
        c = Counter()
        for n, lista in notas.items():
            if n != nombre and i < len(lista):
                c.update(lista[i])
        otras.append(c)
    en_sitio, total = coincidencia(mia, otras)
    if en_sitio is None or total < 20:
        return "bien", "poca música"
    corrida = [x for x in (coincidencia(mia, otras, d)[0] for d in (-2, -1, 1, 2)) if x is not None]
    azar = sum(corrida) / len(corrida) if corrida else 0
    for t in range(1, 12):
        movida = [Counter({(pc - t) % 12: k for pc, k in c.items()}) for c in mia]
        x = coincidencia(movida, otras)[0] or 0
        if x > en_sitio + 0.05:
            return "OTRO TONO", f"encaja mejor {t} semitonos más abajo"
    if (1 - en_sitio) > 0.75 * (1 - azar):
        return "NO ENCAJA", f"en su sitio {en_sitio:.0%}, corrida un compás {azar:.0%}"
    return "bien", f"{en_sitio:.0%} frente a {azar:.0%} corrida"


def limitar_voces(parte: ET.Element) -> int:
    """MuseScore solo admite 4 voces por pentagrama (y una voz en un solo pentagrama). Audiveris, en los escaneos,
    reparte a veces una mano en 5–6 voces: MuseScore no abre ese compás. Se quedan las 4 voces con más notas de cada
    pentagrama (1–4 arriba, 5–8 abajo) y lo demás se quita. Devuelve cuántas notas se quitaron."""
    quitadas = 0
    for m in parte.findall("measure"):
        cuenta = Counter()
        for n in m.findall("note"):
            cuenta[(n.findtext("staff") or "1", n.findtext("voice") or "1")] += 1
        if not cuenta:
            continue
        nuevo = {}
        for staff in sorted({s for s, _ in cuenta}, key=int):
            voces = sorted((v for s, v in cuenta if s == staff), key=lambda v: -cuenta[(staff, v)])
            for k, v in enumerate(voces[:4]):
                nuevo[(staff, v)] = str((int(staff) - 1) * 4 + k + 1)
        if all(nuevo.get(c) == c[1] for c in cuenta) and len(nuevo) == len(cuenta):
            continue
        for e in list(m):
            if e.tag not in ("note", "forward"):
                continue
            clave = (e.findtext("staff") or "1", e.findtext("voice") or "1")
            if e.tag == "forward" and e.find("voice") is None:
                continue
            if clave in nuevo:
                v = e.find("voice")
                if v is not None:
                    v.text = nuevo[clave]
            else:
                m.remove(e)
                quitadas += e.tag == "note"
    return quitadas


def terminar(general, lista, partes, beats, beat_type, tempo, destino, min_calderon=3):
    """Lo común a todas las generales: instrumentos, tempos, compases bien medidos, limpieza, .mxl + .mid."""
    malos = 0
    for k, (nombre, parte) in enumerate(partes, 1):
        pid = f"P{k}"
        sp = ET.SubElement(lista, "score-part", id=pid)
        ET.SubElement(sp, "part-name").text = nombre
        poner_instrumento(sp, pid, nombre, k)
        quitar_tempos(parte)
        voces_fuera = limitar_voces(parte)
        if voces_fuera:
            print(f"  {nombre}: {voces_fuera} notas de voces de más quitadas (MuseScore admite 4 por pentagrama)")
        malos += medir_bien(parte, beats, beat_type)
        parte.set("id", pid)
        general.append(parte)
    print(f"Compases que no medían lo que deben (tresillos no leídos, notas perdidas), ajustados: {malos}")
    # calderones y cesuras: Audiveris los ve donde no hay (y cada uno frena el MIDI a la mitad). Solo se dejan en
    # los compases donde los tienen al menos 3 partes (un calderón de verdad lo tiene toda la orquesta)
    veces = Counter()
    for parte in general.findall("part"):
        for i, m in enumerate(parte.findall("measure")):
            if m.find(".//fermata") is not None or m.find(".//caesura") is not None:
                veces[i] += 1
    quitados = 0
    for parte in general.findall("part"):
        for i, m in enumerate(parte.findall("measure")):
            if veces[i] >= min_calderon:
                continue
            for padre in m.iter():
                for h in list(padre):
                    if h.tag in ("fermata", "caesura"):
                        padre.remove(h)
                        quitados += 1
    if quitados:
        print(f"Calderones/cesuras sueltos quitados (mal leídos): {quitados}")
    # la maquetación de cada parte suelta (saltos de página y de línea, anchos) no vale para la general:
    # fuera, y que MuseScore la coloque (si no, sale una primera página en blanco)
    for m in general.iter("measure"):
        m.attrib.pop("width", None)
        for p in m.findall("print"):
            m.remove(p)
    # letras de ensayo (A, B…): MuseScore las pone por encima de TODA la orquesta, así que con las de cada parte
    # salen apiladas 10 veces. Solo las de la primera parte. Y fuera los textos basura del OCR («,», «W», «r3-|»).
    for k, parte in enumerate(general.findall("part")):
        for m in parte.findall("measure"):
            for d in m.findall("direction"):
                for dt in d.findall("direction-type"):
                    r = dt.find("rehearsal")
                    w = dt.find("words")
                    if (r is not None and k > 0) or (w is not None and not re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]{3}", w.text or "")):
                        d.remove(dt)
                if d.find("direction-type") is None:
                    m.remove(d)
    # un solo tempo al principio (los de Audiveris salen absurdos: «tempo 1», «♩ = 5»); sin texto, solo para el MIDI
    primera = general.find("part/measure")
    if primera is not None:
        d = ET.Element("direction", placement="above")
        ET.SubElement(ET.SubElement(d, "direction-type"), "words").text = ""
        ET.SubElement(d, "sound", tempo=str(tempo))
        hijos = list(primera)
        pos = next((i for i, h in enumerate(hijos) if h.tag in ("note", "backup", "forward")), len(hijos))
        primera.insert(pos, d)

    destino.with_suffix(".mid").unlink(missing_ok=True)   # si no, uno viejo hace creer que salió bien
    escribir_mxl(general, destino)
    con_musescore([{"in": str(destino), "out": [str(destino.with_suffix(".mid"))]}])
    if not destino.with_suffix(".mid").exists():
        print("MuseScore no la abre: busco los compases rotos (tarda unos minutos)...")
        if os.environ.get("TDJ_DEPURAR"):   # para mirar qué rompe MuseScore
            escribir_mxl(general, Path(os.environ["TDJ_DEPURAR"]))
        nombres = {sp.get("id"): sp.findtext("part-name") for sp in general.iter("score-part")}
        for parte in general.findall("part"):
            for k in reparar_para_musescore(general, parte):
                print(f"  {nombres[parte.get('id')]}: compás {k} cambiado por silencio (MuseScore no lo abría)")
        escribir_mxl(general, destino)
        con_musescore([{"in": str(destino), "out": [str(destino.with_suffix(".mid"))]}])
    print("Partitura general:", destino.as_uri())
    if destino.with_suffix(".mid").exists():
        print("MIDI:", destino.with_suffix(".mid").as_uri())
    else:
        print("(MuseScore no pudo sacar el .mid)")


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    carpeta = Path(a[0])
    titulo = a[a.index("--nombre") + 1] if "--nombre" in a else carpeta.name
    copia = sys.stdout = Copia(sys.stdout)
    print(f"Partitura general hecha con cuadrar_partes.py a partir de las partes de:\n  {carpeta}\n")

    # --quitar "TOL3(KB),cue,Clarinet in A": partes alternativas o repetidas que no deben entrar (trozo del nombre)
    quitar = [q.strip().lower() for q in a[a.index("--quitar") + 1].split(",")] if "--quitar" in a else []
    pdfs = sorted(carpeta.glob("*.pdf"))
    datos = []
    for pdf in pdfs:
        if any(x in pdf.stem.lower().rsplit(" - ", 1)[-1] for x in NO_PARTES) or "cond." in pdf.stem.lower():
            print("  no es una parte (se salta):", pdf.name)
            continue
        if any(q and q in pdf.stem.lower() for q in quitar):
            print("  parte alternativa o repetida (se quita):", pdf.name)
            continue
        raiz = buscar_mxl(pdf)
        if raiz is None:
            print("  falta convertir:", pdf.name, "(convertir_partituras.py --pdf)")
            continue
        inicios = inicios_de_linea(pdf)
        datos.append((pdf, raiz, inicios))
    if not datos:
        sys.exit("No hay nada que cuadrar.")
    if "--compas" in a:
        beats, beat_type = map(int, a[a.index("--compas") + 1].split("/"))
    else:
        beats, beat_type = compas_escrito(datos)

    # total de compases: lo más repetido de (inicio de la última línea + compases que Audiveris vio en ella - 1)
    finales = []
    for pdf, raiz, inicios in datos:
        for parte in raiz.findall("part"):
            lin = lineas_de(parte)
            aj = ajustar(inicios, len(lin))
            if aj and aj[-1] is not None:
                finales.append(aj[-1] + len(lin[-1]) - 1)
    if not finales:
        sys.exit(f"{titulo}: en ninguna parte coinciden las líneas de Audiveris con las del PDF; no se puede cuadrar.")
    total = Counter(finales).most_common(1)[0][0]
    print(f"{titulo}: {total} compases, compás {beats}/{beat_type}")

    general = ET.Element("score-partwise", version="4.0")
    ET.SubElement(ET.SubElement(general, "work"), "work-title").text = titulo
    # notas algo más pequeñas que lo normal: con 15–20 pentagramas, si no, no cabe ni un sistema por página
    # (y MuseScore deja la primera página solo con el título)
    esc = ET.SubElement(ET.SubElement(general, "defaults"), "scaling")
    n_pent = sum(2 if raiz.find(".//staves") is not None else 1 for _, raiz, _ in datos)
    ET.SubElement(esc, "millimeters").text = "4.5" if n_pent <= 20 else "3.6"
    ET.SubElement(esc, "tenths").text = "40"
    lista = ET.SubElement(general, "part-list")
    partes = []
    # nombre del instrumento: lo que va detrás de « - » o, si no hay, lo que no comparten todos los nombres
    # («Mi Serenata Bandoneon 1» → «Bandoneon 1»)
    tallos = [p.stem.split() for p, _, _ in datos]
    comun = 0
    while len(tallos) > 1 and all(len(t) > comun + 1 for t in tallos) and len({t[comun] for t in tallos}) == 1:
        comun += 1
    for pdf, raiz, inicios in datos:
        trozos_nombre = [t.strip() for t in pdf.stem.split(" - ")]
        while len(trozos_nombre) > 1 and len(trozos_nombre[-1]) <= 3:   # «Piano - OT»: OT es la orquesta, no el instrumento
            trozos_nombre.pop()
        instrumento = (trozos_nombre[-1] if " - " in pdf.stem
                       else " ".join(pdf.stem.split()[comun:])).strip()
        trozos = raiz.findall("part")
        if len(trozos) > 1:
            # un PDF de un instrumento solo tiene UNA parte: lo demás que saca Audiveris son pentagramas invisibles
            # del PDF (print-object="no") o restos casi vacíos. Se queda la parte con más notas, y otra solo si
            # tiene al menos la mitad de notas (de verdad hay dos, p. ej. divisi).
            def n_notas(p):
                return sum(1 for n in p.iter("note") if n.find("pitch") is not None)

            def invisible(p):
                sd = p.find("measure/attributes/staff-details")
                return sd is not None and sd.get("print-object") == "no"
            mayor = max(n_notas(p) for p in trozos)
            buenos = [p for p in trozos if not invisible(p) and n_notas(p) >= 0.5 * mayor] or \
                     [max(trozos, key=n_notas)]
            if len(buenos) < len(trozos):
                print(f"  {instrumento}: {len(trozos) - len(buenos)} pentagrama(s) fantasma de Audiveris quitado(s)")
            trozos = buenos
        for i, parte in enumerate(trozos):
            nombre = nombre_limpio(instrumento)
            if len(trozos) > 1:   # dos pentagramas de verdad del mismo instrumento: casi siempre las dos manos
                clave = parte.find("measure/attributes/clef/sign")
                nombre += " (mano izq.)" if clave is not None and clave.text == "F" else " (mano der.)"
            k = 2
            base = nombre
            while any(n == nombre for n, _ in partes):   # dos «Guitarra» o dos «Violín» sin número
                nombre = f"{base} ({k})"
                k += 1
            informe = []
            hecho = cuadrar(copy.deepcopy(parte), inicios, total, beats, beat_type, informe)
            if hecho is not None and es_viola(nombre):
                k = arreglar_viola(hecho)
                if k:
                    informe.append(f"  clave de do mal leída como de fa: {k} notas subidas a su sitio")
            if hecho is not None:
                t = poner_transposicion(hecho, nombre)
                if t:
                    informe.append("  " + t)
            print(f"{nombre}:")
            print("\n".join(informe))
            if hecho is not None:
                partes.append((nombre, hecho))
    partes.sort(key=lambda p: clave_orden(p[0]))
    # control de calidad: una parte que no encaja con la armonía de las demás (o está en otro tono) se queda FUERA
    # de la general, para no ensuciarla. Se apunta en el informe.
    fuera = []
    if "--sin-control" not in a:
        notas = {n: notas_por_compas(p)[0] for n, p in partes}
        for nombre, parte in list(partes):
            v, detalle = veredicto(nombre, notas)
            if v != "bien":
                partes.remove((nombre, parte))
                fuera.append(f"{nombre}: {v} ({detalle})")
        for f in fuera:
            print("  FUERA de la general:", f)
    destino = SALIDA / (titulo.replace(" ", "_") + "_general.mxl")
    terminar(general, lista, partes, beats, beat_type,
             tempo_del_pdf([p for p, _, _ in datos]) or tempo_de_textos(datos) or TEMPO, destino)
    print("\nPartes en la general:", ", ".join(sp.findtext("part-name") for sp in general.iter("score-part")))
    print("Textos en la partitura: «compás añadido» = Audiveris perdió ese compás (va en silencio); «compás recortado»"
          " = leyó notas de más (casi siempre un tresillo) y se cortó lo que sobraba: ahí FALTAN notas;"
          " «compás quitado» = MuseScore no lo abría y se cambió por silencio.")
    sys.stdout = copia.salida
    destino.with_suffix(".txt").write_text("".join(copia.texto), encoding="utf-8")


if __name__ == "__main__":
    main()
