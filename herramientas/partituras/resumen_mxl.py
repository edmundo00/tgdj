"""Resumen legible de una partitura MusicXML (.mxl / .musicxml / .xml), para que Claude la lea sin cargarla entera.

Uso:  python resumen_mxl.py <partitura.mxl> [--compases 1-8] [--parte bandoneon]

Sin opciones: título, partes, nº de compases, tonalidad y compás (y dónde cambian), tempo, repeticiones,
          y por parte: cuántas notas, registro (nota más grave y más aguda), notas más usadas, figuras.
--compases A-B: además, compás a compás, las notas de cada parte con su tiempo dentro del compás
          (p. ej. «1:Do4 negra  2½:Mi4 corchea»; semi = semicorchea); acordes simultáneos con «+»; silencios con «·».
--parte texto: solo las partes cuyo nombre contenga ese texto (da igual mayúsculas/acentos).

Solo usa Python estándar (zipfile + xml). Funciona con los .mxl de Partituras\\convertidas y con los de Audiveris.
"""
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from fractions import Fraction
from pathlib import Path

NOTAS = {"C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}
ALTER = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}
MAYOR = ["Dob", "Solb", "Reb", "Lab", "Mib", "Sib", "Fa", "Do", "Sol", "Re", "La", "Mi", "Si", "Fa#", "Do#"]
MENOR = ["Lab", "Mib", "Sib", "Fa", "Do", "Sol", "Re", "La", "Mi", "Si", "Fa#", "Do#", "Sol#", "Re#", "La#"]
FIGURA = {"breve": "cuadrada", "whole": "redonda", "half": "blanca", "quarter": "negra", "eighth": "corchea",
          "16th": "semi", "32nd": "fusa", "64th": "semifusa"}
SEMITONO = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def leer(ruta: Path) -> ET.Element:
    if ruta.suffix.lower() == ".mxl":
        with zipfile.ZipFile(ruta) as z:
            nombre = None
            if "META-INF/container.xml" in z.namelist():
                c = ET.fromstring(z.read("META-INF/container.xml"))
                rf = c.find(".//{*}rootfile")
                if rf is not None:
                    nombre = rf.get("full-path")
            if not nombre:
                nombre = next(n for n in z.namelist() if n.endswith((".xml", ".musicxml")) and "META-INF" not in n)
            return ET.fromstring(z.read(nombre))
    return ET.parse(ruta).getroot()


def sin_ns(raiz):
    for e in raiz.iter():
        if isinstance(e.tag, str) and "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]
    return raiz


