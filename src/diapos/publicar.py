"""
Publicar la presentación web en internet (GitHub Pages) con un clic, sin pedírselo a nadie.

    url = publicar([presentación.html, lista.html, sw.js, …], titulo="Milonga Mia 13/10/2026")

- Usa git (tiene que estar instalado y con permiso para subir al repositorio, el de config).
- Copia local del repositorio en carpeta_repo_presentaciones (se clona sola la primera vez y se pone al día
  antes de cada subida, por si se publicó desde otro ordenador).
- Rehace index.html: la página con todas las milongas publicadas (pantalla grande y lista de cada noche).
"""
import html as h
import os
import re
import shutil
import subprocess

from src.config.config import (carpeta_anuncios, carpeta_repo_presentaciones, foto_dj, frase_dj, instagram_dj,
                               repo_presentaciones_web, url_presentaciones_web)
from src.diapos.generador import FIRMA_DJ


class ErrorPublicar(Exception):
    pass


def _git(carpeta, *args):
    try:
        r = subprocess.run(["git", *args], cwd=carpeta, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=600)
    except FileNotFoundError:
        raise ErrorPublicar("No está instalado Git (https://git-scm.com).")
    except subprocess.TimeoutExpired:
        raise ErrorPublicar("Git tarda demasiado: ¿hay internet?")
    if r.returncode:
        raise ErrorPublicar(f"git {' '.join(args)}:\n{(r.stderr or r.stdout).strip()}")
    return r.stdout


def preparar(carpeta=carpeta_repo_presentaciones, remoto=repo_presentaciones_web):
    """Copia local del repositorio: la clona si no está y si no, la pone al día."""
    if not os.path.isdir(os.path.join(carpeta, ".git")):
        os.makedirs(os.path.dirname(carpeta), exist_ok=True)
        _git(os.path.dirname(carpeta), "clone", remoto, carpeta)
    else:
        _git(carpeta, "pull", "--rebase", "--quiet")
    return carpeta


def _titulo(ruta):
    """El <title> de una página (leyendo solo el principio: las presentaciones pesan varios MB)."""
    with open(ruta, encoding="utf-8", errors="replace") as f:
        m = re.search(r"<title>(.*?)</title>", f.read(4096), re.S)
    return h.unescape(m.group(1).strip()) if m else os.path.basename(ruta)


def _reducir(origen, destino, lado):
    """Copia ligera de una foto (lado mayor = lado px, JPEG) para la web."""
    from PIL import Image, ImageOps
    with Image.open(origen) as im:
        im.draft("RGB", (lado * 2, lado * 2))
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((lado, lado))
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        im.save(destino, "JPEG", quality=82, optimize=True, progressive=True)
    return destino


def _compacto(texto):
    from unidecode import unidecode
    return re.sub(r"[^a-z]", "", unidecode(texto).lower())


