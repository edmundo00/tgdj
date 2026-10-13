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

from src.config.config import carpeta_repo_presentaciones, repo_presentaciones_web, url_presentaciones_web
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


def crear_indice(carpeta):
    """index.html: todas las milongas publicadas, la más reciente arriba."""
    noches = sorted((n for n in os.listdir(carpeta)
                     if re.match(r"\d{6}-.+\.html$", n) and not n.endswith("-lista.html")), reverse=True)
    filas = []
    for n in noches:
        lista = n[:-len(".html")] + "-lista.html"
        enlaces = (f'<a class="boton" href="{h.escape(lista)}">La música</a>' if os.path.exists(os.path.join(carpeta, lista))
                   else "")
        enlaces += f'<a class="boton suave" href="{h.escape(n)}">Pantalla grande</a>'
        filas.append(f'<section><h2>{h.escape(_titulo(os.path.join(carpeta, n)))}</h2><p>{enlaces}</p></section>')
    with open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDICE.replace("__DJ__", h.escape(FIRMA_DJ)).replace("__NOCHES__", "\n".join(filas) or "<p>Aún no hay ninguna.</p>"))
    return "index.html"


def publicar(archivos, titulo, carpeta=carpeta_repo_presentaciones, remoto=repo_presentaciones_web):
    """Sube los archivos (y el índice) y devuelve la dirección del primero."""
    preparar(carpeta, remoto)
    nombres = []
    for a in archivos:
        shutil.copyfile(a, os.path.join(carpeta, os.path.basename(a)))
        nombres.append(os.path.basename(a))
    nombres.append(crear_indice(carpeta))
    _git(carpeta, "add", "--", *nombres)
    if _git(carpeta, "status", "--porcelain", "--", *nombres).strip():
        _git(carpeta, "commit", "--quiet", "-m", titulo)
        _git(carpeta, "push", "--quiet")
    return url_presentaciones_web + nombres[0]


INDICE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Milongas · TDJ __DJ__</title><link rel="icon" href="icono-192.png">
<style>
  :root { --fondo:#fbf7f0; --texto:#2a1f17; --suave:#7a6a5c; --tango:#b9852a; }
  @media (prefers-color-scheme: dark) { :root { --fondo:#120c08; --texto:#f6efe4; --suave:#b9ab9b; } }
  body { margin:0; background:var(--fondo); color:var(--texto); font:16px/1.45 Georgia, "Palatino Linotype", serif; }
  header { padding:32px 16px 8px; text-align:center; }
  h1 { margin:0; font-size:32px; } header p { margin:6px 0 0; color:var(--suave); }
  .dj { font:600 12px system-ui, sans-serif; letter-spacing:.2em; text-transform:uppercase; color:var(--tango); }
  main { max-width:640px; margin:0 auto; padding:0 16px 40px; }
  section { margin:14px 0; padding:12px 14px; border-left:5px solid var(--tango); border-radius:8px; background:rgba(127,100,70,.08); }
  h2 { margin:0 0 6px; font-size:19px; } section p { margin:0; }
  .boton { display:inline-block; margin:4px 8px 4px 0; padding:9px 16px; border-radius:99px; font:600 15px system-ui, sans-serif;
    background:var(--tango); color:#fff; text-decoration:none; }
  .boton.suave { background:transparent; color:var(--tango); border:1px solid var(--tango); }
</style></head>
<body><header><p class="dj">TDJ __DJ__</p><h1>Milongas</h1><p>La música de cada noche</p></header>
<main>
__NOCHES__
</main></body></html>
"""
