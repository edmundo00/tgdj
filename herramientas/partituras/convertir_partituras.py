"""Pasa las partituras de MuseScore (.mscz) a MusicXML (.mxl) + MIDI (.mid).

Uso:  python convertir_partituras.py [carpeta_origen] [--todo]
      python convertir_partituras.py --pdf <archivo.pdf | imagen | carpeta> [...] [--todo]

- Busca todos los .mscz dentro de TDJ\\Partituras (o la carpeta que se le dé).
- Deja el resultado en TDJ\\Partituras\\convertidas\\<nombre>.mxl y <nombre>.mid
  (MusicXML = la partitura como texto, para leer/analizar; MIDI = para escuchar).
- Los .mid / .midi sueltos los pasa a <nombre>_desde_midi.mxl (MuseScore los cuantiza: ritmo aproximado,
  sin dinámicas ni articulación; las voces del piano pueden salir mezcladas).
- Para leer un .mxl sin cargarlo entero: resumen_mxl.py.
- Solo convierte lo nuevo o cambiado (--todo = rehacer todo).
- Usa MuseScore 4 por línea de órdenes, sin abrir ventanas.
- --pdf: PDF o imágenes (.jpg .png .tif) → <nombre>_audiveris.mxl + .mid con Audiveris (de consola, en la carpeta
  audiveris\\ de al lado, sin instalar). Lento: 1–3 min por página (más si el PC está ocupado). Tango a tango,
  nunca los 2.500 de golpe. Una carpeta = todos los PDF/imágenes de dentro (sin subcarpetas).
  El registro de Audiveris queda en convertidas\\_audiveris\\<nombre>.log.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PARTITURAS = Path(r"D:\Dropbox\TDJ\Partituras")
SALIDA = PARTITURAS / "convertidas"
MUSESCORE = [
    Path(r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"),
    Path(r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe"),
]


def buscar_musescore():
    for m in MUSESCORE:
        if m.exists():
            return m
    sys.exit("No encuentro MuseScore 4 (C:\\Program Files\\MuseScore 4).")
AUDIVERIS = Path(__file__).parent / "audiveris" / "Audiveris" / "Audiveris.exe"
IMAGENES = (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff")


def con_musescore(trabajos):
    print(f"Convirtiendo {len(trabajos)} partituras con MuseScore...")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as t:
        json.dump(trabajos, t, ensure_ascii=False)
        trabajo = t.name
    try:
        r = subprocess.run([str(buscar_musescore()), "-j", trabajo],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        os.unlink(trabajo)
    return r


def nombrar_parte(mxl: Path, nombre_archivo: str):
    """Audiveris casi nunca lee el nombre del instrumento (sale «Voice» o «Piano»). Si la partitura tiene una sola
    parte, se le pone el instrumento del nombre del archivo: «El Huracán OT - Contrabass» → «Contrabass»."""
    import re
    import zipfile
    instrumento = nombre_archivo.rsplit(" - ", 1)[-1].strip()
    with zipfile.ZipFile(mxl) as z:
        contenido = {n: z.read(n) for n in z.namelist()}
    xmls = [n for n in contenido if n.endswith(".xml") and "META-INF" not in n]
    if len(xmls) != 1:
        return
    texto = contenido[xmls[0]].decode("utf-8")
    if texto.count("<score-part ") != 1:
        return
    texto = re.sub(r"<part-name>[^<]*</part-name>", f"<part-name>{instrumento}</part-name>", texto, count=1)
    contenido[xmls[0]] = texto.encode("utf-8")
    with zipfile.ZipFile(mxl, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in contenido.items():
            z.writestr(n, b)


def con_audiveris(rutas, todo):
    if not AUDIVERIS.exists():
        sys.exit(f"No encuentro Audiveris en {AUDIVERIS} (pasos en PENDIENTE.md de esta carpeta).")
    archivos = []
    for r in rutas:
        r = Path(r)
        if r.is_dir():
            archivos += sorted(f for f in r.iterdir() if f.suffix.lower() in IMAGENES)
        elif r.suffix.lower() in IMAGENES:
            archivos.append(r)
        else:
            print("  no es PDF ni imagen:", r)
    registros = SALIDA / "_audiveris"
    registros.mkdir(parents=True, exist_ok=True)
    hechos, mal, bien = [], [], 0
    for f in archivos:
        destino = SALIDA / (f.stem + "_audiveris.mxl")
        if not todo and destino.exists() and destino.stat().st_mtime >= f.stat().st_mtime:
            continue
        print(f"Audiveris: {f.name} ...", flush=True)
        with tempfile.TemporaryDirectory() as tmp:
            with open(registros / (f.stem + ".log"), "w", encoding="utf-8", errors="replace") as log:
                subprocess.run([str(AUDIVERIS), "-batch",
                                "-constant", "org.audiveris.omr.Main.sheetStepTimeOut=1200",
                                "-export", "-output", tmp, "--", str(f)],
                               stdout=log, stderr=subprocess.STDOUT,
                               # sin esto, algunas páginas fallan con «Comparison method violates its general contract»
                               # TESSDATA_PREFIX = idiomas del OCR de texto (eng, spa) para títulos y nombres de partes
                               env={**os.environ, "JAVA_TOOL_OPTIONS": "-Djava.util.Arrays.useLegacyMergeSort=true",
                                    "TESSDATA_PREFIX": str(AUDIVERIS.parent.parent / "tessdata")},
                               creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
            salidas = sorted(Path(tmp).glob("*.mxl"))
            if not salidas:
                mal.append(f.name)
                continue
            # si sale en varios trozos («movimientos»), se guardan todos: <nombre>_audiveris.mvt2.mxl...
            for i, o in enumerate(salidas):
                d = destino if i == 0 else SALIDA / (f.stem + f"_audiveris.mvt{i + 1}.mxl")
                shutil.copyfile(o, d)
                nombrar_parte(d, f.stem)
                hechos.append(d)
            bien += 1
    print(f"Audiveris bien: {bien}   Fallan: {len(mal)}")
    for m in mal:
        print("  FALLA:", m, "(mirar el .log en", registros.as_uri() + ")")
    if hechos:
        con_musescore([{"in": str(d), "out": [str(d.with_suffix(".mid"))]} for d in hechos])
        for d in hechos:
            sin_mid = "" if d.with_suffix(".mid").exists() else "   (MuseScore no pudo sacar el .mid)"
            print("  ", d.as_uri() + sin_mid)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    todo = "--todo" in sys.argv
    SALIDA.mkdir(parents=True, exist_ok=True)
    if "--pdf" in sys.argv:
        if not args:
            sys.exit("Falta el PDF, la imagen o la carpeta.")
        con_audiveris(args, todo)
        return
    origen = Path(args[0]) if args else PARTITURAS

    trabajos = []
    for f in sorted(origen.rglob("*.mscz")):
        if SALIDA in f.parents:
            continue
        mxl = SALIDA / (f.stem + ".mxl")
        mid = SALIDA / (f.stem + ".mid")
        if not todo and mxl.exists() and mid.exists() and \
                min(mxl.stat().st_mtime, mid.stat().st_mtime) >= f.stat().st_mtime:
            continue
        trabajos.append({"in": str(f), "out": [str(mxl), str(mid)]})
    for f in sorted(list(origen.rglob("*.mid")) + list(origen.rglob("*.midi"))):
        if SALIDA in f.parents or f.suffix.lower() not in (".mid", ".midi"):
            continue
        mxl = SALIDA / (f.stem + "_desde_midi.mxl")
        if not todo and mxl.exists() and mxl.stat().st_mtime >= f.stat().st_mtime:
            continue
        trabajos.append({"in": str(f), "out": [str(mxl)]})

    if not trabajos:
        print("Nada nuevo que convertir.")
        return
    r = con_musescore(trabajos)

    bien, mal = 0, []
    for j in trabajos:
        if all(Path(o).exists() and Path(o).stat().st_size > 0 for o in j["out"]):
            bien += 1
        else:
            mal.append(Path(j["in"]).name)
    print(f"Bien: {bien}   Fallan: {len(mal)}")
    for m in mal:
        print("  FALLA:", m)
    if mal and r.stderr:
        print(r.stderr[-2000:])
    print("Carpeta:", SALIDA.as_uri())


if __name__ == "__main__":
    main()
