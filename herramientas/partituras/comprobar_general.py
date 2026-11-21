"""¿Están bien cuadradas las partes de una partitura general? (las que hace cuadrar_partes.py)

Uso:  python comprobar_general.py <X_general.mxl> [...]

Para cada parte mira, compás a compás, cuántas de sus notas (sin octava) suenan también en las demás partes en ese
mismo compás. Si la parte está en su sitio, casi todas coinciden (es la misma armonía); si está corrida un compás o
más, coinciden muchas menos. Para saber cuánto es «poco», lo compara con la misma parte corrida 1 compás («al azar»).
También cuenta los compases añadidos o quitados al cuadrar.
  bien      = coincide claramente más en su sitio que corrida
  dudosa    = casi igual en su sitio que corrida (puede estar descolocada, o tocar poco)
"""
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

SEMITONO = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def leer(ruta: Path):
    with zipfile.ZipFile(ruta) as z:
        n = [x for x in z.namelist() if x.endswith((".xml", ".musicxml")) and "META-INF" not in x][0]
        return ET.fromstring(z.read(n))


def notas_por_compas(parte):
    """Lista (por compás) de Counter de clases de nota (0–11); los instrumentos transpositores no se corrigen."""
    salida, marcas = [], []
    trans = 0   # instrumentos en otro tono: lo que SUENA (cuadrar_partes.py les pone <transpose>)
    for m in parte.findall("measure"):
        t = m.find("attributes/transpose/chromatic")
        if t is not None:
            trans = int(t.text)
        c = Counter()
        for n in m.findall("note"):
            p = n.find("pitch")
            if p is not None:
                c[(SEMITONO[p.findtext("step")] + int(float(p.findtext("alter") or 0)) + trans) % 12] += 1
        salida.append(c)
        marcas.append(" ".join(w.text or "" for w in m.iter("words")))
    return salida, marcas


def coincidencia(mia, otras, corrimiento=0):
    si = total = 0
    for i, c in enumerate(mia):
        j = i + corrimiento
        if not c or not (0 <= j < len(otras)) or not otras[j]:
            continue
        for pc, k in c.items():
            total += k
            if pc in otras[j]:
                si += k
    return (si / total if total else None), total


def comprobar(ruta: Path):
    raiz = leer(ruta)
    nombres = {sp.get("id"): sp.findtext("part-name") for sp in raiz.iter("score-part")}
    partes = [(nombres.get(p.get("id"), "?"), *notas_por_compas(p)) for p in raiz.findall("part")]
    largos = {len(n) for _, n, _ in partes}
    print(f"== {ruta.name}: {len(partes)} partes, compases {sorted(largos)}")
    malas = 0
    for k, (nombre, mia, marcas) in enumerate(partes):
        otras = []
        for i in range(len(mia)):
            c = Counter()
            for kk, (_, n, _) in enumerate(partes):
                if kk != k and i < len(n):
                    c.update(n[i])
            otras.append(c)
        en_sitio, total = coincidencia(mia, otras)
        corrida = [coincidencia(mia, otras, d)[0] for d in (-2, -1, 1, 2)]
        corrida = [c for c in corrida if c is not None]
        azar = sum(corrida) / len(corrida) if corrida else None
        # ¿encaja mejor transportada? (clarinete/trompeta en Si♭ = +2 escrito, saxo alto = +9, clave mal leída…)
        mejor_t, mejor = 0, en_sitio or 0
        for t in range(1, 12):
            movida = [Counter({(pc - t) % 12: k for pc, k in c.items()}) for c in mia]
            x = coincidencia(movida, otras)[0] or 0
            if x > mejor + 0.05:
                mejor_t, mejor = t, x
        anadidos = sum("añadido" in x for x in marcas)
        quitados = sum("quitado" in x for x in marcas)
        # se comparan los FALLOS: en su sitio debe fallar bastante menos que corrida (con armonía quieta, corrida
        # también acierta mucho, así que mirar la diferencia de aciertos engaña)
        if en_sitio is None or total < 20:
            v = "poca música"
        elif mejor_t:
            v, malas = "OTRO TONO", malas + 1
        elif azar is not None and (1 - en_sitio) > 0.75 * (1 - azar):
            v, malas = "DUDOSA", malas + 1
        else:
            v = "bien"
        extra = (f", {anadidos} compases añadidos" if anadidos else "") + (f", {quitados} quitados" if quitados else "")
        if mejor_t:
            extra += f"; encaja mejor {mejor_t} semitonos más abajo ({mejor:.0%}): ¿instrumento en otro tono o clave mal leída?"
        pct = (lambda x: "—" if x is None else f"{x:.0%}")
        print(f"  {v:11} {nombre[:28]:28} en su sitio {pct(en_sitio):>4}  corrida {pct(azar):>4}  ({total} notas{extra})")
    return malas


def main():
    for a in sys.argv[1:]:
        comprobar(Path(a))


if __name__ == "__main__":
    main()
