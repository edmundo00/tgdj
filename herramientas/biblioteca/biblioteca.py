# -*- coding: utf-8 -*-
"""
BIBLIOTECA de TDJ: OCR de los libros escaneados + índice + buscador.

  python biblioteca.py ocr [--procesos 2] [--hilos 8]   pasa OCR a las páginas sin texto (se puede cortar y seguir)
  python biblioteca.py indice                          rehace Buscador\\datos.js (lo que haya leído hasta ahora)
  python biblioteca.py buscar tresillo "3-3-2" ...     busca desde la consola (para Claude), con enlaces file:///
  python biblioteca.py estado                          cuántas páginas faltan

Qué entra:
  LIBROS (texto completo, con OCR si es escaneo): Libros tango, Instagram\\documentacion, Analisis tangos\\_referencias
  PARTITURAS (catálogo: nombre, texto de las 2 primeras páginas si lo tiene, y lo que hay dentro de cada .zip/.rar)
Resultado: D:\\Dropbox\\TDJ\\Buscador\\buscar.html (se abre en Chrome) y Buscador\\_textos\\ (lo leído, por libro).
Necesita: pymupdf, easyocr (con el modelo latino ya bajado en ~/.EasyOCR). 7-Zip para mirar dentro de los .rar.
"""
import sys, os, re, json, hashlib, time, argparse, subprocess, zipfile, unicodedata
from pathlib import Path

TDJ = Path(__file__).resolve().parents[4]          # ...\TDJ\PYTHON\tgdj\herramientas\biblioteca
SALIDA = TDJ / "Buscador"
TEXTOS = SALIDA / "_textos"
# (ruta desde TDJ, carpeta o archivo · nombre del grupo en el buscador). Lo repetido (mismo nombre y tamaño) entra una vez.
LIBROS = [("Libros tango", "Libros"),
          (r"Partituras\pdf\sueltas\Cancionero del tango- Hugo Satorre.pdf", "Libros"),
          (r"Instagram\documentacion", "Documentación Instagram"),
          (r"Analisis tangos\_referencias", "Referencias"),
          (r"..\MUSICA", "MUSICA (cursos y métodos)")]
# dentro de esas carpetas, no entra lo que tenga en la ruta alguno de estos trozos (partituras, programas, papeles)
NO_LIBROS = [r"\PARTITURAS PDF", r"\MUSESCORE", r"\MIDI", r"\Software", r"\music_ocr", r"\LMMS", r"\Inkscape",
             r"\guitar pro", r"\Editorial Orquesta Típica", r"\Piano (Editorial)",
             "Canvi de titular", "Activitats-Literatura Medieval"]
PARTITURAS = ["Partituras"]
EXT_LIBRO = {".pdf", ".txt", ".md", ".doc", ".docx"}
MIN_TEXTO = 50          # menos caracteres que esto en una página = escaneo, hay que pasarle OCR
DPI = 200
SIETE_ZIP = [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]


# ---------------------------------------------------------------- utilidades
def url(p: Path) -> str:
    return Path(p).resolve().as_uri()


def limpiar(t: str) -> str:
    t = t.replace("\u00ad", "")
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)     # palabras cortadas a final de línea
    return re.sub(r"\s+", " ", t).strip()


