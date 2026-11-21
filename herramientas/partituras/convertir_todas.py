"""Pasa TODAS las partituras de tango (PDF e imágenes) a MusicXML + MIDI con Audiveris. Se puede cortar y seguir.

Uso:  python convertir_todas.py              (sigue donde lo dejó; en segundo plano, prioridad baja)
      python convertir_todas.py --contar     (solo cuenta lo que hay y lo que falta, y calcula el tiempo)
      python convertir_todas.py --reintentar (vuelve a probar las que fallaron)
Procesos a la vez: el número de  Partituras\\convertidas\\todas\\PROCESOS.txt  (se puede cambiar sin parar: lo relee
cada poco). Empieza con 2.

Orden: 1) PDF hechos con ordenador, 2) PDF escaneados, 3) imágenes sueltas (.jpg .tif), 4) imágenes de dentro de
los .zip/.rar. Las imágenes pequeñas (< 2000 px de alto) se agrandan antes ×2 o ×3 (si no, Audiveris no las lee).
Fuera: los .sib (Sibelius), lo de Chopin y lo ya convertido.

Salida: Partituras\\convertidas\\todas\\<misma ruta que el original>.mxl + .mid
        (lo de dentro de un .zip/.rar: <ruta del zip>\\<nombre de dentro>.mxl)
Estado: Partituras\\ESTADO_PARTITURAS.txt  (porcentaje, hora estimada de fin, «TERMINADO»; cada 3 minutos)
        convertidas\\todas\\_estado.json  (qué está hecho: bien / dudosa / falla, con motivos; NO borrar)
        convertidas\\todas\\REVISAR.txt   (las dudosas y las que fallan, por grupo)
Solo en un PC a la vez: convertidas\\todas\\_EN_MARCHA.txt lleva el nombre del PC y la hora; si otro PC lo ha
tocado hace menos de 15 min, no arranca.
"""
import json
import math
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comprobar_mxl import comprobar  # noqa: E402
from convertir_partituras import AUDIVERIS, buscar_musescore, nombrar_parte  # noqa: E402

PARTITURAS = Path(r"D:\Dropbox\TDJ\Partituras")
ORIGEN = PARTITURAS / "pdf"
SALIDA = PARTITURAS / "convertidas" / "todas"
ESTADO_TXT = PARTITURAS / "ESTADO_PARTITURAS.txt"
ESTADO_JSON = SALIDA / "_estado.json"
LISTA_JSON = SALIDA / "_lista.json"
PROCESOS_TXT = SALIDA / "PROCESOS.txt"
EN_MARCHA = SALIDA / "_EN_MARCHA.txt"
REVISAR = SALIDA / "REVISAR.txt"
CATALOGO = Path(r"D:\Dropbox\TDJ\Buscador\_textos\_partituras.json")
SIETE_ZIP = Path(r"C:\Program Files\7-Zip\7z.exe")
IMAGEN = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif", ".bmp")
# Fuera: Chopin, los documentos de Community Tango Orchestra y el cancionero de Satorre (son texto, no partituras)
FUERA = ("chopin", "\\documents\\", "cancionero del tango")
GRUPOS = {1: "PDF hechos con ordenador", 2: "PDF escaneados", 3: "imágenes sueltas", 4: "imágenes de los .zip/.rar"}
SEG_POR_PAGINA = 45          # para la primera estimación (medido el 18-11-2026 con 1 proceso)
TIEMPO_MAX = 40 * 60         # por partitura, o 4 min por página si es más (luego se da por fallida)
BAJA = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
OCULTA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def rel(p: Path) -> str:
    return str(p.relative_to(ORIGEN))


def reemplazar(tmp: Path, ruta: Path):
    """os.replace con reintentos: Dropbox bloquea el archivo unos segundos mientras lo sube."""
    for i in range(60):
        try:
            os.replace(tmp, ruta)
            return
        except PermissionError:
            time.sleep(1 + i % 5)
    os.replace(tmp, ruta)