def _comun(a, b):
    """Largo del trozo común más largo ('eldesbande' y 'desbande' -> 8)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b)).size


def buscar_cartel(clave, anuncios=carpeta_anuncios, dias=3):
    """El cartel de una noche ('240920-milonga-mia'): «AAMMDD_lugar.jpg» de esa fecha (o de pocos días antes o
    después: a veces el cartel lleva otra fecha) y con el nombre que más se parezca. None si no hay."""
    import datetime as dt
    if not os.path.isdir(anuncios):
        return None
    fecha = dt.datetime.strptime(clave[:6], "%y%m%d").date()
    nombre = _compacto(clave[7:])
    mejor = None
    for a in sorted(os.listdir(anuncios)):                 # 240818_Arrabal antes que 240818 Arrabal_2
        m = re.match(r"(\d{6})[ _-]*(.*)\.(jpe?g|png|jfif|webp)$", a, re.I)
        if not m:
            continue
        try:
            distancia = abs((dt.datetime.strptime(m.group(1), "%y%m%d").date() - fecha).days)
        except ValueError:
            continue
        parecido = _comun(nombre, _compacto(m.group(2)))
        if distancia <= dias and parecido >= min(5, len(nombre)):
            puntos = (parecido, -distancia, -len(a))          # a igualdad, «Arrabal» antes que «Arrabal_2»
            if mejor is None or puntos > mejor[0]:
                mejor = (puntos, os.path.join(anuncios, a))
    return mejor and mejor[1]


def poner_fotos(carpeta, anuncios=carpeta_anuncios, foto=foto_dj):
    """carteles/AAMMDD-lugar.jpg (el cartel de cada noche publicada, si lo hay) y foto-dj.jpg. Devuelve los nuevos."""
    nuevos = []
    for n in os.listdir(carpeta):
        m = re.match(r"(\d{6}-.+)-lista\.html$", n)
        destino = m and os.path.join(carpeta, "carteles", m.group(1) + ".jpg")
        cartel = m and not os.path.exists(destino) and buscar_cartel(m.group(1), anuncios)
        if cartel:
            try:
                nuevos.append(os.path.relpath(_reducir(cartel, destino, 720), carpeta).replace("\\", "/"))
            except OSError:
                pass
    destino = os.path.join(carpeta, "foto-dj.jpg")
    if foto and os.path.exists(foto) and not os.path.exists(destino):
        try:
            _reducir(foto, destino, 900)
            nuevos.append("foto-dj.jpg")
        except OSError:
            pass
    return nuevos


def crear_indice(carpeta):
    """index.html: la página del DJ (el enlace de su Instagram) con todas las milongas, por años, la más reciente
    arriba. Una noche cuenta si tiene su lista (las pasadas, rehechas de su playlist, no tienen pantalla grande)."""
    noches = {}
    for n in os.listdir(carpeta):
        m = re.match(r"(\d{6})-(.+?)(-lista)?\.html$", n)
        if m:
            noches.setdefault(m.group(1) + "-" + m.group(2), {})["lista" if m.group(3) else "pantalla"] = n
    años, total = {}, 0
    for clave in sorted(noches, reverse=True):
        n = noches[clave]
        if "lista" not in n:
            continue
        total += 1
        titulo = _titulo(os.path.join(carpeta, n["lista"]))
        milonga, _, fecha = titulo.partition(" · ")
        cartel = f"carteles/{clave}.jpg"
        imagen = (f'<img src="{cartel}" alt="" loading="lazy">' if os.path.exists(os.path.join(carpeta, cartel))
                  else f'<span class="sin">{h.escape(milonga[:1])}</span>')
        pantalla = (f' <a class="pantalla" href="{h.escape(n["pantalla"])}">Pantalla grande</a>'
                    if "pantalla" in n else "")
        años.setdefault("20" + clave[:2], []).append(
            f'<a class="noche" href="{h.escape(n["lista"])}">{imagen}<span><b>{h.escape(milonga)}</b>'
            f'<small>{h.escape(fecha)}</small></span></a>{pantalla}')
    bloques = "\n".join(f'<h2>{a}</h2><div class="noches">' + "".join(f"<div>{x}</div>" for x in filas) + "</div>"
                        for a, filas in años.items())
    foto = '<img class="foto" src="foto-dj.jpg" alt="">' if os.path.exists(os.path.join(carpeta, "foto-dj.jpg")) else ""
    with open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDICE.replace("__DJ__", h.escape(FIRMA_DJ)).replace("__FOTO__", foto)
                .replace("__FRASE__", h.escape(frase_dj)).replace("__INSTAGRAM__", h.escape(instagram_dj))
                .replace("__CUANTAS__", f"{total} milonga{'s' if total != 1 else ''}")
                .replace("__NOCHES__", bloques or "<p>Aún no hay ninguna.</p>"))
    return "index.html"


def publicar(archivos, titulo, carpeta=carpeta_repo_presentaciones, remoto=repo_presentaciones_web,
             anuncios=carpeta_anuncios, foto=foto_dj):
    """Sube los archivos (con el cartel de la noche, la foto del DJ y el índice) y devuelve la dirección del primero."""
    preparar(carpeta, remoto)
    nombres = []
    for a in archivos:
        shutil.copyfile(a, os.path.join(carpeta, os.path.basename(a)))
        nombres.append(os.path.basename(a))
    nombres += poner_fotos(carpeta, anuncios, foto)
    nombres.append(crear_indice(carpeta))
    _git(carpeta, "add", "--", *nombres)
    if _git(carpeta, "status", "--porcelain", "--", *nombres).strip():
        _git(carpeta, "commit", "--quiet", "-m", titulo)
        _git(carpeta, "push", "--quiet")
    return url_presentaciones_web + nombres[0]


INDICE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TDJ __DJ__ · Milongas</title><link rel="icon" href="icono-192.png">
<meta name="description" content="TDJ __DJ__, Tango DJ. La música de todas mis milongas, tanda a tanda.">
<meta property="og:title" content="TDJ __DJ__ · Milongas"><meta property="og:image" content="foto-dj.jpg">
<style>
  :root { --fondo:#fbf7f0; --texto:#2a1f17; --suave:#7a6a5c; --tango:#b9852a; --caja:rgba(127,100,70,.09); }
  @media (prefers-color-scheme: dark) { :root { --fondo:#120c08; --texto:#f6efe4; --suave:#b9ab9b; --caja:rgba(185,133,42,.10); } }
  body { margin:0; background:var(--fondo); color:var(--texto); font:16px/1.45 Georgia, "Palatino Linotype", serif; }
  header { padding:28px 16px 4px; text-align:center; }
  .foto { width:150px; height:150px; object-fit:cover; border-radius:50%; border:3px solid var(--tango); }
  h1 { margin:10px 0 0; font-size:32px; } .frase { margin:6px auto 0; color:var(--suave); max-width:460px; }
  .dj { font:600 12px system-ui, sans-serif; letter-spacing:.2em; text-transform:uppercase; color:var(--tango); margin:0; }
  .boton { display:inline-block; margin:14px 4px 0; padding:10px 18px; border-radius:99px; font:600 15px system-ui, sans-serif;
    background:var(--tango); color:#fff; text-decoration:none; }
  main { max-width:720px; margin:0 auto; padding:8px 16px 40px; }
  .intro { text-align:center; color:var(--suave); font-style:italic; margin:18px 0 0; }
  h2 { font-size:22px; margin:26px 0 10px; padding-bottom:4px; border-bottom:1px solid rgba(127,100,70,.3); }
  .noches { display:grid; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr)); gap:10px; }
  .noche { display:flex; align-items:center; gap:12px; padding:8px; border-radius:10px; background:var(--caja);
    color:inherit; text-decoration:none; border-left:5px solid var(--tango); }
  .noche:hover { outline:1px solid var(--tango); }
  .noche img, .noche .sin { width:64px; height:64px; flex:none; border-radius:6px; object-fit:cover; }
  .noche .sin { display:flex; align-items:center; justify-content:center; background:var(--tango); color:#fff; font-size:28px; }
  .noche b { display:block; font-size:18px; } .noche small { color:var(--suave); font:14px system-ui, sans-serif; }
  .pantalla { display:inline-block; margin:4px 0 0 82px; font:600 13px system-ui, sans-serif; color:var(--tango); }
  footer { text-align:center; color:var(--suave); font:14px system-ui, sans-serif; padding:0 16px 32px; }
</style></head>
<body><header>__FOTO__<p class="dj">TDJ</p><h1>__DJ__</h1><p class="frase">__FRASE__</p>
<a class="boton" href="__INSTAGRAM__" target="_blank" rel="noopener">Sígueme en Instagram</a></header>
<main>
<p class="intro">La música de mis milongas (__CUANTAS__). Toca una para ver sus tandas<br>y volver a escuchar los temas en casa.</p>
__NOCHES__
</main>
<footer>Música: TDJ __DJ__</footer></body></html>
"""