def normal(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def cache_de(rel: str) -> Path:
    h = hashlib.md5(rel.encode("utf-8")).hexdigest()[:8]
    base = re.sub(r"[^\w\- ]", "_", Path(rel).stem)[:60].strip()
    return TEXTOS / f"{base}_{h}.json"


def huella(p: Path):
    s = p.stat()
    return [s.st_size, int(s.st_mtime)]


def guardar(path: Path, datos):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    # Dropbox (o el aviso, que lo está leyendo) puede tener el archivo abierto un momento: reintentar, no caerse
    for intento in range(30):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(1 + intento)
    print("  no se pudo guardar (se queda en .tmp y se reintenta la próxima vez):", path.name, flush=True)


def leer_json(path: Path):
    for intento in range(10):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (PermissionError, json.JSONDecodeError):
            time.sleep(1)
    return json.loads(path.read_text(encoding="utf-8"))


def prioridad_baja():
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL


def relativa(p: Path) -> str:
    return os.path.relpath(p, TDJ)          # «..\MUSICA\...» para lo que está fuera de TDJ


def lista_libros():
    vistos = set()
    for ruta, grupo in LIBROS:
        base = (TDJ / ruta).resolve()
        if not base.exists():
            continue
        for p in ([base] if base.is_file() else sorted(base.rglob("*"))):
            if not p.is_file() or p.suffix.lower() not in EXT_LIBRO or "_textos" in p.parts:
                continue
            if p.name.startswith("~$") or any(x.lower() in str(p).lower() for x in NO_LIBROS):
                continue
            clave = (p.name.lower(), p.stat().st_size)
            if clave in vistos:
                continue
            vistos.add(clave)
            yield grupo, p


# ---------------------------------------------------------------- leer un libro (sin OCR)
def leer_doc_word(p: Path) -> str:
    """.doc/.docx con Word (si está instalado)."""
    destino = TEXTOS / ("_word_" + hashlib.md5(str(p).encode()).hexdigest()[:8] + ".txt")
    ps = (f"$w=New-Object -ComObject Word.Application; $w.Visible=$false; "
          f"$d=$w.Documents.Open('{p}', $false, $true); $d.SaveAs2('{destino}', 7, $false, '', $false, '', $false, $false, $false, $false, $false, 65001); "
          f"$d.Close($false); $w.Quit()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=120, capture_output=True)
        t = destino.read_text(encoding="utf-8", errors="replace")
        destino.unlink()
        return t
    except Exception as e:
        print("  no se pudo leer con Word:", p.name, e)
        return ""


def preparar(carpeta, p: Path):
    """Crea/actualiza la caché del libro con el texto que ya trae. Devuelve la caché."""
    rel = relativa(p)
    c = cache_de(rel)
    if c.exists():
        d = leer_json(c)
        if d.get("huella") == huella(p):
            return c, d
    d = {"archivo": rel, "grupo": carpeta, "huella": huella(p), "paginas": []}
    ext = p.suffix.lower()
    if ext == ".pdf":
        import pymupdf
        doc = pymupdf.open(p)
        for pag in doc:
            t = limpiar(pag.get_text())
            d["paginas"].append({"t": t, "ocr": None if len(t) >= MIN_TEXTO else "falta"})
    else:
        t = p.read_text(encoding="utf-8", errors="replace") if ext in (".txt", ".md") else leer_doc_word(p)
        t = limpiar(t)
        # los textos largos (Word, txt) se parten en trozos de ~3000 letras, que hacen de «páginas»
        i = 0
        while i < len(t) or not d["paginas"]:
            j = min(len(t), i + 3000)
            if j < len(t):
                k = t.rfind(". ", i + 2000, j)
                j = k + 1 if k > 0 else j
            d["paginas"].append({"t": t[i:j].strip(), "ocr": None})
            i = j
            if not t:
                break
    guardar(c, d)
    return c, d


# ---------------------------------------------------------------- OCR
_lector = None


def _iniciar(hilos):
    global _lector
    prioridad_baja()
    import torch, easyocr, warnings
    warnings.filterwarnings("ignore")
    torch.set_num_threads(hilos)
    _lector = easyocr.Reader(["es", "en"], gpu=False, verbose=False)


def _ocr_libro(cache_path):
    import pymupdf, numpy as np
    c = Path(cache_path)
    d = leer_json(c)
    doc = pymupdf.open(TDJ / d["archivo"])
    hechas, t0 = 0, time.time()
    for i, pag in enumerate(d["paginas"]):
        if pag["ocr"] != "falta":
            continue
        pix = doc[i].get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
        try:
            trozos = _lector.readtext(img, detail=0, paragraph=True)
        except Exception as e:
            trozos = []
            print("  error en", d["archivo"], "pág", i + 1, e, flush=True)
        pag["t"] = limpiar("\n".join(trozos))
        pag["ocr"] = "easyocr"
        hechas += 1
        if hechas % 5 == 0:
            guardar(c, d)
    guardar(c, d)
    return d["archivo"], hechas, time.time() - t0


def cmd_ocr(a):
    TEXTOS.mkdir(parents=True, exist_ok=True)
    pendientes = []
    for carpeta, p in lista_libros():
        c, d = preparar(carpeta, p)
        n = sum(1 for x in d["paginas"] if x["ocr"] == "falta")
        if n:
            pendientes.append((n, str(c)))
    pendientes.sort(reverse=True)
    total = sum(n for n, _ in pendientes)
    print(f"{len(pendientes)} libros con {total} páginas sin texto", flush=True)
    if total:
        import threading
        parar = threading.Event()

        def avisar():                       # ESTADO_OCR.txt cada 5 minutos
            while not parar.wait(300):
                try:
                    escribir_aviso()
                except Exception as e:
                    print("  aviso:", e, flush=True)
        escribir_aviso()
        threading.Thread(target=avisar, daemon=True).start()
        from multiprocessing import Pool
        hechas = 0
        with Pool(a.procesos, initializer=_iniciar, initargs=(a.hilos,)) as pool:
            for arch, n, seg in pool.imap_unordered(_ocr_libro, [c for _, c in pendientes]):
                hechas += n
                print(f"  listo ({hechas}/{total}): {arch}  {n} págs en {seg/60:.0f} min", flush=True)
        parar.set()
    cmd_indice(a)
    escribir_aviso(fin=True)


AVISO = SALIDA / "ESTADO_OCR.txt"      # se ve desde cualquier PC por Dropbox


def contar():
    filas, leidas, faltan = [], 0, 0
    for carpeta, p in lista_libros():
        c = cache_de(relativa(p))
        if not c.exists():
            continue
        d = leer_json(c)
        f = sum(1 for x in d["paginas"] if x["ocr"] == "falta")
        o = sum(1 for x in d["paginas"] if x["ocr"] == "easyocr")
        leidas += o; faltan += f
        if f or o:
            filas.append((o, f, p.name))
    return filas, leidas, faltan


def escribir_aviso(fin=False, extra=""):
    """ESTADO_OCR.txt: porcentaje, libros y hora estimada de fin (la velocidad sale de la medida anterior)."""
    filas, leidas, faltan = contar()
    total = leidas + faltan
    pct = 100 * leidas / total if total else 100
    hist = TEXTOS / "_ritmo_ocr.json"
    ahora = time.time()
    try:
        h = json.loads(hist.read_text(encoding="utf-8"))
    except Exception:
        h = {}
    eta = ""
    if h.get("t") and leidas > h.get("leidas", 0) and ahora > h["t"]:
        vel = (leidas - h["leidas"]) / ((ahora - h["t"]) / 60)          # páginas por minuto
        if faltan and vel > 0:
            eta = f"Ritmo: {vel:.1f} págs/min → acaba hacia las {time.strftime('%H:%M', time.localtime(ahora + faltan / vel * 60))}"
    if not h.get("t") or ahora - h["t"] > 240:
        guardar(hist, {"t": ahora, "leidas": leidas})
    lineas = [f"OCR DE LOS LIBROS · actualizado {time.strftime('%d-%m-%Y %H:%M')}", ""]
    if fin or not faltan:
        lineas += ["*** TERMINADO ***", f"{leidas} páginas leídas con OCR. El buscador ya está al día:",
                   url(SALIDA / "buscar.html"), ""]
    else:
        lineas += [f"{pct:.0f} % · {leidas} de {total} páginas · faltan {faltan}", eta,
                   "(Se renueva cada 5 minutos. Si esta hora tiene más de 20 minutos, el OCR se ha parado:",
                   " relanzarlo con «biblioteca.py ocr», sigue donde lo dejó.)", ""]
    if extra:
        lineas += [extra, ""]
    lineas += ["Libro por libro (leídas / faltan):"]
    for o, f, n in sorted(filas, key=lambda x: (x[1] == 0, -x[1])):
        lineas.append(f"  {'listo' if not f else f'{100*o/(o+f):3.0f} %':>6}  {o:4} / {f:4}  {n}")
    SALIDA.mkdir(parents=True, exist_ok=True)
    AVISO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return leidas, faltan


def cmd_estado(a):
    if a.aviso:
        escribir_aviso(extra=a.extra or "")
        print(AVISO.read_text(encoding="utf-8"))
        return
    filas, leidas, faltan = contar()
    for o, f, n in filas:
        print(f"  {o:4} leídas, {f:4} faltan | {n}")
    print(f"Total OCR: {leidas} leídas, faltan {faltan}")


# ---------------------------------------------------------------- partituras (catálogo)
def siete_zip():
    for x in SIETE_ZIP:
        if Path(x).exists():
            return x


def dentro_de(p: Path):
    try:
        if p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as z:
                return [n for n in z.namelist() if not n.endswith("/")]
        sz = siete_zip()
        if sz:
            r = subprocess.run([sz, "l", "-slt", "-ba", str(p)], capture_output=True, timeout=60)
            txt = r.stdout.decode("utf-8", errors="replace")
            return [l[7:] for l in txt.splitlines() if l.startswith("Path = ")]
    except Exception:
        pass
    return []


def catalogo_partituras():
    TEXTOS.mkdir(parents=True, exist_ok=True)
    cpath = TEXTOS / "_partituras.json"
    viejo = leer_json(cpath) if cpath.exists() else {}
    nuevo = {}
    import pymupdf
    for carpeta in PARTITURAS:
        for p in sorted((TDJ / carpeta).rglob("*")):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext not in (".pdf", ".zip", ".rar", ".mscz", ".mid", ".sib", ".mxl", ".musicxml", ".xml"):
                continue
            rel = relativa(p)
            hu = huella(p)
            if rel in viejo and viejo[rel]["huella"] == hu:
                nuevo[rel] = viejo[rel]
                continue
            extra = ""
            if ext == ".pdf":
                try:
                    doc = pymupdf.open(p)
                    extra = limpiar(" ".join(doc[i].get_text() for i in range(min(2, len(doc)))))[:1500]
                    n = len(doc)
                except Exception:
                    n = 0
            elif ext in (".zip", ".rar"):
                extra = " | ".join(dentro_de(p))
                n = 0
            else:
                n = 0
            nuevo[rel] = {"huella": hu, "paginas": n, "t": extra}
    guardar(cpath, nuevo)
    return nuevo


# ---------------------------------------------------------------- índice + página
def cmd_indice(a):
    TEXTOS.mkdir(parents=True, exist_ok=True)
    docs = []
    for carpeta, p in lista_libros():
        c, d = preparar(carpeta, p)
        falta = sum(1 for x in d["paginas"] if x["ocr"] == "falta")
        ocr = sum(1 for x in d["paginas"] if x["ocr"] == "easyocr")
        docs.append({"g": carpeta, "n": p.name, "u": url(p), "pdf": p.suffix.lower() == ".pdf",
                     "ocr": ocr, "falta": falta, "p": [x["t"] for x in d["paginas"]]})
    part = catalogo_partituras()
    for rel, x in part.items():
        p = TDJ / rel
        sub = str(Path(rel).parent.relative_to("Partituras")) if rel.startswith("Partituras") else ""
        docs.append({"g": "Partituras", "n": p.name, "u": url(p), "pdf": p.suffix.lower() == ".pdf",
                     "sub": sub, "ocr": 0, "falta": 0,
                     "p": [f"{sub} / {p.name} {x['t']}".strip()]})
    js = "window.BIBLIOTECA = " + json.dumps({"hecho": time.strftime("%d-%m-%Y %H:%M"), "docs": docs},
                                             ensure_ascii=False, separators=(",", ":")) + ";\n"
    (SALIDA / "datos.js").write_text(js, encoding="utf-8")
    plantilla = Path(__file__).with_name("buscar_plantilla.html").read_text(encoding="utf-8")
    (SALIDA / "buscar.html").write_text(plantilla, encoding="utf-8")
    nlib = sum(1 for d in docs if d["g"] != "Partituras")
    print(f"Índice: {nlib} libros/documentos, {len(docs)-nlib} partituras · {len(js)/2**20:.1f} MB")
    print("Buscador:", url(SALIDA / "buscar.html"))


# ---------------------------------------------------------------- buscar desde la consola
def cmd_buscar(a):
    frases = [normal(x) for x in a.palabras]
    hay = 0
    for carpeta, p in lista_libros():
        c = cache_de(relativa(p))
        if not c.exists():
            continue
        d = leer_json(c)
        aciertos = []
        for i, pag in enumerate(d["paginas"]):
            tn = normal(pag["t"])
            if any(f in tn for f in frases):
                f = next(f for f in frases if f in tn)
                k = tn.find(f)
                trozo = pag["t"][max(0, k - a.contexto): k + len(f) + a.contexto]
                aciertos.append((i + 1, trozo))
        if aciertos:
            hay += len(aciertos)
            print(f"\n## {p.name}  ({len(aciertos)} págs)")
            for n, trozo in aciertos[: a.max]:
                ancla = f"#page={n}" if p.suffix.lower() == ".pdf" else ""
                print(f"- [pág {n}]({url(p)}{ancla}): …{trozo}…")
    if a.partituras:
        part = json.loads((TEXTOS / "_partituras.json").read_text(encoding="utf-8"))
        for rel, x in part.items():
            if any(f in normal(rel + " " + x["t"]) for f in frases):
                hay += 1
                print(f"- [{rel}]({url(TDJ / rel)})")
    print(f"\n{hay} aciertos")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    o = sp.add_parser("ocr"); o.add_argument("--procesos", type=int, default=2); o.add_argument("--hilos", type=int, default=8)
    sp.add_parser("indice")
    e = sp.add_parser("estado"); e.add_argument("--aviso", action="store_true", help="escribe Buscador\\ESTADO_OCR.txt")
    e.add_argument("--extra", help="frase que se añade al aviso")
    b = sp.add_parser("buscar"); b.add_argument("palabras", nargs="+")
    b.add_argument("--max", type=int, default=8); b.add_argument("--contexto", type=int, default=150)
    b.add_argument("--partituras", action="store_true")
    a = ap.parse_args()
    {"ocr": cmd_ocr, "indice": cmd_indice, "estado": cmd_estado, "buscar": cmd_buscar}[a.cmd](a)
