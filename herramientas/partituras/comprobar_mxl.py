"""Comprobación automática de una partitura MusicXML sacada con Audiveris: ¿vale o hay que mirarla?

Uso:  python comprobar_mxl.py <archivo.mxl> [...]
      (y desde convertir_todas.py, con la función comprobar())

Da «bien» o «dudosa» con los motivos. Mira:
  - que tenga compases y notas (y no casi todo silencio);
  - que los compases midan casi todos lo mismo (si Audiveris lee mal el ritmo, salen de largos distintos);
  - que las notas de cada parte estén en un registro posible (ni bajísimas ni altísimas, ni más de 4 octavas y
    media en una parte que no sea de piano: pasa cuando lee mal la clave);
  - que no cambie de tonalidad a cada rato (señal de armaduras mal leídas).
Son señales, no pruebas: una «bien» puede tener notas mal, y una «dudosa» puede valer.
"""
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from fractions import Fraction
from pathlib import Path

SEMITONO = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
GRAVES = ("contrab", "cbj", "bass", "cello", "violonc", "vc", "fagot", "bajo")
AGUDOS = ("violin", "vl", "flaut", "flute", "clar", "tpta", "trompet", "sax", "oboe")


def leer(ruta: Path) -> ET.Element:
    with zipfile.ZipFile(ruta) as z:
        n = [x for x in z.namelist() if x.endswith((".xml", ".musicxml")) and "META-INF" not in x][0]
        raiz = ET.fromstring(z.read(n))
    for e in raiz.iter():
        if isinstance(e.tag, str) and "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]
    return raiz


def comprobar(ruta: Path, instrumento: str = ""):
    """Devuelve (veredicto, motivos, datos). instrumento = nombre del archivo, si el MusicXML no lo trae."""
    try:
        raiz = leer(ruta)
    except Exception as e:  # noqa: BLE001
        return "dudosa", [f"no se puede leer ({e.__class__.__name__})"], {}
    nombres = {sp.get("id"): (sp.findtext("part-name") or "").lower() for sp in raiz.iter("score-part")}
    motivos = []
    total_notas = total_comp = 0
    largos = Counter()
    cambios_tono = 0
    for parte in raiz.findall("part"):
        nombre = nombres.get(parte.get("id"), "")
        if len(raiz.findall("part")) == 1 and instrumento:
            nombre = instrumento.lower()
        piano = any(p in nombre for p in ("piano", "pno", "guitar", "guitarra", "teclado", "organ"))
        div = 1
        alturas = []
        vacios = 0
        tono = None
        compases = parte.findall("measure")
        for m in compases:
            for a in m.findall("attributes"):
                if a.findtext("divisions"):
                    div = int(float(a.findtext("divisions")))
                k = a.findtext("key/fifths")
                if k is not None:
                    if tono is not None and k != tono:
                        cambios_tono += 1
                    tono = k
            dur = Fraction(0)
            suenan = 0
            for e in m:
                if e.tag == "backup":
                    break
                if e.tag == "note" and e.find("chord") is None and e.find("grace") is None:
                    dur += Fraction(int(float(e.findtext("duration") or 0)), div)
            for n in m.findall("note"):
                p = n.find("pitch")
                if p is not None:
                    suenan += 1
                    alturas.append(12 * (int(p.findtext("octave")) + 1) + SEMITONO[p.findtext("step")]
                                   + int(float(p.findtext("alter") or 0)))
            if not suenan:
                vacios += 1
            if dur:
                largos[dur] += 1
        total_comp = max(total_comp, len(compases))
        total_notas += len(alturas)
        if alturas:
            alturas.sort()
            # sin el 2 % de los extremos (alguna nota suelta mal leída no debe tumbar la parte)
            q = max(1, len(alturas) // 50)
            bajo, alto = alturas[q - 1] if len(alturas) > q else alturas[0], alturas[-q]
            if bajo < 24 or alto > 103:
                motivos.append(f"{nombre or 'parte'}: notas imposibles ({bajo}–{alto} en MIDI)")
            elif not piano and alto - bajo > 54:
                motivos.append(f"{nombre or 'parte'}: registro de más de 4½ octavas (¿clave mal leída?)")
            media = alturas[len(alturas) // 2]
            palabras = nombre.replace("-", " ").replace(".", " ").split()
            def es(lista):
                return any(w.startswith(x) for w in palabras for x in lista) or any(x in nombre for x in lista if len(x) > 3)
            if es(GRAVES) and media >= 64:
                motivos.append(f"{nombre}: demasiado agudo para un instrumento grave (¿clave mal leída?)")
            elif es(AGUDOS) and not es(GRAVES) and media < 55:
                motivos.append(f"{nombre}: demasiado grave para un instrumento agudo (¿clave mal leída?)")
        if compases and vacios / len(compases) > 0.8 and len(raiz.findall("part")) == 1:
            motivos.append("casi todo silencio")
    if total_comp < 4:
        motivos.append(f"solo {total_comp} compases")
    if total_notas < 10:
        motivos.append(f"solo {total_notas} notas")
    if largos:
        largo_normal, veces = largos.most_common(1)[0]
        parecidos = veces / sum(largos.values())
        if parecidos < 0.6:
            motivos.append(f"compases de largos distintos (solo el {parecidos:.0%} mide {largo_normal} negras)")
    if total_comp and cambios_tono > max(3, total_comp // 15):
        motivos.append(f"{cambios_tono} cambios de tonalidad (¿armaduras mal leídas?)")
    datos = {"compases": total_comp, "notas": total_notas, "partes": len(raiz.findall("part"))}
    return ("dudosa" if motivos else "bien"), motivos, datos


def main():
    for a in sys.argv[1:]:
        v, motivos, datos = comprobar(Path(a), Path(a).stem.split("_audiveris")[0].rsplit(" - ", 1)[-1])
        print(f"{v.upper():7} {Path(a).name}  {datos}" + ("".join("\n        - " + m for m in motivos)))


if __name__ == "__main__":
    main()