def normal(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def tonalidad(fifths, modo):
    i = int(fifths) + 7
    if not 0 <= i < 15:
        return f"{fifths} alteraciones"
    if modo == "minor":
        return f"{MENOR[i]} menor"
    return f"{MAYOR[i]} mayor" if modo == "major" else f"{MAYOR[i]} mayor / {MENOR[i]} menor"


def nombre_nota(n):
    p = n.find("pitch")
    if p is None:
        u = n.find("unpitched")
        return ("perc." + (u.findtext("display-step") or "")) if u is not None else "?"
    paso = p.findtext("step")
    alt = int(float(p.findtext("alter") or 0))
    return f"{NOTAS[paso]}{ALTER.get(alt, '')}{p.findtext('octave')}"


def midi_de(n):
    p = n.find("pitch")
    if p is None:
        return None
    return 12 * (int(p.findtext("octave")) + 1) + SEMITONO[p.findtext("step")] + int(float(p.findtext("alter") or 0))


def tiempo_txt(f: Fraction):
    """posición en tiempos (empezando en 1) como texto corto: 1, 1½, 2¼, 1⅓..."""
    v = f + 1
    ent = int(v)
    resto = v - ent
    marcas = {Fraction(1, 2): "½", Fraction(1, 4): "¼", Fraction(3, 4): "¾", Fraction(1, 3): "⅓",
              Fraction(2, 3): "⅔", Fraction(1, 8): "⅛", Fraction(3, 8): "⅜", Fraction(5, 8): "⅝", Fraction(7, 8): "⅞"}
    if resto == 0:
        return str(ent)
    return f"{ent}{marcas.get(resto, '+' + str(resto))}"


def analizar(raiz):
    partes = {}
    for sp in raiz.iter("score-part"):
        nombre = (sp.findtext("part-name") or "").strip() or (sp.findtext("part-abbreviation") or "").strip()
        partes[sp.get("id")] = {"nombre": nombre or sp.get("id")}
    datos = []
    for parte in raiz.findall("part"):
        pid = parte.get("id")
        info = partes.get(pid, {"nombre": pid})
        divisiones = 1
        beat_type = 4
        compases = []
        for m in parte.findall("measure"):
            c = {"num": m.get("number"), "notas": [], "tonalidad": None, "compas": None, "tempo": None,
                 "repeticion": [], "acordes": []}
            pos = Fraction(0)
            ultimo_inicio = Fraction(0)
            for e in m:
                if e.tag == "attributes":
                    divisiones = int(float(e.findtext("divisions") or divisiones))
                    k = e.find("key")
                    if k is not None and k.findtext("fifths") is not None:
                        c["tonalidad"] = tonalidad(k.findtext("fifths"), k.findtext("mode"))
                    t = e.find("time")
                    if t is not None and t.findtext("beats"):
                        beat_type = int(t.findtext("beat-type") or 4)
                        c["compas"] = f"{t.findtext('beats')}/{beat_type}"
                elif e.tag == "direction":
                    s = e.find(".//sound")
                    if s is not None and s.get("tempo"):
                        c["tempo"] = round(float(s.get("tempo")))
                    for w in e.iter("words"):
                        if w.text and w.text.strip():
                            txt = re.sub(r"<[^>]*>", "", w.text).strip()
                            if txt:
                                c.setdefault("textos", []).append(txt)
                elif e.tag == "sound" and e.get("tempo"):
                    c["tempo"] = round(float(e.get("tempo")))
                elif e.tag == "harmony":
                    r = e.find("root")
                    if r is not None:
                        nom = NOTAS.get(r.findtext("root-step"), "?") + ALTER.get(int(float(r.findtext("root-alter") or 0)), "")
                        kind = e.find("kind")
                        txt = (kind.get("text") if kind is not None and kind.get("text") is not None else
                               {"minor": "m", "dominant": "7", "minor-seventh": "m7", "major-seventh": "maj7",
                                "diminished": "dim", "augmented": "aum", "major": ""}.get(kind.text if kind is not None else "", ""))
                        c["acordes"].append(nom + txt)
                elif e.tag == "barline":
                    rep = e.find("repeat")
                    if rep is not None:
                        c["repeticion"].append("𝄆" if rep.get("direction") == "forward" else "𝄇")
                    end = e.find("ending")
                    if end is not None and end.get("type") == "start":
                        c["repeticion"].append(f"casilla {end.get('number')}")
                elif e.tag == "backup":
                    pos -= Fraction(int(float(e.findtext("duration") or 0)), divisiones)
                elif e.tag == "forward":
                    pos += Fraction(int(float(e.findtext("duration") or 0)), divisiones)
                elif e.tag == "note":
                    dur = Fraction(int(float(e.findtext("duration") or 0)), divisiones)
                    es_acorde = e.find("chord") is not None
                    if e.find("grace") is not None:
                        continue
                    inicio = ultimo_inicio if es_acorde else pos
                    # posición en tiempos del compás (tiempo = la figura de beat_type)
                    en_tiempos = inicio * Fraction(beat_type, 4)
                    silencio = e.find("rest") is not None
                    ligada = any(t.get("type") == "stop" for t in e.findall("tie"))
                    c["notas"].append({"t": en_tiempos, "nota": None if silencio else nombre_nota(e),
                                       "midi": None if silencio else midi_de(e), "fig": e.findtext("type") or "",
                                       "puntillo": e.find("dot") is not None, "ligada": ligada,
                                       "tresillo": e.find("time-modification") is not None,
                                       "voz": e.findtext("voice") or "1", "pentagrama": e.findtext("staff") or "1"})
                    if not es_acorde:
                        ultimo_inicio = pos
                        pos += dur
            compases.append(c)
        datos.append({"id": pid, "nombre": info["nombre"], "compases": compases})
    return datos


def figura_txt(n):
    f = FIGURA.get(n["fig"], n["fig"])
    return f + (" con puntillo" if n["puntillo"] else "") + (" de tresillo" if n["tresillo"] else "")


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    ruta = Path(a[0])
    desde = hasta = None
    filtro = None
    if "--compases" in a:
        r = a[a.index("--compases") + 1]
        desde, _, hasta = r.partition("-")
        desde = int(desde)
        hasta = int(hasta or desde)
    if "--parte" in a:
        filtro = normal(a[a.index("--parte") + 1])

    raiz = sin_ns(leer(ruta))
    titulo = (raiz.findtext("work/work-title") or raiz.findtext("movement-title") or "").strip()
    autores = [f"{(c.get('type') or 'autor')}: {c.text.strip()}" for c in raiz.iter("creator") if c.text and c.text.strip()]
    for cw in raiz.iter("credit-words"):
        if not titulo and cw.text and cw.text.strip():
            titulo = cw.text.strip()
    partes = analizar(raiz)
    print(f"Archivo: {ruta.name}")
    print(f"Título: {titulo or '(sin título)'}" + (f"   ·  {' · '.join(autores)}" if autores else ""))
    if not partes:
        print("No tiene partes.")
        return
    n_comp = max(len(p["compases"]) for p in partes)
    print(f"Partes: {len(partes)}   Compases: {n_comp}")

    # cambios de tonalidad, compás y tempo (de la primera parte que los tenga), repeticiones
    for clave, etiqueta in (("tonalidad", "Tonalidad"), ("compas", "Compás"), ("tempo", "Tempo (negras/min)")):
        cambios = []
        for p in partes:
            for i, c in enumerate(p["compases"]):
                if c[clave] and (not cambios or cambios[-1][1] != c[clave]):
                    cambios.append((c["num"], c[clave]))
            if cambios:
                break
        if cambios:
            print(f"{etiqueta}: " + ", ".join(f"{v} (c.{n})" for n, v in cambios))
    reps = [(c["num"], r) for c in partes[0]["compases"] for r in c["repeticion"]]
    if reps:
        print("Repeticiones: " + ", ".join(f"{r} c.{n}" for n, r in reps))
    textos = [(c["num"], t) for c in partes[0]["compases"] for t in c.get("textos", [])]
    if textos:
        print("Indicaciones: " + "; ".join(f"c.{n} «{t}»" for n, t in textos[:25]) + (" …" if len(textos) > 25 else ""))
    acordes = [(c["num"], " ".join(c["acordes"])) for p in partes for c in p["compases"] if c["acordes"]]
    if acordes:
        print(f"Cifrado (acordes escritos): {len(acordes)} compases, empieza: " +
              ", ".join(f"c.{n} {t}" for n, t in acordes[:12]))
    print()

    elegidas = [p for p in partes if not filtro or filtro in normal(p["nombre"])]
    for p in elegidas:
        notas = [n for c in p["compases"] for n in c["notas"]]
        sonando = [n for n in notas if n["nota"] and not n["ligada"]]
        silencios = sum(1 for n in notas if not n["nota"])
        vacios = sum(1 for c in p["compases"] if not any(n["nota"] for n in c["notas"]))
        print(f"== {p['nombre']}  ({len(p['compases'])} compases, {vacios} sin notas)")
        if not sonando:
            print("   sin notas")
            continue
        con_midi = [n for n in sonando if n["midi"] is not None]
        if con_midi:
            grave = min(con_midi, key=lambda n: n["midi"])
            agudo = max(con_midi, key=lambda n: n["midi"])
            print(f"   {len(sonando)} notas, {silencios} silencios · registro {grave['nota']} – {agudo['nota']}")
        base = Counter(n["nota"].rstrip("0123456789-") for n in sonando)
        print("   notas más usadas: " + ", ".join(f"{k} {v}" for k, v in base.most_common(8)))
        figs = Counter(figura_txt(n) for n in sonando)
        print("   figuras: " + ", ".join(f"{k} {v}" for k, v in figs.most_common(8)))
        tres = sum(1 for n in sonando if n["tresillo"])
        if tres:
            print(f"   tresillos (notas): {tres}")

    if desde is not None:
        print()
        print(f"--- Compases {desde}–{hasta}  (posición = tiempo del compás: 1, 1½, 2¼…; «+» = a la vez; «~» = ligada de antes; · = silencio)")
        for p in elegidas:
            print(f"== {p['nombre']}")
            for c in p["compases"]:
                try:
                    num = int("".join(ch for ch in c["num"] if ch.isdigit()) or 0)
                except ValueError:
                    continue
                if not desde <= num <= hasta:
                    continue
                grupos = {}
                for n in c["notas"]:
                    clave = (n["pentagrama"], n["voz"])
                    grupos.setdefault(clave, {}).setdefault(n["t"], []).append(n)
                lineas = []
                for (pent, voz), porpos in sorted(grupos.items()):
                    trozos = []
                    for t in sorted(porpos):
                        ns = porpos[t]
                        if all(not n["nota"] for n in ns):
                            trozos.append(f"{tiempo_txt(t)}:·{figura_txt(ns[0])}")
                        else:
                            txt = "+".join(("~" if n["ligada"] else "") + n["nota"] for n in ns if n["nota"])
                            trozos.append(f"{tiempo_txt(t)}:{txt} {figura_txt(ns[0])}")
                    etiqueta = f"p{pent}v{voz}" if len(grupos) > 1 else ""
                    lineas.append((etiqueta + " " if etiqueta else "") + "  ".join(trozos))
                extra = (" [" + " ".join(c["acordes"]) + "]") if c["acordes"] else ""
                print(f"  c.{c['num']}{extra}: " + ("\n        ".join(lineas) if lineas else "(vacío)"))


if __name__ == "__main__":
    main()