def guardar_json(ruta: Path, datos):
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=0), encoding="utf-8")
    reemplazar(tmp, ruta)


def leer_json(ruta: Path, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return defecto


# ------------------------------------------------------------------ lista de trabajos
def dentro_de(archivo: Path):
    r = subprocess.run([str(SIETE_ZIP), "l", "-slt", "-ba", str(archivo)], capture_output=True, timeout=120,
                       creationflags=OCULTA)
    txt = r.stdout.decode("utf-8", errors="replace")
    return [ln[7:] for ln in txt.splitlines() if ln.startswith("Path = ")]


def hacer_lista():
    """Todos los trabajos, con grupo y páginas. Se guarda en _lista.json y solo se rehace si cambia Partituras."""
    import pymupdf
    catalogo = leer_json(CATALOGO, {})
    trabajos = []
    for p in sorted(ORIGEN.rglob("*")):
        if not p.is_file() or any(f in str(p).lower() for f in FUERA):
            continue
        ext = p.suffix.lower()
        if ext == ".pdf":
            info = catalogo.get(str(p.relative_to(PARTITURAS.parent)))
            if info and "paginas" in info:
                texto, paginas = len(info["t"].strip()) >= 20, info["paginas"]
            else:
                try:
                    doc = pymupdf.open(p)
                    paginas = len(doc)
                    texto = len("".join(doc[i].get_text() for i in range(min(2, paginas))).strip()) >= 20
                except Exception:  # noqa: BLE001
                    paginas, texto = 1, False
            trabajos.append({"id": rel(p), "grupo": 1 if texto else 2, "paginas": max(1, paginas)})
        elif ext in IMAGEN:
            trabajos.append({"id": rel(p), "grupo": 3, "paginas": 1})
        elif ext in (".zip", ".rar"):
            try:
                nombres = dentro_de(p)
            except Exception:  # noqa: BLE001
                nombres = []
            for n in nombres:
                if Path(n).suffix.lower() in IMAGEN + (".pdf",):
                    trabajos.append({"id": rel(p) + "|" + n, "grupo": 4, "paginas": 1})
    trabajos.sort(key=lambda t: (t["grupo"], t["id"].lower()))
    return trabajos


def destino_de(t) -> Path:
    if "|" in t["id"]:
        arch, dentro = t["id"].split("|", 1)
        return SALIDA / arch / (str(Path(dentro).with_suffix("")) + ".mxl")
    return SALIDA / (str(Path(t["id"]).with_suffix("")) + ".mxl")


# ------------------------------------------------------------------ un trabajo
def preparar_entrada(t, tmp: Path) -> Path:
    """Ruta del archivo que verá Audiveris (sacado del zip y agrandado si es una imagen pequeña)."""
    if "|" in t["id"]:
        arch, dentro = t["id"].split("|", 1)
        subprocess.run([str(SIETE_ZIP), "e", "-y", f"-o{tmp}", str(ORIGEN / arch), dentro],
                       capture_output=True, timeout=300, creationflags=OCULTA)
        entrada = tmp / Path(dentro).name
    else:
        entrada = ORIGEN / t["id"]
    if entrada.suffix.lower() in IMAGEN:
        from PIL import Image
        try:
            im = Image.open(entrada)
            if im.height < 2000:
                f = min(3, math.ceil(2400 / im.height))
                grande = tmp / (entrada.stem + "_grande.png")
                im.convert("L").resize((im.width * f, im.height * f), Image.LANCZOS).save(grande)
                return grande
        except Exception:  # noqa: BLE001
            pass
    return entrada


def lanzar(t, carpeta_tmp: Path):
    tmp = Path(tempfile.mkdtemp(prefix="aud_", dir=carpeta_tmp))
    entrada = preparar_entrada(t, tmp)
    log = open(tmp / "audiveris.log", "w", encoding="utf-8", errors="replace")
    env = {**os.environ, "JAVA_TOOL_OPTIONS": "-Djava.util.Arrays.useLegacyMergeSort=true",
           "TESSDATA_PREFIX": str(AUDIVERIS.parent.parent / "tessdata")}
    proc = subprocess.Popen([str(AUDIVERIS), "-batch", "-constant", "org.audiveris.omr.Main.sheetStepTimeOut=1200",
                             "-export", "-output", str(tmp / "sal"), "--", str(entrada)],
                            stdout=log, stderr=subprocess.STDOUT, env=env, creationflags=BAJA | OCULTA)
    return {"t": t, "proc": proc, "tmp": tmp, "log": log, "inicio": time.time(), "entrada": entrada}


def terminar(job, musescore):
    """Recoge lo que hizo Audiveris: copia, nombra la parte, saca el MIDI y comprueba. Devuelve el registro."""
    t, tmp = job["t"], job["tmp"]
    job["log"].close()
    seg = round(time.time() - job["inicio"])
    salidas = sorted((tmp / "sal").glob("*.mxl")) if (tmp / "sal").exists() else []
    reg = {"grupo": t["grupo"], "paginas": t["paginas"], "seg": seg}
    if not salidas:
        motivo = "Audiveris no sacó nada"
        try:
            txt = (tmp / "audiveris.log").read_text(encoding="utf-8", errors="replace")
            if "Sheet ignored" in txt:
                motivo = "Audiveris no la reconoce como partitura (imagen mala o pequeña)"
            elif "TimeoutException" in txt:
                motivo = "tarda demasiado"
        except Exception:  # noqa: BLE001
            pass
        reg.update(r="falla", motivos=[motivo])
    else:
        destino = destino_de(t)
        destino.parent.mkdir(parents=True, exist_ok=True)
        hechos = []
        for i, o in enumerate(salidas):
            d = destino if i == 0 else destino.with_name(destino.stem + f".mvt{i + 1}.mxl")
            shutil.copyfile(o, d)
            instrumento = Path(t["id"].split("|")[-1]).stem.rsplit(" - ", 1)[-1].strip()
            try:
                nombrar_parte(d, Path(t["id"].split("|")[-1]).stem)
            except Exception:  # noqa: BLE001
                pass
            mid = d.with_suffix(".mid")
            try:
                subprocess.run([str(musescore), "-o", str(mid), str(d)], capture_output=True, timeout=300,
                               creationflags=BAJA | OCULTA)
            except Exception:  # noqa: BLE001
                pass
            v, motivos, datos = comprobar(d, instrumento)
            if not mid.exists():
                v, motivos = "dudosa", motivos + ["MuseScore no pudo sacar el .mid"]
            hechos.append((d, v, motivos, datos))
        malas = [h for h in hechos if h[1] != "bien"]
        reg.update(r="dudosa" if malas else "bien",
                   motivos=[m for h in hechos for m in h[2]],
                   compases=sum(h[3].get("compases", 0) for h in hechos),
                   salida=str(destino.relative_to(SALIDA)), trozos=len(hechos))
    shutil.rmtree(tmp, ignore_errors=True)
    return reg


# ------------------------------------------------------------------ estado
def escribir_estado(trabajos, estado, procesos, en_curso, inicio_sesion, hechas_sesion_pag, fin=False):
    total_pag = sum(t["paginas"] for t in trabajos)
    hechas_pag = sum(estado[t["id"]]["paginas"] for t in trabajos if t["id"] in estado)
    faltan_pag = total_pag - hechas_pag
    ahora = datetime.now()
    horas = (time.time() - inicio_sesion) / 3600
    if hechas_sesion_pag >= 20 and horas > 0:
        ritmo = hechas_sesion_pag / horas
        de_donde = "medido en esta tanda"
    else:
        ritmo = 3600 / SEG_POR_PAGINA * max(1, procesos)
        de_donde = f"estimado ({SEG_POR_PAGINA} s por página y proceso)"
    eta = ahora + timedelta(hours=faltan_pag / ritmo) if ritmo and faltan_pag else ahora
    lin = []
    lin.append("TERMINADO" if fin else "EN MARCHA (se puede cortar: al relanzar sigue donde lo dejó)")
    lin.append(f"Partituras → MusicXML con Audiveris · {ahora:%d-%m-%Y %H:%M} · PC {socket.gethostname()}")
    lin.append("")
    lin.append(f"Hecho: {hechas_pag} de {total_pag} páginas ({100 * hechas_pag / max(1, total_pag):.1f} %)")
    if not fin:
        lin.append(f"Ritmo: {ritmo:.0f} páginas/hora ({de_donde}), {procesos} procesos a la vez")
        lin.append(f"Fin estimado: {eta:%A %d-%m %H:%M}".replace("Monday", "lunes").replace("Tuesday", "martes")
                   .replace("Wednesday", "miércoles").replace("Thursday", "jueves").replace("Friday", "viernes")
                   .replace("Saturday", "sábado").replace("Sunday", "domingo"))
    lin.append("")
    lin.append(f"{'grupo':30} {'hechas':>8} {'de':>6}   bien  dudosas  fallan")
    for g, nombre in GRUPOS.items():
        ts = [t for t in trabajos if t["grupo"] == g]
        rs = [estado[t["id"]]["r"] for t in ts if t["id"] in estado]
        lin.append(f"{nombre:30} {len(rs):8} {len(ts):6}   {rs.count('bien'):4}  {rs.count('dudosa'):7}  "
                   f"{rs.count('falla'):6}")
    if en_curso:
        lin.append("")
        lin.append("Ahora mismo:")
        for j in en_curso:
            lin.append(f"  {j['t']['id']}  ({round((time.time() - j['inicio']) / 60)} min)")
    lin.append("")
    lin.append(f"Resultados: {SALIDA.as_uri()}   ·   Para revisar: {REVISAR.as_uri()}")
    lin.append("bien = pasa la comprobación automática (comprobar_mxl.py); dudosa = mirarla; falla = no salió nada.")
    tmp = ESTADO_TXT.with_suffix(".tmp")
    tmp.write_text("\n".join(lin) + "\n", encoding="utf-8")
    reemplazar(tmp, ESTADO_TXT)
    # lista para revisar
    rev = []
    for g, nombre in GRUPOS.items():
        malas = [(t["id"], estado[t["id"]]) for t in trabajos if t["grupo"] == g and t["id"] in estado
                 and estado[t["id"]]["r"] != "bien"]
        if malas:
            rev.append(f"== {nombre}: {len(malas)}")
            for i, e in malas:
                rev.append(f"{e['r'].upper():7} {i}  ·  " + "; ".join(e.get("motivos", [])))
            rev.append("")
    REVISAR.write_text("\n".join(rev) + "\n", encoding="utf-8")


def tomar_turno():
    if EN_MARCHA.exists():
        try:
            pc, cuando = EN_MARCHA.read_text(encoding="utf-8").split("|")[:2]
            if pc != socket.gethostname() and time.time() - float(cuando) < 15 * 60:
                sys.exit(f"Ya está en marcha en el PC «{pc}». Solo en un PC a la vez.")
        except ValueError:
            pass
    EN_MARCHA.write_text(f"{socket.gethostname()}|{time.time()}|{datetime.now():%d-%m-%Y %H:%M}", encoding="utf-8")


def procesos_pedidos():
    try:
        return max(0, min(8, int(PROCESOS_TXT.read_text(encoding="utf-8").split()[0])))
    except Exception:  # noqa: BLE001
        return 2


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    if not PROCESOS_TXT.exists():
        PROCESOS_TXT.write_text("2\n\nProcesos de Audiveris a la vez (0 = parar al acabar los que están en marcha).\n"
                                "Se puede cambiar sin parar el programa: lo relee cada poco.\n", encoding="utf-8")
    lista = leer_json(LISTA_JSON, None)
    if lista is None or "--relistar" in sys.argv:
        print("Haciendo la lista de partituras (una vez)...", flush=True)
        lista = hacer_lista()
        guardar_json(LISTA_JSON, lista)
    lista = [t for t in lista if not any(f in t["id"].lower() for f in FUERA)]
    estado = leer_json(ESTADO_JSON, {})
    if "--reintentar" in sys.argv:
        estado = {k: v for k, v in estado.items() if v["r"] != "falla"}
    pend = [t for t in lista if t["id"] not in estado]

    if "--contar" in sys.argv:
        for g, nombre in GRUPOS.items():
            ts = [t for t in lista if t["grupo"] == g]
            print(f"{nombre:30} {len(ts):5} archivos  {sum(t['paginas'] for t in ts):6} páginas   "
                  f"faltan {sum(1 for t in ts if t['id'] not in estado)}")
        pag = sum(t["paginas"] for t in pend)
        for n in (1, 2, 3, 4):
            print(f"  con {n} procesos: ~{pag * SEG_POR_PAGINA / n / 3600:.0f} h")
        return

    tomar_turno()
    musescore = buscar_musescore()
    carpeta_tmp = Path(tempfile.gettempdir()) / "convertir_todas"
    shutil.rmtree(carpeta_tmp, ignore_errors=True)
    carpeta_tmp.mkdir(parents=True, exist_ok=True)
    en_curso = []
    inicio = time.time()
    pag_sesion = 0
    ultimo_estado = 0
    print(f"Faltan {len(pend)} partituras. Estado: {ESTADO_TXT.as_uri()}", flush=True)
    while pend or en_curso:
        n = procesos_pedidos()
        while pend and len(en_curso) < n:
            t = pend.pop(0)
            try:
                en_curso.append(lanzar(t, carpeta_tmp))
            except Exception as e:  # noqa: BLE001
                estado[t["id"]] = {"r": "falla", "grupo": t["grupo"], "paginas": t["paginas"], "seg": 0,
                                   "motivos": [f"no se pudo preparar ({e.__class__.__name__})"]}
                guardar_json(ESTADO_JSON, estado)
        if n == 0 and not en_curso:
            break
        for job in list(en_curso):
            vivo = job["proc"].poll() is None
            if vivo and time.time() - job["inicio"] > max(TIEMPO_MAX, 240 * job["t"]["paginas"]):
                job["proc"].kill()
                job["proc"].wait()
                vivo = False
            if not vivo:
                en_curso.remove(job)
                try:
                    reg = terminar(job, musescore)
                except Exception as e:  # noqa: BLE001
                    reg = {"r": "falla", "grupo": job["t"]["grupo"], "paginas": job["t"]["paginas"],
                           "seg": 0, "motivos": [f"error al recoger ({e.__class__.__name__}: {e})"]}
                estado[job["t"]["id"]] = reg
                pag_sesion += job["t"]["paginas"]
                guardar_json(ESTADO_JSON, estado)
                print(f"{reg['r']:7} {reg['seg']:5}s  {job['t']['id']}", flush=True)
        if time.time() - ultimo_estado > 180:
            try:            # el estado no es vital: si Dropbox lo tiene bloqueado, ya se escribirá la próxima vez
                escribir_estado(lista, estado, n, en_curso, inicio, pag_sesion)
                tomar_turno()
            except OSError as e:
                print("  (no se pudo escribir el estado:", e, ")", flush=True)
            ultimo_estado = time.time()
        time.sleep(3)
    fin = not [t for t in lista if t["id"] not in estado]
    escribir_estado(lista, estado, procesos_pedidos(), [], inicio, pag_sesion, fin=fin)
    if fin or EN_MARCHA.exists():
        EN_MARCHA.unlink(missing_ok=True)
    print("TERMINADO" if fin else "Parado (quedan partituras: al relanzar sigue).", flush=True)


if __name__ == "__main__":
    main()
