"""Arregla el MusicXML que saca Audiveris de un PDF de Sibelius y lo pasa a MIDI.

Uso (python del venv analizar_tango, lleva music21):
    python partitura_audiveris.py <entrada.mxl> <salida.mid> --nombre Contrabajo --fa 1 [--bemoles 2] [--sol8 1]

Qué arregla (visto con «El Huracán», Community Tango Orchestra, 18-11-2026):
- La clave de fa no la reconoce: lee ese pentagrama como si fuera clave de sol. --fa <pentagrama> baja
  esas notas 12 grados (posición de sol -> posición de fa) y les vuelve a poner la armadura.
- La clave de sol a veces la lee como «sol 8va» (clef-octave-change 1): --sol8 <pentagrama> baja una octava.
- Si no ha leído la armadura (contrabajo), --bemoles N la pone (2 = si bemol mayor / sol menor).
- No ve NINGÚN sostenido con la letra de esas partituras (ni en el piano). --sostenidos F sube los fa que no lleven
  alteración escrita (en sol menor el fa# de re7 es lo normal; algún fa natural de sol7 saldrá mal, y los do# de
  adorno se pierden).
Las alteraciones escritas (<accidental>) se respetan y valen hasta el final del compás.
Escribe también <salida>.musicxml arreglado (para verlo en MuseScore).
"""
import re, sys, zipfile, argparse

PASOS = "CDEFGAB"
ORDEN_BEMOLES = "BEADGCF"
VALOR_ACC = {"sharp": 1, "flat": -1, "natural": 0, "double-sharp": 2, "flat-flat": -2}


def leer_xml(ruta):
    if ruta.lower().endswith(".mxl"):
        z = zipfile.ZipFile(ruta)
        nombre = [n for n in z.namelist() if n.lower().endswith((".xml", ".musicxml")) and not n.startswith("META")][0]
        return z.read(nombre).decode("utf-8")
    return open(ruta, encoding="utf-8").read()


def arreglar(x, fa, sol8, bemoles_cli, sostenidos=""):
    # armadura: la que haya leído Audiveris (la primera) o la dada
    k = re.search(r"<fifths>(-?\d+)</fifths>", x)
    fifths = -bemoles_cli if bemoles_cli is not None else (int(k.group(1)) if k else 0)
    if not k:
        x = re.sub(r"(<attributes>\s*<divisions>\d+</divisions>)",
                   rf"\1<key><fifths>{fifths}</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time>", x, count=1)
    arm = {p: 0 for p in PASOS}
    for p in (ORDEN_BEMOLES[:-fifths] if fifths < 0 else ORDEN_BEMOLES[::-1][:fifths]):
        arm[p] = -1 if fifths < 0 else 1
    # claves
    for st in sol8:
        x = re.sub(rf'(<clef number="{st}">\s*<sign>G</sign>\s*<line>2</line>\s*)<clef-octave-change>1</clef-octave-change>', r"\1", x)
        if st == 1:
            x = re.sub(r'(<clef>\s*<sign>G</sign>\s*<line>2</line>\s*)<clef-octave-change>1</clef-octave-change>', r"\1", x)
    for st in fa:
        clave = f'<clef number="{st}"><sign>F</sign><line>4</line></clef>'
        if re.search(rf'<clef number="{st}">', x):
            x = re.sub(rf'<clef number="{st}">.*?</clef>', clave, x, count=1, flags=re.S)
        elif "<staves>" in x:
            x = re.sub(r"(<staves>\d</staves>)", r"\1" + clave, x, count=1)
        else:   # una sola pauta, sin clave
            x = re.sub(r"(<attributes>\s*<divisions>\d+</divisions>(?:<key>.*?</key>)?(?:<time>.*?</time>)?)",
                       r"\1" + clave.replace(' number="1"', ""), x, count=1, flags=re.S)

    def compas(mm):
        cuerpo = mm.group(0)
        vistas = {}   # (pauta, paso, octava) -> alteración escrita en este compás

        def nota(nm):
            n = nm.group(0)
            if "<pitch>" not in n:
                return n
            st = int(re.search(r"<staff>(\d)</staff>", n).group(1)) if "<staff>" in n else 1
            paso = re.search(r"<step>(\w)</step>", n).group(1)
            octava = int(re.search(r"<octave>(-?\d+)</octave>", n).group(1))
            paso0 = paso
            if st in fa:
                g = PASOS.index(paso) + 7 * octava - 12
                paso, octava = PASOS[g % 7], g // 7
            elif st in sol8:
                octava -= 1
            acc = re.search(r"<accidental[^>]*>([a-z-]+)</accidental>", n)
            a0 = re.search(r"<alter>(-?\d+)</alter>", n)
            a0 = int(a0.group(1)) if a0 else 0
            if acc and acc.group(1) in VALOR_ACC:
                vistas[(st, paso, octava)] = VALOR_ACC[acc.group(1)]
            elif st in fa and a0 and (not k or a0 != arm[paso0]):
                # Audiveris pone a veces el sostenido solo como <alter>; si no viene de la armadura, es una alteración escrita
                vistas[(st, paso, octava)] = a0
            alt = vistas.get((st, paso, octava), arm[paso] if st in fa else None)
            if alt is None:   # pauta de sol: la alteración de Audiveris ya vale
                alt = a0
            if paso in sostenidos and (st, paso, octava) not in vistas and alt == 0:
                alt = 1   # sensible sin alteración escrita: Audiveris no ve los sostenidos de esta letra
            nuevo = f"<pitch><step>{paso}</step>" + (f"<alter>{alt}</alter>" if alt else "") + f"<octave>{octava}</octave></pitch>"
            return re.sub(r"<pitch>.*?</pitch>", nuevo, n, flags=re.S)

        return re.sub(r"<note[ >].*?</note>", nota, cuerpo, flags=re.S)

    return re.sub(r"<measure[ >].*?</measure>", compas, x, flags=re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada"); ap.add_argument("salida")
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--fa", type=int, nargs="*", default=[])
    ap.add_argument("--sol8", type=int, nargs="*", default=[])
    ap.add_argument("--bemoles", type=int)
    ap.add_argument("--sostenidos", default="", help="notas que se suben si no llevan alteración escrita (p. ej. F en sol menor)")
    ap.add_argument("--programa", type=int, default=None, help="programa General MIDI (0 piano, 32 bajo, 21 acordeón)")
    a = ap.parse_args()
    x = arreglar(leer_xml(a.entrada), set(a.fa), set(a.sol8), a.bemoles, a.sostenidos.upper())
    x = re.sub(r"<part-name>[^<]*</part-name>", f"<part-name>{a.nombre}</part-name>", x)
    xml_sal = a.salida.rsplit(".", 1)[0] + ".musicxml"
    open(xml_sal, "w", encoding="utf-8").write(x)
    import music21
    s = music21.converter.parse(xml_sal)
    s.write("midi", fp=a.salida)
    # nombre e instrumento en el MIDI (para que comprobar_con_midi.py sepa qué es)
    import pretty_midi
    m = pretty_midi.PrettyMIDI(a.salida)
    notas = []
    for ins in m.instruments:
        ins.name = a.nombre
        if a.programa is not None:
            ins.program = a.programa
        notas += ins.notes
    m.write(a.salida)
    print(f"{a.salida}: {len(notas)} notas, {len(m.get_downbeats())} compases, de {notas[0].start:.1f} a {max(n.end for n in notas):.1f} s (a 120)")


if __name__ == "__main__":
    main()
