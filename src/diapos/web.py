"""
Presentación web de la milonga: un solo archivo .html (fotos dentro) que se ve en cualquier navegador, sin
internet ni PowerPoint.

    crear_web(tandas, datos, destino)

- Portada, una diapo por tema (la tanda entera con el tema que suena destacado), cortinas que anuncian la
  próxima tanda y La Cumparsita.
- Cada diapo lleva la canción ("Artista - Título") para que el modo en vivo (proyectar.py, que lee el
  tracklist de VirtualDJ) salte sola a la que suena. Abierta como archivo, se pasa con las flechas.
- Orquesta sin foto: un emblema con sus iniciales.
"""
import base64
from urllib.parse import quote_plus
import io
import json
import os

from src.config.config import background_image_folder, redes_milongas
from src.diapos.generador import (
    FIRMA_DJ, compositor_para_diapo, duracion_texto, fecha_larga, imagen_orquesta,
)

ANCHO_FOTO = 900          # las fotos se reducen a esto (px) para que el archivo no pese demasiado


def _imagen_base64(ruta, ancho=ANCHO_FOTO, calidad=85):
    """data: URI de la imagen, reducida y en JPEG si no tiene transparencia (o PNG si la tiene)."""
    from PIL import Image
    with Image.open(ruta) as im:
        if im.width > ancho:
            im = im.resize((ancho, round(im.height * ancho / im.width)))
        buf = io.BytesIO()
        if im.mode in ("RGBA", "LA", "P"):
            im.convert("RGBA").save(buf, "PNG", optimize=True)
            tipo = "png"
        else:
            im.convert("RGB").save(buf, "JPEG", quality=calidad)
            tipo = "jpeg"
    return f"data:image/{tipo};base64,{base64.b64encode(buf.getvalue()).decode()}"


def _autores(compositor):
    """'Música: X - Letra: Y' (con tilde) para la presentación web y la lista."""
    return compositor_para_diapo(compositor).replace("Musica:", "Música:")


# ---------------------------------------------------------------- para publicar (GitHub Pages)
SW = """// Guarda lo que se abre para que funcione sin internet: con red, lo último (y se guarda); sin red, lo guardado
const CACHE = "milongas-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const r = await fetch(e.request);
      if (r.ok) cache.put(e.request, r.clone());
      return r;
    } catch (err) {
      const guardado = await cache.match(e.request, {ignoreSearch: true});
      if (guardado) return guardado;
      throw err;
    }
  })());
});
"""


def nombre_manifiesto(datos):
    return nombre_web(datos)[:-len(".html")] + ".webmanifest"


def crear_icono(destino, lado):
    """Icono de la app (pantalla de inicio de la tablet): círculo dorado con «TDJ» sobre fondo oscuro."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (lado, lado), "#0d0907")
    d = ImageDraw.Draw(im)
    m = lado // 10
    d.ellipse([m, m, lado - m, lado - m], fill="#d9a441")
    try:
        letra = ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "georgiab.ttf"), lado // 4)
    except OSError:
        letra = ImageFont.load_default()
    d.text((lado / 2, lado / 2), "TDJ", fill="#120c08", font=letra, anchor="mm")
    im.save(destino)
    return destino


def archivos_para_publicar(datos, carpeta):
    """Crea junto a la presentación lo que necesita para funcionar sin internet y abrirse a pantalla completa
    desde un icono: sw.js, el manifiesto y los iconos. Devuelve sus nombres."""
    nombres = ["sw.js", nombre_manifiesto(datos), "icono-192.png", "icono-512.png"]
    with open(os.path.join(carpeta, "sw.js"), "w", encoding="utf-8") as f:
        f.write(SW)
    manifiesto = {
        "name": f"{datos['milonga']} · {fecha_larga(datos['fecha'])}", "short_name": datos["milonga"][:12],
        "start_url": "./" + nombre_web(datos), "scope": "./", "display": "fullscreen", "orientation": "landscape",
        "background_color": "#0d0907", "theme_color": "#0d0907",
        "icons": [{"src": "icono-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icono-512.png", "sizes": "512x512", "type": "image/png"}],
    }
    with open(os.path.join(carpeta, nombre_manifiesto(datos)), "w", encoding="utf-8") as f:
        json.dump(manifiesto, f, ensure_ascii=False, indent=1)
    crear_icono(os.path.join(carpeta, "icono-192.png"), 192)
    crear_icono(os.path.join(carpeta, "icono-512.png"), 512)
    return nombres


def _archivo(ruta):
    """Nombre del archivo en minúsculas: el programa de pinchar (Mixxx) dice qué archivo suena."""
    return os.path.basename(str(ruta).replace("/", "\\")).lower()


def _bpm(c):
    """BPM del tema (el ya calculado, o el guardado en la caché; sin calcular nada nuevo), o None."""
    try:
        v = float(c.get("bpm"))
        if v == v and v > 0:
            return round(v)
    except (TypeError, ValueError):
        pass
    try:
        from src.diapos import bpm
        v = bpm.CacheBpm().guardado(c["ruta"], c["genre"])[1]
        return round(v) if v else None
    except Exception:
        return None


def _genero(genero):
    return "vals" if "vals" in genero else "milonga" if "milonga" in genero else "tango"


def _iniciales(nombre):
    """'Juan D'Arienzo' -> 'JD'; 'Orquesta Típica Victor' -> 'V' (la primera y la última palabra del nombre)."""
    relleno = {"orquesta", "tipica", "típica", "de", "del", "la", "y", "su", "sexteto", "cuarteto", "quinteto"}
    palabras = [p for p in nombre.replace("'", " ").replace("-", " ").split() if p.lower() not in relleno]
    if not palabras:
        return nombre[:2].upper()
    return (palabras[0][0] + (palabras[-1][0] if len(palabras) > 1 else "")).upper()


def diapos(tandas, datos):
    """Lista de diapos (diccionarios) e imágenes {clave: data URI}."""
    imagenes, salida = {}, []

    def foto(orquesta):
        ruta = imagen_orquesta(orquesta) if orquesta else None
        if not ruta:
            return None
        if ruta not in imagenes:
            try:
                imagenes[ruta] = _imagen_base64(ruta)
            except Exception:
                return None
        return ruta

    reales = [t for t in tandas if not t.es_cortina and not t.es_cumparsita]
    salida.append({
        "tipo": "portada", "milonga": datos["milonga"], "fecha": fecha_larga(datos["fecha"]),
        "horario": f"de {datos['inicio']} a {datos['fin']}", "dj": FIRMA_DJ,
        "tandas": [{"orquesta": t.titulo_orquesta, "subtitulo": t.subtitulo, "genero": _genero(t.genero)}
                   for t in reales],
        # "Hoy suenan": una foto (o emblema) por orquesta de la noche
        "hoy": [{"orquesta": o, "foto": foto(o), "iniciales": _iniciales(o)}
                for o in dict.fromkeys(t.orquesta for t in reales if t.orquesta)],
    })
    numero = 0
    for i, t in enumerate(tandas):
        if t.es_cortina:
            proxima = next((u for u in tandas[i + 1:] if not u.es_cortina), None)
            for _, c in t.canciones.iterrows():
                salida.append({
                    "tipo": "cortina", "titulo": c["title"], "artista": c["artist"],
                    "clave": f"{c['artist']} - {c['title']}", "archivo": _archivo(c['ruta']), "_ruta": c['ruta'],
                    "proxima": None if proxima is None else {
                        "orquesta": proxima.titulo_orquesta, "subtitulo": proxima.subtitulo,
                        "genero": "final" if proxima.es_cumparsita else _genero(proxima.genero),
                        "foto": foto(proxima.orquesta), "iniciales": _iniciales(proxima.orquesta or "?"),
                        "numero": None if proxima.es_cumparsita else numero + 1, "total": len(reales)},
                })
            continue
        if not t.es_cumparsita:
            numero += 1
        temas = [{"titulo": c["title"], "ano": c["ano"], "autores": _autores(c["composer"]),
                  "cantor": c["artist2"]} for _, c in t.canciones.iterrows()]
        for k, (_, c) in enumerate(t.canciones.iterrows()):
            salida.append({
                "tipo": "cumparsita" if t.es_cumparsita else "tema", "numero": numero, "total": len(reales),
                "orquesta": t.titulo_orquesta, "subtitulo": t.subtitulo, "genero": _genero(t.genero),
                "foto": foto(t.orquesta), "iniciales": _iniciales(t.orquesta or "?"),
                "temas": temas, "actual": k, "duracion": round(float(c["duration"] or 0), 1), "bpm": _bpm(c), "clave": f"{c['artist']} - {c['title']}", "archivo": _archivo(c['ruta']), "_ruta": c['ruta'],
            })
    return salida, imagenes


def nombre_lista(datos):
    """'261013-milonga-mia-lista.html': la lista ligera de la noche (para el móvil de la gente)."""
    return nombre_web(datos)[:-len(".html")] + "-lista.html"


def qr_svg(texto):
    """Código QR en SVG (para meterlo dentro del .html: se ve sin internet)."""
    import segno
    # sin tamaño fijo (solo viewBox) para que se escale entero sin recortarse; negro sobre blanco y el margen
    # blanco de 4 módulos que los lectores necesitan
    return segno.make(texto, error="m").svg_inline(omitsize=True, border=4, dark="#000", light="#fff")


def crear_lista(tandas, datos, destino):
    """Versión ligera: el programa de la noche (tandas, temas y cortinas), para leer en el móvil. Unos pocos KB."""
    import html as h
    filas = []
    numero = 0
    for t in tandas:
        if t.es_cortina:
            for _, c in t.canciones.iterrows():
                filas.append(f'<div class="cortina">Cortina · <b>{h.escape(c["title"])}</b>'
                             f'{" — " + h.escape(c["artist"]) if c["artist"] else ""}</div>')
            continue
        if not t.es_cumparsita:
            numero += 1
        genero = "final" if t.es_cumparsita else _genero(t.genero)
        etiqueta = "Último baile" if t.es_cumparsita else {"tango": "Tango", "vals": "Vals", "milonga": "Milonga"}[genero]
        temas = []
        for _, c in t.canciones.iterrows():
            ano = f" <span>{h.escape(str(c['ano']))}</span>" if c["ano"] else ""
            autores = _autores(c["composer"])
            autores = f"<small>{h.escape(autores)}</small>" if autores else ""
            busqueda = quote_plus(" ".join(x for x in (c["artist1"], c["artist2"], c["title"], str(c["ano"] or ""))
                                           if x))
            youtube = (f' <a class="yt" href="https://www.youtube.com/results?search_query={busqueda}" '
                       f'target="_blank" rel="noopener" title="Escuchar en YouTube">▶</a>')
            temas.append(f"<li><b>{h.escape(c['title'])}</b>{ano}{youtube}{autores}</li>")
        temas = "".join(temas)
        filas.append(f'<section class="{genero}"><div class="cab"><em>{"" if t.es_cumparsita else str(numero) + " · "}{etiqueta}</em></div>'
                     f'<h2>{h.escape(t.titulo_orquesta)}</h2><p>{h.escape(t.subtitulo)}</p><ol>{temas}</ol></section>')
    contenido = LISTA.replace("__TITULO__", h.escape(f"{datos['milonga']} · {fecha_larga(datos['fecha'])}")) \
        .replace("__MILONGA__", h.escape(datos["milonga"])) \
        .replace("__FECHA__", h.escape(f"{fecha_larga(datos['fecha'])} · de {datos['inicio']} a {datos['fin']}")) \
        .replace("__DJ__", h.escape(FIRMA_DJ)).replace("__TANDAS__", "\n".join(filas))
    red = redes_milongas.get(datos["milonga"].strip().lower())
    contenido = contenido.replace(
        "__REDES__", f'<a class="boton" href="{h.escape(red)}" target="_blank" rel="noopener">Síguelos en Instagram</a>'
        if red else "")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(contenido)
    return destino


LISTA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title>
<style>
  :root { --fondo:#fbf7f0; --texto:#2a1f17; --suave:#7a6a5c; --tango:#b9852a; --vals:#3f8f5a; --milonga:#c75a2c; --final:#7d5bb5; }
  @media (prefers-color-scheme: dark) { :root { --fondo:#120c08; --texto:#f6efe4; --suave:#b9ab9b; } }
  body { margin:0; background:var(--fondo); color:var(--texto); font:16px/1.45 Georgia, "Palatino Linotype", serif; }
  header { padding:28px 16px 12px; text-align:center; }
  h1 { margin:0; font-size:30px; } header p { margin:6px 0 0; color:var(--suave); }
  .dj { font:600 12px system-ui, sans-serif; letter-spacing:.2em; text-transform:uppercase; color:var(--tango); }
  main { max-width:640px; margin:0 auto; padding:0 16px 32px; }
  section { margin:14px 0; padding:12px 14px; border-left:5px solid var(--tango); border-radius:8px; background:rgba(127,100,70,.08); }
  section.vals { border-color:var(--vals); } section.milonga { border-color:var(--milonga); } section.final { border-color:var(--final); }
  .cab em { font:600 12px system-ui, sans-serif; letter-spacing:.12em; text-transform:uppercase; color:var(--suave); font-style:normal; }
  h2 { margin:2px 0 0; font-size:20px; } section > p { margin:0 0 6px; color:var(--suave); font-style:italic; }
  ol { margin:0; padding-left:20px; } li { margin:4px 0; } li span { color:var(--suave); font-size:14px; }
  li small { display:block; color:var(--suave); font-style:italic; font-size:13px; }
  footer { text-align:center; color:var(--suave); font-size:15px; padding:8px 16px 32px; }
  footer .gracias { font-size:22px; color:var(--texto); margin-bottom:6px; }
  footer .firma { font:600 12px system-ui, sans-serif; letter-spacing:.15em; text-transform:uppercase; color:var(--tango); }
  .intro { margin-top:14px !important; font-style:italic; }
  .boton { display:inline-block; margin:6px 4px; padding:10px 16px; border-radius:99px; border:0; cursor:pointer;
    font:600 15px system-ui, sans-serif; background:var(--tango); color:#fff; text-decoration:none; }
  a.yt { display:inline-block; margin-left:6px; padding:0 7px; border-radius:99px; font:600 12px system-ui, sans-serif;
    background:#c4302b; color:#fff; text-decoration:none; vertical-align:1px; }
  .cortina { margin:4px 0 4px 6px; padding:4px 10px; font:400 13px system-ui, sans-serif; color:var(--suave); }
  .cortina b { font-weight:600; }
</style></head>
<body><header><h1>__MILONGA__</h1><p>__FECHA__</p><p class="dj">TDJ __DJ__</p>
<p class="intro">Esta es la música que ha sonado esta noche.<br>Toca ▶ para volver a escuchar un tema en casa.</p></header>
<main>
__TANDAS__
</main>
<footer>
  <p class="gracias">¡Gracias por bailar!</p>
  <p>¿Te ha gustado la música? <b>Díselo al organizador</b> 😊</p>
  <p>__REDES__ <button class="boton" id="compartir">Compartir esta lista</button></p>
  <p class="firma">Música: TDJ __DJ__</p>
</footer>
<script>
  // Compartir (WhatsApp, etc.) con el menú del móvil; si no hay, copia el enlace
  document.getElementById("compartir").addEventListener("click", async () => {
    const datos = {title: document.title, text: "La música de " + document.title, url: location.href};
    try { if (navigator.share) { await navigator.share(datos); return; } } catch (e) { return; }
    try { await navigator.clipboard.writeText(location.href); alert("Enlace copiado"); }
    catch (e) { prompt("Copia el enlace:", location.href); }
  });
</script></body></html>
"""


def nombre_web(datos):
    """'261013-milonga-mia.html': sin espacios ni acentos, para que sirva tal cual de dirección web."""
    import re
    from unidecode import unidecode
    nombre = re.sub(r"[^a-z0-9]+", "-", unidecode(datos["milonga"]).lower()).strip("-") or "milonga"
    return f"{datos['fecha']:%y%m%d}-{nombre}.html"


def huellas_de_diapos(rutas, progreso=None):
    """{índice de diapo: [códigos (Uint32 en base64), instantes (Uint16 en base64)]} para reconocer por el
    sonido. Se lee cada canción entera (a 8 kHz); ~0,6 s por canción."""
    import numpy as np
    from src.diapos import bpm, huellas
    salida = {}
    for n, (i, ruta) in enumerate(sorted(rutas.items()), 1):
        try:
            muestras = bpm.leer_trozo(ruta, segundos=900, frecuencia=huellas.FRECUENCIA, donde="principio")
            h = huellas.huella_de(muestras)
        except Exception:
            h = []
        if h:
            codigos = np.array([c for c, _ in h], dtype="<u4")
            instantes = np.minimum([t for _, t in h], 65535).astype("<u2")
            salida[i] = [base64.b64encode(codigos.tobytes()).decode(), base64.b64encode(instantes.tobytes()).decode()]
        if progreso:
            progreso(n, len(rutas))
    return salida


def crear_web(tandas, datos, destino, reconocer=True, progreso=None, url_lista=None):
    """
    reconocer: meter las huellas de audio para que la tablet pueda reconocer la canción por el sonido.
    url_lista: dirección pública de la lista ligera (crear_lista): sale un QR pequeño en una esquina.
    """
    lista, imagenes = diapos(tandas, datos)
    try:
        qr = (f'<div id="qr" title="{url_lista}">{qr_svg(url_lista)}<span>La música de hoy</span><span>escanéala y mírala en casa</span></div>'
              if url_lista else "")
    except Exception:
        qr = ""
    rutas = {i: d.pop("_ruta") for i, d in enumerate(lista) if "_ruta" in d}
    huellas_json = json.dumps(huellas_de_diapos(rutas, progreso) if reconocer else {})
    fondo = os.path.join(background_image_folder, "background_tango_degradado.png")
    try:
        fondo_uri = _imagen_base64(fondo, ancho=1600, calidad=80)
    except Exception:
        fondo_uri = ""
    html = (PLANTILLA
            .replace("__TITULO__", f"{datos['milonga']} · {fecha_larga(datos['fecha'])}")
            .replace("__HUELLAS__", huellas_json)
            .replace("__DIAPOS__", json.dumps(lista, ensure_ascii=False))
            .replace("__IMAGENES__", json.dumps(imagenes))
            .replace("__FONDO__", fondo_uri)
            .replace("__FIRMA__", f"TDJ {FIRMA_DJ} · {datos['milonga']}")
            .replace("__QR__", qr)
            .replace("__MANIFEST__", nombre_manifiesto(datos)))
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(html)
    return destino


PLANTILLA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="__MANIFEST__"><meta name="theme-color" content="#0d0907">
<meta name="mobile-web-app-capable" content="yes"><link rel="icon" href="icono-192.png">
<title>__TITULO__</title>
<style>
  :root { --tango:#d9a441; --vals:#6fbf8a; --milonga:#e0784a; --final:#c9a0ff; --texto:#f6efe4; --suave:#cdbfae; }
  html,body { margin:0; height:100%; background:#0d0907; color:var(--texto); overflow:hidden;
    font-family: Georgia, "Palatino Linotype", "Book Antiqua", serif; }
  #fondo { position:fixed; inset:-2vw; background:#0d0907 url("__FONDO__") center/cover no-repeat;
    filter:brightness(.28) blur(6px) saturate(.8); }
  #fondo { transition:filter 1.5s ease, opacity 1s ease; } #velo { transition:opacity 1s ease; }
  /* Cortinas: lo moderno, alegre. Un degradado de colores vivos que se mueve despacio (cada cortina, otro) */
  #alegre { position:fixed; inset:0; opacity:0; transition:opacity 1s ease; pointer-events:none;
    background:linear-gradient(125deg, var(--c1, #ff5f6d), var(--c2, #ffc371), var(--c3, #ff5f9e), var(--c1, #ff5f6d));
    background-size:300% 300%; animation:ola 16s ease-in-out infinite; }
  @keyframes ola { 0% { background-position:0% 50%; } 50% { background-position:100% 50%; } 100% { background-position:0% 50%; } }
  body[data-tipo="cortina"] #alegre { opacity:1; }
  body[data-tipo="cortina"] #fondo, body[data-tipo="cortina"] #velo { opacity:0; }
  body[data-tipo="cortina"] #hora, body[data-tipo="cortina"] #firma, body[data-tipo="cortina"] #estado { color:rgba(255,255,255,.75); }
  #tinte { position:fixed; inset:0; pointer-events:none; opacity:0; transition:opacity 1.5s ease; }
  body[data-genero="tango"] #tinte { opacity:1; background:radial-gradient(ellipse at 22% 50%, rgba(217,164,65,.14), transparent 65%); }
  body[data-genero="vals"] #tinte { opacity:1; background:radial-gradient(ellipse at 22% 50%, rgba(111,191,138,.2), transparent 65%); }
  body[data-genero="milonga"] #tinte { opacity:1; background:radial-gradient(ellipse at 22% 50%, rgba(224,120,74,.26), transparent 72%); }
  body[data-genero="milonga"] #fondo { filter:brightness(.36) blur(6px) saturate(1.15); }
  body[data-genero="vals"] #fondo { filter:brightness(.3) blur(6px) saturate(.9) hue-rotate(-12deg); }
  #velo { position:fixed; inset:0; background:linear-gradient(90deg, rgba(13,9,7,.35), rgba(13,9,7,.75) 45%, rgba(13,9,7,.85)); }
  #diapo { position:fixed; inset:0; display:flex; align-items:center; justify-content:center; padding:4vh 5vw 120px;
    box-sizing:border-box; transition:opacity .35s ease; }
  .oculta { opacity:0; }
  .tanda { display:grid; grid-template-columns: 34vw 1fr; gap:4vw; width:100%; align-items:center; }
  .foto { width:min(34vw, 62vh); height:min(34vw, 62vh); border-radius:2vw; object-fit:cover; background:#2a211b;
    box-shadow:0 2vh 6vh rgba(0,0,0,.6); border:.35vw solid rgba(255,255,255,.12); }
  .emblema { width:min(34vw, 62vh); height:min(34vw, 62vh); border-radius:50%; display:flex; align-items:center;
    justify-content:center; font-size:12vw; letter-spacing:.05em; color:#120c08;
    background:radial-gradient(circle at 35% 30%, #f3d9a4, var(--tango)); box-shadow:0 2vh 6vh rgba(0,0,0,.6); }
  .chip { display:inline-block; padding:.4vh 1.1vw; border-radius:99px; font:600 1.6vw system-ui, sans-serif;
    letter-spacing:.12em; text-transform:uppercase; color:#120c08; background:var(--tango); }
  .chip.vals { background:var(--vals); } .chip.milonga { background:var(--milonga); } .chip.final { background:var(--final); }
  .num { font:500 1.6vw system-ui, sans-serif; color:var(--suave); margin-left:1vw; letter-spacing:.08em; }
  h1 { font-size:min(5.2vw, 8.5vh); line-height:1.02; margin:1.6vh 0 .6vh; font-weight:700; text-shadow:0 .4vh 1.2vh #000; }
  h2 { font-size:min(2.4vw, 4.2vh); margin:0 0 2.5vh; font-weight:400; font-style:italic; color:var(--suave); }
  ol { list-style:none; margin:0; padding:0; }
  li { margin:.8vh 0; padding:1vh 1.4vw; border-left:.5vw solid transparent; border-radius:.6vw;
    color:rgba(246,239,228,.45); transition:all .35s; }
  li .t { font-size:min(2.9vw, 4.8vh); } li .a { font-size:min(1.5vw, 2.6vh); font-style:italic; display:block; margin-top:.4vh; }
  li .y { font:400 1.6vw system-ui, sans-serif; margin-left:1vw; }
  li.ya { color:rgba(246,239,228,.3); }
  li.normal { color:var(--texto); }
  .cuenta { font:500 max(15px, 1.7vw) system-ui, sans-serif; color:var(--suave); margin-top:4vh; min-height:2em; }
  body.pausado .cuenta { color:var(--milonga); }
  #tandas { position:fixed; inset:0; display:none; background:rgba(8,5,4,.94); z-index:11; overflow:auto;
    padding:3vh 4vw; box-sizing:border-box; font:400 max(15px, 1.5vw) system-ui, sans-serif; }
  #tandas.visible { display:block; }
  #tandas h3 { font:700 max(22px, 2.4vw) Georgia, serif; color:var(--tango); margin:0 0 2vh; }
  #tandas .rejilla { display:grid; grid-template-columns:repeat(auto-fill, minmax(17em, 1fr)); gap:1vh 1.2vw; }
  #tandas button { text-align:left; padding:1.2vh 1vw; min-height:48px; border-radius:.8vw; cursor:pointer;
    border:1px solid rgba(246,239,228,.15); background:rgba(255,255,255,.05); color:var(--texto); font:inherit; }
  #tandas button.aqui { border-color:var(--tango); background:rgba(217,164,65,.18); }
  #tandas button b { display:inline-block; width:.9em; height:.9em; border-radius:50%; margin-right:.5em; background:var(--tango); }
  #tandas button b.vals { background:var(--vals); } #tandas button b.milonga { background:var(--milonga); }
  #tandas button b.final { background:var(--final); }
  #tandas button i { color:var(--suave); }
  body.bloqueado #b-bloqueo { background:var(--tango); color:#120c08; }
  body.simple #b-simple { background:var(--vals); color:#120c08; }
  li.ahora { color:var(--texto); background:rgba(0,0,0,.35); border-left-color:var(--tango); }
  li.ahora .t { font-size:min(3.6vw, 6vh); font-weight:700; }
  .eq { display:inline-flex; align-items:flex-end; gap:.25vw; height:2.2vw; margin-left:1.2vw; vertical-align:-.15vw; }
  .eq i { display:block; width:.45vw; height:100%; border-radius:.2vw; background:var(--tango); opacity:.85;
    transform-origin:bottom; animation:latido ease-in-out infinite alternate; }
  .vals .eq i { background:var(--vals); } .milonga .eq i { background:var(--milonga); }
  @keyframes latido { from { transform:scaleY(.15); } to { transform:scaleY(1); } }
  body.pausado .eq i { animation-play-state:paused; }
  #qr { position:fixed; left:1vw; top:1vh; display:flex; flex-direction:column; align-items:center; gap:2px;
    padding:4px 4px 3px; border-radius:6px; background:#fff; z-index:5; }
  #qr svg { width:max(96px, 14vh); height:max(96px, 14vh); display:block; shape-rendering:crispEdges; }
  #qr { display:none; }
  body[data-tipo="portada"] #qr, body[data-tipo="cortina"] #qr { display:flex; }   /* no tapar a los músicos */
  #qr span { font:600 max(10px, 1.3vh) system-ui, sans-serif; color:#000; }
  #qr span + span { font-weight:400; font-size:max(9px, 1.1vh); }
  #hora { position:fixed; right:1.6vw; top:1.2vh; font:500 max(14px, 1.5vw) system-ui, sans-serif;
    color:rgba(246,239,228,.45); letter-spacing:.05em; }
  .vals li.ahora { border-left-color:var(--vals); } .milonga li.ahora { border-left-color:var(--milonga); }
  .portada { text-align:center; width:100%; }
  .portada h1 { font-size:7vw; margin:0; }
  .portada .fecha { font-size:2.6vw; color:var(--suave); margin:1.5vh 0 .5vh; }
  .portada .dj { font:500 1.6vw system-ui, sans-serif; letter-spacing:.2em; text-transform:uppercase; color:var(--tango); margin-bottom:4vh; }
  .portada .lista { display:grid; grid-template-columns:repeat(3, 1fr); gap:1vh 2vw; text-align:left; max-width:88vw; margin:0 auto; }
  .portada .lista div { font-size:1.45vw; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .portada .lista b { display:inline-block; width:1.4vw; height:1.4vw; border-radius:50%; margin-right:.8vw; vertical-align:-.15vw; background:var(--tango); }
  .portada .lista b.vals { background:var(--vals); } .portada .lista b.milonga { background:var(--milonga); }
  .cortina { text-align:center; width:100%; }
  .cortina .sonando { font:600 max(16px, 2vw) system-ui, sans-serif; letter-spacing:.35em; text-transform:uppercase; color:#fff; opacity:.9; }
  .cortina h1 { font:800 min(8.5vw, 15vh)/1.02 system-ui, "Segoe UI", sans-serif; letter-spacing:-.02em; color:#fff;
    margin:1vh 0 .5vh; text-shadow:0 .6vh 3vh rgba(0,0,0,.35); }
  .cortina h2 { font:italic 400 min(3.6vw, 6vh) Georgia, serif; color:#fff; opacity:.92; margin-bottom:5vh;
    text-shadow:0 .3vh 1.5vh rgba(0,0,0,.3); }
  .cortina .proxima { background:rgba(20,10,30,.45); backdrop-filter:blur(4px); }
  .cortina .cuenta { color:rgba(255,255,255,.85); }
  .cortina .mensaje { background:rgba(255,255,255,.2); border-color:rgba(255,255,255,.5); }
  .proxima { display:inline-flex; align-items:center; gap:2.5vw; padding:2.5vh 3vw; border-radius:2vw; background:rgba(0,0,0,.45); text-align:left; }
  .proxima img, .proxima .emblema { width:14vw; height:14vw; font-size:5vw; }
  .proxima .que { font:500 1.5vw system-ui, sans-serif; letter-spacing:.2em; text-transform:uppercase; color:var(--suave); }
  .proxima .orq { font-size:3.2vw; font-weight:700; margin:.6vh 0; }
  .proxima .sub { font-size:1.8vw; font-style:italic; color:var(--suave); }
  #firma { position:fixed; left:2vw; bottom:1.6vh; font:400 1.1vw system-ui, sans-serif; color:rgba(246,239,228,.45); }
  #estado { position:fixed; right:1.5vw; bottom:1.6vh; font:400 1vw system-ui, sans-serif; color:rgba(246,239,228,.45); }
  #estado b { display:inline-block; width:max(11px, .9vw); height:max(11px, .9vw); border-radius:50%; background:#777;
    margin-right:.5vw; vertical-align:-.1vw; }
  #estado[data-punto="verde"] b { background:#46d36b; box-shadow:0 0 1vw #46d36b; }      /* sabe dónde está */
  #estado[data-punto="amarillo"] b { background:#e0b341; }                              /* va por tiempo */
  #estado[data-punto="rojo"] b { background:#e05a5a; box-shadow:0 0 1vw #e05a5a; }      /* sin micrófono */
  body.quieto { cursor:none; }
  #reproductor { position:fixed; left:16px; right:16px; bottom:88px; display:flex; align-items:center;
    gap:12px; font:600 max(15px, 1.4vw) system-ui, sans-serif; color:var(--suave); transition:opacity .4s; }
  #reproductor.apagado { display:none; }
  #pista { flex:1; height:12px; border-radius:99px; background:rgba(255,255,255,.12); cursor:pointer;
    touch-action:none; position:relative; }
  #pista::before { content:""; position:absolute; left:0; right:0; top:-16px; bottom:-16px; }   /* más fácil con el dedo */
  #relleno { height:100%; width:0; border-radius:99px; background:rgba(217,164,65,.8); }
  #reproductor .total { opacity:.7; }
  body.quieto #reproductor { opacity:.15; }
  body.pausado #reproductor { opacity:1; }
  #botones { position:fixed; left:50%; bottom:14px; transform:translateX(-50%); display:flex; gap:12px;
    transition:opacity .4s; }
  #botones button, #mas button, #pedir button { font:600 20px system-ui, sans-serif; min-width:68px; height:60px;
    padding:0 18px; border:1px solid rgba(246,239,228,.3); border-radius:16px; background:rgba(13,9,7,.8);
    color:var(--texto); cursor:pointer; white-space:nowrap; touch-action:manipulation; }
  #botones button:active, #mas button:active { background:rgba(217,164,65,.35); }
  #mas, #pedir, #cumple { position:fixed; inset:0; display:none; align-items:center; justify-content:center; z-index:12;
    background:rgba(8,5,4,.9); }
  #mas.visible, #pedir.visible, #cumple.visible { display:flex; }
  #mas .rejilla { display:grid; grid-template-columns:repeat(auto-fill, minmax(190px, 1fr)); gap:14px; width:min(720px, 92vw); }
  #mas button { height:76px; font-size:20px; text-align:left; }
  #mas button small { display:block; font:400 13px system-ui, sans-serif; color:var(--suave); margin-top:2px; white-space:normal; }
  #pedir > div { width:min(640px, 92vw); font:500 20px system-ui, sans-serif; color:var(--texto); }
  #pedir input { width:100%; box-sizing:border-box; font:600 28px system-ui, sans-serif; padding:14px; margin:16px 0;
    border-radius:12px; border:2px solid var(--tango); background:#1b1410; color:var(--texto); }
  #pedir .fila { display:flex; gap:12px; justify-content:flex-end; }
  #cumple { flex-direction:column; text-align:center; overflow:hidden; background:radial-gradient(circle, #3a2414, #0d0907); }
  #cumple .que { font:500 max(18px, 2.4vw) system-ui, sans-serif; letter-spacing:.3em; text-transform:uppercase; color:var(--tango); }
  #cumple .quien { font:700 max(48px, 9vw) Georgia, serif; margin:2vh 0; text-shadow:0 .5vh 2vh #000; }
  #cumple .baila { font:italic 400 max(20px, 3vw) Georgia, serif; color:var(--suave); }
  #cumple i { position:absolute; top:-5vh; width:1.2vw; height:2vw; min-width:8px; min-height:12px; opacity:.9;
    animation:cae linear infinite; }
  @keyframes cae { to { transform:translateY(115vh) rotate(720deg); } }
  #aviso { position:fixed; left:50%; top:3vh; transform:translateX(-50%); padding:12px 20px; border-radius:12px; z-index:13;
    background:rgba(13,9,7,.95); border:1px solid var(--tango); font:500 18px system-ui, sans-serif; display:none;
    max-width:88vw; line-height:1.4; }
  #aviso.visible { display:block; }
  #aviso.grande { font-size:max(24px, 2.6vw); padding:20px 30px; background:#3a0f0c; border:2px solid #e05a5a; }
  #listo { position:fixed; inset:0; display:none; align-items:center; justify-content:center; z-index:12;
    background:rgba(8,5,4,.94); font:400 max(16px, 1.6vw) system-ui, sans-serif; color:var(--texto); }
  #listo.visible { display:flex; }
  #listo > div { width:min(760px, 92vw); }
  #listo h3 { font:700 max(26px, 2.8vw) Georgia, serif; color:var(--tango); margin:0 0 2vh; }
  #listo ul { list-style:none; margin:0; padding:0; }
  #listo li { display:flex; align-items:baseline; gap:.6em; flex-wrap:wrap; margin:0 0 1.4vh; padding:0; border:0; color:var(--texto); }
  #listo li b { flex:0 0 1.4em; font-size:1.3em; text-align:center; }
  #listo li.si b { color:#46d36b; } #listo li.no b { color:#e05a5a; } #listo li.medio b { color:#e0b341; }
  #listo li small { flex-basis:100%; margin-left:2.4em; color:var(--suave); font-size:.85em; }
  #listo .cerrar { margin-top:3vh; text-align:center; color:var(--tango); font-weight:600; }
  #cinta { position:fixed; left:50%; top:1.2vh; transform:translateX(-50%); z-index:9; display:none; gap:12px; align-items:center;
    padding:6px 8px 6px 18px; border-radius:99px; background:#7d5bb5; font:700 max(15px, 1.4vw) system-ui, sans-serif; }
  body.ensayo #cinta { display:flex; }
  #cinta button { font:600 16px system-ui, sans-serif; height:44px; padding:0 16px; border-radius:99px; border:0;
    background:#120c08; color:var(--texto); cursor:pointer; }
  #pedir-opciones { display:flex; flex-wrap:wrap; gap:10px; margin-top:12px; }
  #pedir #pedir-opciones button { font-size:16px; height:48px; min-width:0; padding:0 14px; }
  .mensaje { margin:3vh auto 0; max-width:70vw; padding:1.6vh 2vw; border-radius:1.2vw; background:rgba(217,164,65,.15);
    border:1px solid rgba(217,164,65,.4); font:500 max(16px, 2vw) system-ui, sans-serif; color:var(--texto); }
  .chip.ultima { background:#e05a5a; color:#fff; margin-left:.8vw; }
  .hoy { display:flex; flex-wrap:wrap; justify-content:center; gap:1.2vw; margin:0 auto 3.5vh; max-width:90vw; }
  .hoy img, .hoy .emblema { width:6.5vw; height:6.5vw; min-width:44px; min-height:44px; border-radius:50%; object-fit:cover;
    font-size:2.4vw; border:2px solid rgba(255,255,255,.15); }
  body.micro .eq i { animation:none; transition:transform .06s linear; }
  body.quieto #botones { opacity:.08; }
  body.pausado #botones { opacity:1; }
  body.pausado #b-pausa { background:var(--tango); color:#120c08; }
  body.pausado #relleno { background:rgba(224,120,74,.9); }
  #ayuda { position:fixed; inset:0; display:none; align-items:center; justify-content:center; background:rgba(8,5,4,.92);
    font:400 max(15px, 1.5vw)/1.5 system-ui, sans-serif; color:var(--texto); z-index:10; padding:3vh 5vw; box-sizing:border-box;
    overflow:auto; }
  #ayuda.visible { align-items:flex-start; }
  #ayuda.visible { display:flex; }
  #ayuda > div { max-width:70em; }
  #ayuda h3 { font:700 max(22px, 2.6vw) Georgia, serif; margin:0 0 1.5vh; color:var(--tango); }
  #ayuda ol { list-style:decimal; padding-left:1.5em; }
  #ayuda li { margin:.8vh 0; padding:0; border:0; color:var(--texto); }
  #ayuda .cerrar { margin-top:3vh; text-align:center; color:var(--tango); font-weight:600; }
  @media (max-aspect-ratio: 1/1) {          /* tablet o móvil en vertical */
    .tanda { grid-template-columns:1fr; text-align:center; } .foto, .emblema { width:60vw; height:60vw; margin:0 auto; }
    h1 { font-size:8vw; } h2 { font-size:4vw; } li .t { font-size:5vw; } li.ahora .t { font-size:6vw; }
    li .a, li .y, .chip, .num { font-size:3vw; } .portada .lista { grid-template-columns:1fr; } .portada .lista div { font-size:3.2vw; }
  }
</style></head>
<body>
<div id="fondo"></div><div id="velo"></div><div id="tinte"></div><div id="alegre"></div>
<div id="diapo"></div>
<div id="firma">© __FIRMA__</div>
<div id="hora"></div>
__QR__
<div id="estado" title="Verde: sabe lo que suena (en vivo o por el micrófono). Amarillo: va por tiempo. Rojo: el micrófono no funciona"><b></b><span>por tiempo · toca al empezar cada tanda</span></div>
<div id="reproductor" class="apagado">
  <span id="t-lleva">0:00</span>
  <div id="pista" title="Toca o arrastra para poner el tema en su punto"><div id="relleno"></div></div>
  <span id="t-queda">−0:00</span><span class="total">/ <span id="t-total">0:00</span></span>
</div>
<div id="botones">
  <button id="b-atras" title="Anterior">◀</button>
  <button id="b-pausa" title="Parar / seguir el reloj">⏸ Pausa</button>
  <button id="b-adelante" title="Siguiente">▶</button>
  <button id="b-tandas" title="Ir directo a una tanda">≡ Tandas</button>
  <button id="b-mas" title="Más opciones">⋯ Más</button>
</div>
<div id="mas"><div class="rejilla">
  <button id="b-cumple">🎂 Cumpleaños<small>«¡Feliz cumpleaños, …!» con confeti</small></button>
  <button id="b-mensaje">💬 Mensaje<small>texto en todas las cortinas</small></button>
  <button id="b-bloqueo">🔓 Bloquear toques<small>tocar la pantalla no pasa diapos</small></button>
  <button id="b-simple">Simple<small>una diapo por tanda</small></button>
  <button id="b-micro">🎤 Reconocer canción<small>escucha y corrige solo; si no, sigue el reloj</small></button>
  <button id="b-listo">✓ Comprobar<small>¿micrófono, sin internet, batería…?</small></button>
  <button id="b-ensayo">🎬 Ensayo rápido<small>toda la noche en ~3 min, para repasarla</small></button>
  <button id="b-ayuda">? Ayuda<small>cómo funciona</small></button>
  <button id="b-completa">⛶ Pantalla completa</button>
  <button id="b-cerrar">✕ Cerrar</button>
</div></div>
<div id="pedir"><div>
  <div id="pedir-texto"></div>
  <div id="pedir-opciones"></div>
  <input id="pedir-valor" type="text" autocomplete="off">
  <div class="fila"><button id="pedir-no">Cancelar</button><button id="pedir-si">Aceptar</button></div>
</div></div>
<div id="cumple"><div class="que">¡Feliz cumpleaños!</div><div class="quien" id="cumple-quien"></div>
  <div class="baila">Un vals para celebrarlo</div></div>
<div id="aviso"></div>
<div id="listo"><div><h3>¿Todo listo?</h3><ul id="listo-cosas"></ul>
  <p class="cerrar" id="listo-cerrar">Toca una vez para activar lo que falta (pantalla completa, micrófono…)</p></div></div>
<div id="cinta">🎬 ENSAYO ×60 <button id="b-fin-ensayo">■ Terminar</button></div>
<div id="tandas"></div>
<div id="ayuda"><div>
  <h3>Cómo funciona</h3>
  <p><b>Sin conexión ni cables (modo «por tiempo»):</b></p>
  <ol>
    <li>Cuando suena la <b>cortina</b>, la pantalla anuncia la próxima tanda. Si no tocas, <b>al minuto</b> empieza sola la tanda.</li>
    <li>Mejor: cuando empieza el <b>primer tema</b> de la tanda, <b>toca la pantalla una vez</b> (en la parte derecha). Si la cortina va a durar más, ⏸ Pausa.</li>
    <li>Los temas avanzan <b>solos</b> según su duración (la barrita dorada de abajo) y al acabar la tanda vuelve a la cortina.</li>
  </ol>
  <p><b>Botones</b> (abajo, grandes; se apagan solos y vuelven al tocar): <b>◀</b> anterior · <b>⏸ Pausa</b> / <b>▶ Seguir</b> (para el reloj: si hablan, cortina larga…) · <b>▶</b> siguiente · <b>≡ Tandas</b> ir directo a una tanda si te pierdes · <b>⋯ Más</b>: 🎂 cumpleaños con confeti · 💬 mensaje en las cortinas · 🔓 bloquear toques (tocar la pantalla sin querer no pasa nada) · Simple (una diapo por tanda) · 🎤 reconocer canción (la tablet escucha y corrige sola si oye otra cosa o va desfasada; el reloj sigue mandando, y si no hay micrófono no pasa nada) · ✓ comprobar (micrófono, sin internet, batería…) · 🎬 ensayo rápido (la noche entera en unos 3 minutos, para repasarla en casa) · ? ayuda · ⛶ pantalla completa.</p>
  <p><b>Punto de abajo a la derecha:</b> 🟢 sabe lo que suena · 🟡 va por tiempo · 🔴 el micrófono no funciona (sigue por tiempo).</p>
  <p><b>Reproductor</b> (encima de los botones): lo que lleva el tema, lo que queda y lo que dura. Si no cuadra con Mixxx, <b>toca o arrastra la barra</b> hasta el punto en que va el tema (por ejemplo, si en Mixxx va por 1:30, ponla en 1:30).</p>
  <p>En la cortina se ve cuándo empezará sola la tanda. Si se cierra o se recarga, al abrirla vuelve a la misma diapo.</p>
  <p>Tocar la pantalla: a la <b>derecha</b> avanza, en el <b>tercio izquierdo</b> retrocede. En un ordenador: flechas, espacio, F = pantalla completa.</p>
  <p><b>Con red</b> (misma wifi, o el punto de acceso de un móvil aunque no tenga datos): en TangoTags, Crear diapos → «📽 Proyectar en vivo», y abrir aquí la dirección que indica. El punto de abajo se pone verde y sigue sola al tema que suena en Mixxx.</p>
  <p class="cerrar">Toca para empezar (y pasar a pantalla completa)</p>
</div></div>
<script>
const DIAPOS = __DIAPOS__;
const IMG = __IMAGENES__;
const HUELLAS = __HUELLAS__;
let actual = 0, ultimoTexto = null;

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const norm = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
                   .replace(/\(.*?\)/g, " ").replace(/[^a-z0-9]+/g, " ").trim();
const genero = g => ({tango:"Tango", vals:"Vals", milonga:"Milonga", final:"Último baile"}[g] || g);
const imagen = (foto, iniciales, clase) => foto && IMG[foto]
  ? `<img class="${clase}" src="${IMG[foto]}" alt="">` : `<div class="emblema">${esc(iniciales)}</div>`;

// Ecualizador que late al BPM del tema (calculado del audio); cada barra a su aire para que parezca vivo
function ecualizador(bpm, genero) {
  // una subida y bajada por pulso (en el vals, por compás de 3: a 200 BPM parpadearía)
  const pulsos = genero === "vals" ? (bpm || 200) / 3 : (bpm || 110);
  const medio = 30 / pulsos;                       // "alternate": medio pulso para subir y medio para bajar
  const barras = [1, 0.5, 1, 2, 0.5, 1, 0.5].map((x, i) =>
    `<i style="animation-duration:${(medio * x).toFixed(3)}s; animation-delay:-${(medio * i * 0.37).toFixed(3)}s"></i>`);
  return `<span class="eq" title="${bpm ? bpm + " BPM" : ""}">${barras.join("")}</span>`;
}

// "Última tanda" / "Penúltima tanda"
function ultimas(numero, total) {
  if (!numero || !total) return "";
  const quedan = total - numero;
  return quedan === 0 ? `<span class="chip ultima">Última tanda</span>`
       : quedan === 1 ? `<span class="chip ultima">Penúltima tanda</span>` : "";
}

let mensaje = "";          // mensaje del organizador en las cortinas (se recuerda en esta tablet)

function pintar(d) {
  if (d.tipo === "portada") {
    return `<div class="portada"><h1>${esc(d.milonga)}</h1><div class="fecha">${esc(d.fecha)} · ${esc(d.horario)}</div>
      <div class="dj">TDJ ${esc(d.dj)}</div>
      ${d.hoy && d.hoy.length ? `<div class="hoy">${d.hoy.map(o => imagen(o.foto, o.iniciales, "foto")).join("")}</div>` : ""}
      <div class="lista" style="grid-template-rows:repeat(${Math.ceil(d.tandas.length / 3)}, auto); grid-auto-flow:column">${d.tandas.map((t, n) =>
      `<div><b class="${t.genero}"></b>${n + 1}. ${esc(t.orquesta.replace(/^Orquesta de /, ""))} <i>${esc(t.subtitulo)}</i></div>`).join("")}</div></div>`;
  }
  if (d.tipo === "cortina") {
    const p = d.proxima;
    return `<div class="cortina"><div class="sonando">Cortina</div><h1>${esc(d.titulo)}</h1><h2>${esc(d.artista)}</h2>
      ${p ? `<div class="proxima">${imagen(p.foto, p.iniciales, "foto")}<div><div class="que">A continuación ·
      <span class="chip ${p.genero}">${genero(p.genero)}</span>${ultimas(p.numero, p.total)}</div><div class="orq">${esc(p.orquesta)}</div>
      <div class="sub">${esc(p.subtitulo)}</div></div></div>` : ""}<div class="cuenta" id="cuenta"></div>${mensaje ? `<div class="mensaje">${esc(mensaje)}</div>` : ""}</div>`;
  }
  const temas = d.temas.map((t, k) => `<li class="${simple ? "normal" : k < d.actual ? "ya" : k === d.actual ? "ahora" : ""}">
      <span class="t">${esc(t.titulo)}</span>${t.ano ? `<span class="y">${esc(t.ano)}</span>` : ""}
      ${!simple && k === d.actual ? ecualizador(d.bpm, d.genero) : ""}
      ${t.autores ? `<span class="a">${esc(t.autores)}</span>` : ""}</li>`).join("");
  const cabecera = d.tipo === "cumparsita" ? `<span class="chip final">Último baile</span>`
    : `<span class="chip ${d.genero}">${genero(d.genero)}</span><span class="num">Tanda ${d.numero} de ${d.total}</span>${ultimas(d.numero, d.total)}`;
  return `<div class="tanda ${d.genero}">${imagen(d.foto, d.iniciales, "foto")}<div>${cabecera}
    <h1>${esc(d.orquesta)}</h1><h2>${esc(d.subtitulo)}</h2><ol>${temas}</ol></div></div>`;
}

// Modo por tiempo (la tablet sola, sin conexión): al tocar cuando empieza una tanda, sus temas avanzan solos
// según su duración y al acabar pasa a la cortina; la cortina, si no se toca, empieza la tanda al minuto.
// El reloj va por la HORA REAL (cuándo empezó lo que suena), no por temporizadores largos: si el navegador de
// la tablet se duerme o va lento, al despertar se pone al día solo y no se acumula retraso.
const PAUSA = 2;                     // segundos entre el final de un tema y el siguiente
const CORTINA = 60;                  // segundos de cortina: si no se toca antes, la tanda empieza sola
let enVivo = false, destino = 0;
let pausado = false;
let inicio = 0;                      // Date.now() en que empezó lo que suena en esta diapo
let largo = 0;                       // ms que dura (0 = esta diapo no avanza sola)
let enPausa = 0;                     // Date.now() en que se pausó

// Lo que se recuerda en esta tablet para esta presentación (si se cierra o recarga): diapo, simple, bloqueo
const CLAVE = "tgdj:" + document.title + ":";
const guarda = (k, v) => { try { localStorage.setItem(CLAVE + k, JSON.stringify(v)); } catch (e) {} };
const lee = (k, def) => { try { const v = localStorage.getItem(CLAVE + k); return v === null ? def : JSON.parse(v); }
                          catch (e) { return def; } };
let simple = lee("simple", false);       // modo simple: una diapo por tanda, sin destacar cada tema
let bloqueado = lee("bloqueado", false); // tocar la pantalla no pasa diapos (solo los botones)

// Diapo siguiente / anterior (en modo simple se saltan las de los temas 2.º y 3.º de cada tanda)
function paso(n, dir) {
  let m = n + dir;
  while (simple && DIAPOS[m] && DIAPOS[m].tipo === "tema" && DIAPOS[m].actual > 0) m += dir;
  return Math.max(0, Math.min(DIAPOS.length - 1, m));
}

// Cuánto dura lo de la diapo n (ms), o 0 si no avanza sola
function duracionDe(n) {
  const d = DIAPOS[n], sigN = paso(n, 1), sig = DIAPOS[sigN];
  if (enVivo || !d || !sig || sigN === n) return 0;
  if (d.tipo === "tema" && d.duracion && ["tema", "cortina"].includes(sig.tipo)) {
    if (!simple) return d.duracion * 1000;
    let ms = 0;            // modo simple: la tanda entera (sus temas y las pausas entre ellos)
    for (let k = n; DIAPOS[k] && DIAPOS[k].tipo === "tema" && DIAPOS[k].numero === d.numero; k++) {
      ms += (DIAPOS[k].duracion || 0) * 1000 + (k > n ? PAUSA * 1000 : 0);
    }
    return ms;
  }
  if (d.tipo === "cortina" && ["tema", "cumparsita"].includes(sig.tipo)) return CORTINA * 1000;
  return 0;
}

// 🎬 Ensayo rápido: el reloj corre VELOCIDAD veces más deprisa (la noche entera en unos minutos)
const VELOCIDAD = 60;
let ensayo = false, baseReal = 0, baseEnsayo = 0;
const reloj = () => ensayo ? baseEnsayo + (Date.now() - baseReal) * VELOCIDAD : Date.now();
const ahora = () => (pausado ? enPausa : reloj());
const lleva = () => Math.max(0, Math.min(largo, ahora() - inicio));      // ms que lleva sonando

// Cada cuarto de segundo: pasar a la siguiente si toca (poniéndose al día si el navegador se durmió)
function tic() {
  for (let vueltas = 0; vueltas < 60 && largo && !pausado; vueltas++) {
    const hueco = DIAPOS[destino].tipo === "tema" ? PAUSA * 1000 : 0;
    const fin = inicio + largo + hueco;              // cuándo empieza lo siguiente
    if (reloj() < fin) break;
    ir(paso(destino, 1), fin);
  }
  pintarReloj();
}

const mmss = ms => { const s = Math.round(ms / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

function pintarReloj() {
  const caja = document.getElementById("reproductor");
  if (!largo) { caja.classList.add("apagado"); return; }
  caja.classList.remove("apagado");
  const l = lleva();
  document.getElementById("relleno").style.width = `${100 * l / largo}%`;
  document.getElementById("t-lleva").textContent = mmss(l);
  document.getElementById("t-total").textContent = mmss(largo);
  document.getElementById("t-queda").textContent = "−" + mmss(largo - l);
  const c = document.getElementById("cuenta");             // en la cortina: cuándo empieza sola la tanda
  if (c) {
    c.textContent = DIAPOS[destino].tipo !== "cortina" ? ""
      : pausado ? "En pausa: la tanda no empezará sola (▶ Seguir)"
      : `La tanda empieza sola en ${mmss(largo - l)} · toca cuando empiece`;
  }
}

// Mover la barra: tocar o arrastrar en ella pone el tema en ese punto (para cuadrarlo con lo que suena)
function buscarEnBarra(e) {
  if (!largo) return;
  const r = document.getElementById("pista").getBoundingClientRect();
  const x = (e.touches ? e.touches[0].clientX : e.clientX);
  const f = Math.max(0, Math.min(1, (x - r.left) / r.width));
  inicio = ahora() - f * largo;
  pintarReloj();
}

// ⏸ / ▶: para el reloj y lo sigue donde se quedó
function pausa() {
  if (pausado) { inicio += reloj() - enPausa; pausado = false; }
  else { enPausa = reloj(); pausado = true; }
  document.getElementById("b-pausa").textContent = pausado ? "▶ Seguir" : "⏸ Pausa";
  document.body.classList.toggle("pausado", pausado);
  pintarReloj();
}

// Ir a la diapo n. `desde`: cuándo empezó lo que suena (por defecto, ahora: al tocar empieza el reloj)
function ir(n, desde) {
  n = Math.max(0, Math.min(DIAPOS.length - 1, n));
  if (simple && DIAPOS[n].tipo === "tema" && DIAPOS[n].actual > 0) n -= DIAPOS[n].actual;   // la de la tanda
  if (n === destino && document.getElementById("diapo").innerHTML) return;
  destino = n;
  if (!ensayo) guarda("diapo", n);
  inicio = desde !== undefined ? desde : ahora();
  largo = duracionDe(n);
  pintarReloj();
  const caja = document.getElementById("diapo");
  caja.classList.add("oculta");
  setTimeout(() => { if (destino !== n) return;
                     actual = n; document.body.dataset.tipo = DIAPOS[n].tipo;
                     document.body.dataset.genero = DIAPOS[n].tipo === "cortina" ? "" : (DIAPOS[n].genero || "");
                     if (DIAPOS[n].tipo === "cortina") alegrar(n);
                     caja.innerHTML = pintar(DIAPOS[n]); caja.classList.remove("oculta");
                     if (!ensayo) history.replaceState(null, "", "#" + n); }, 180);
}

// Colores de las cortinas: cada cortina de la noche con su combinación (vivos, y que se lea el blanco encima)
const ALEGRES = [["#ff5f6d", "#ffc371", "#ff5f9e"], ["#7f00ff", "#e100ff", "#ff6a88"], ["#00b09b", "#3a7bd5", "#00c6ff"],
                 ["#f7971e", "#ff4e50", "#f9d423"], ["#fc466b", "#3f5efb", "#a044ff"], ["#11998e", "#38ef7d", "#0f9b8e"],
                 ["#ee0979", "#ff6a00", "#ff3cac"], ["#4776e6", "#8e54e9", "#00d2ff"]];
function alegrar(n) {
  const k = DIAPOS.slice(0, n).filter(d => d.tipo === "cortina").length % ALEGRES.length;
  const a = document.getElementById("alegre");
  ALEGRES[k].forEach((c, i) => a.style.setProperty(`--c${i + 1}`, c));
}

// Que la pantalla de la tablet no se apague (si el navegador lo permite)
let pantallaDespierta = null;
async function despierta() {
  try {
    if ("wakeLock" in navigator && (!pantallaDespierta || pantallaDespierta.released)) {
      pantallaDespierta = await navigator.wakeLock.request("screen");
    }
  } catch (e) {}
}
document.addEventListener("visibilitychange", () => { if (!document.hidden) despierta(); });

function libre(texto) {
  const [artista, ...resto] = String(texto).split(" - ");
  const titulo = resto.join(" - ") || artista;
  const caja = document.getElementById("diapo");
  caja.classList.add("oculta");
  setTimeout(() => {
    caja.innerHTML = `<div class="cortina"><div class="sonando">Suena</div><h1>${esc(titulo)}</h1>
      <h2>${esc(resto.length ? artista : "")}</h2></div>`;
    caja.classList.remove("oculta");
  }, 180);
}

// Por el archivo que suena (Mixxx lo dice): exacto. La más cercana a la actual, por si se repite.
function porArchivo(ruta) {
  if (!ruta) return null;
  const nombre = String(ruta).replace(/\//g, "\\").split("\\").pop().toLowerCase();
  let mejor = null;
  DIAPOS.forEach((d, n) => {
    if (d.archivo === nombre && (mejor === null || Math.abs(n - actual) < Math.abs(mejor - actual))) mejor = n;
  });
  return mejor;
}

// Buscar la diapo de la canción que suena ("Artista - Título" del tracklist de VirtualDJ)
function buscar(texto) {
  const q = new Set(norm(texto).split(" ").filter(Boolean));
  if (!q.size) return null;
  let mejor = null, puntos = 0;
  DIAPOS.forEach((d, n) => {
    if (!d.clave) return;
    const c = norm(d.clave).split(" ").filter(Boolean);
    const comunes = c.filter(p => q.has(p)).length;
    // parecido, y a igualdad, la más cercana después de la actual (por si un tema se repite)
    const p = comunes / Math.max(c.length, q.size) - (n < actual ? 0.001 : 0) - Math.abs(n - actual) * 1e-6;
    if (p > puntos) { puntos = p; mejor = n; }
  });
  return puntos >= 0.5 ? mejor : null;
}

// Modo en vivo: solo si la sirve TangoTags (📽 Proyectar en vivo). Abierta como archivo o desde GitHub no hay
// servidor: se deja de preguntar a la primera y no se toca el aviso de abajo (el del micrófono o el reloj).
let hayServidor = null;              // null = sin comprobar, true / false
async function vivo() {
  if (location.protocol === "file:" || hayServidor === false) return;
  const estado = document.getElementById("estado");
  try {
    const r = await fetch("ahora", {cache: "no-store"});
    if (!r.ok || !(r.headers.get("content-type") || "").includes("json")) throw new Error("sin servidor");
    const j = await r.json();
    hayServidor = true;
    estado.querySelector("span").textContent = "en vivo";
    if (!enVivo) { enVivo = true; largo = 0; pintarReloj(); }      // con conexión manda el ordenador, no el reloj
    const id = (j.ruta || "") + "|" + (j.texto || "");
    if (j.texto && id !== ultimoTexto) {
      ultimoTexto = id;
      const n = porArchivo(j.ruta) ?? buscar(j.texto);
      if (n !== null) ir(n);
      else libre(j.texto);          // algo que no está en la presentación (reserva, cumpleaños…)
    }
  } catch (e) {
    if (hayServidor === null) { hayServidor = false; return; }      // nunca hubo servidor: no insistir
    // había servidor y se ha perdido la conexión: vuelve el reloj
    if (!reconociendo) estado.querySelector("span").textContent = "por tiempo · toca al empezar cada tanda";
    if (enVivo) { enVivo = false; inicio = ahora(); largo = duracionDe(destino); }
  }
}

function pantallaCompleta() {
  const el = document.documentElement;
  if (document.fullscreenElement || document.webkitFullscreenElement) {
    quiereCompleta = false;                 // salió a propósito: no volver a entrar con el primer toque
    (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  } else {
    quiereCompleta = true;
    (el.requestFullscreen || el.webkitRequestFullscreen || (() => {})).call(el);
  }
  despierta();
}
document.addEventListener("keydown", e => {
  if (["ArrowRight", "PageDown", " ", "Enter"].includes(e.key)) { ir(paso(destino, 1)); e.preventDefault(); }
  else if (["ArrowLeft", "PageUp", "Backspace"].includes(e.key)) { ir(paso(destino, -1)); e.preventDefault(); }
  else if (e.key === "Home") ir(0);
  else if (e.key === "End") ir(DIAPOS.length - 1);
  else if (e.key.toLowerCase() === "f") pantallaCompleta();
  else if (e.key.toLowerCase() === "p") pausa();
  else if (e.key === "?" || e.key.toLowerCase() === "h") document.getElementById("ayuda").classList.toggle("visible");
  else if (e.key === "Escape") { document.getElementById("ayuda").classList.remove("visible");
                                 document.getElementById("tandas").classList.remove("visible"); }
  else if (e.key.toLowerCase() === "t") abrirTandas();
});
// Botones (no avanzan la diapo al tocarlos)
const boton = (id, accion) => document.getElementById(id).addEventListener("click", e => {
  e.stopPropagation(); despierta(); mostrarBotones(); accion(); });
boton("b-atras", () => ir(paso(destino, -1)));
boton("b-pausa", pausa);
boton("b-adelante", () => ir(paso(destino, 1)));
boton("b-ayuda", () => { cerrarMas(); document.getElementById("ayuda").classList.toggle("visible"); });
boton("b-tandas", abrirTandas);
const panel = id => document.getElementById(id);
boton("b-mas", () => panel("mas").classList.add("visible"));
panel("mas").addEventListener("click", e => {          // tocar fuera de los botones cierra el panel
  e.stopPropagation(); if (e.target === e.currentTarget) e.currentTarget.classList.remove("visible"); });
const cerrarMas = () => panel("mas").classList.remove("visible");
boton("b-cerrar", cerrarMas);
boton("b-cumple", () => { cerrarMas(); pedir("¿Quién cumple años?", "", nombre => { if (nombre) cumple(nombre); }); });
const PLANTILLAS = ["Última tanda 💃", "¡Gracias por venir! 🙏", "Un aplauso para la organización 👏",
                    "Próxima milonga: ", "¡Feliz cumpleaños, !", "Sin mensaje"];
boton("b-mensaje", () => { cerrarMas(); pedir("Mensaje para las cortinas (vacío = sin mensaje):", mensaje, texto => {
  mensaje = texto; guarda("mensaje", texto); const n = destino, ini = inicio; destino = -1; ir(n, ini); }, PLANTILLAS); });
boton("b-listo", () => { cerrarMas(); abrirListo(); });
boton("b-ensayo", () => { cerrarMas(); ensayar(true); });
boton("b-fin-ensayo", () => ensayar(false));
boton("b-micro", () => { cerrarMas(); activarReconocer(); });
panel("cumple").addEventListener("click", e => { e.stopPropagation(); e.currentTarget.classList.remove("visible"); });
panel("pedir").addEventListener("click", e => e.stopPropagation());
const pista = document.getElementById("pista");
let arrastrando = false;
pista.addEventListener("pointerdown", e => { arrastrando = true; pista.setPointerCapture(e.pointerId);
                                             buscarEnBarra(e); mostrarBotones(); });
pista.addEventListener("pointermove", e => { if (arrastrando) { buscarEnBarra(e); mostrarBotones(); } });
pista.addEventListener("pointerup", () => { arrastrando = false; });
document.getElementById("reproductor").addEventListener("click", e => e.stopPropagation());
boton("b-bloqueo", () => { ponerBloqueo(!bloqueado); cerrarMas(); });
boton("b-simple", () => { ponerSimple(!simple); cerrarMas(); });
document.getElementById("tandas").addEventListener("click", e => {
  e.stopPropagation();
  const b = e.target.closest("button");
  e.currentTarget.classList.remove("visible");
  if (b && b.dataset.n !== undefined) ir(parseInt(b.dataset.n));
});
boton("b-completa", () => { cerrarMas(); pantallaCompleta(); });
document.getElementById("ayuda").addEventListener("click", e => {
  e.stopPropagation(); e.currentTarget.classList.remove("visible"); guarda("ayuda_vista", true);
  despertarOido(); despierta(); pantallaCompleta(); });
// Algunos navegadores no dejan sonar/escuchar hasta el primer toque: cualquier toque lo despierta
function despertarOido() {
  if (entrada && entrada.ctx.state === "suspended") {
    entrada.ctx.resume().then(() => {
      if (reconociendo) document.getElementById("estado").querySelector("span").textContent = "🎤 escuchando…";
    });
  }
}
document.addEventListener("pointerdown", despertarOido, true);
// Pantalla completa: los navegadores no dejan entrar sola al abrir, así que entra con el primer toque
// (salvo que se haya salido a propósito con el botón ⛶)
let quiereCompleta = true;
document.addEventListener("pointerup", e => {
  if (e.target.closest && e.target.closest("#b-completa, #ayuda")) return;     // esos ya lo gestionan
  const ya = document.fullscreenElement || document.webkitFullscreenElement;
  if (quiereCompleta && !ya) {
    const el = document.documentElement;
    try { (el.requestFullscreen || el.webkitRequestFullscreen).call(el).catch?.(() => {}); } catch (e) {}
  }
}, true);
// Tocar la diapo: a la derecha (2/3 de la pantalla) avanza, a la izquierda retrocede
document.addEventListener("click", e => {
  despierta(); mostrarBotones();
  if (bloqueado) return;            // bloqueado: tocar sin querer no pasa diapos (los botones sí funcionan)
  ir(e.clientX > innerWidth / 3 ? paso(destino, 1) : paso(destino, -1)); });
// Botones y cursor se apagan solos a los 4 s sin tocar; vuelven al tocar o mover el ratón
let quieto;
function mostrarBotones() {
  document.body.classList.remove("quieto"); clearTimeout(quieto);
  quieto = setTimeout(() => document.body.classList.add("quieto"), 4000);
}
document.addEventListener("mousemove", mostrarBotones);
document.addEventListener("touchstart", mostrarBotones, {passive: true});
mostrarBotones();
// ≡ Tandas: ir directo a cualquier tanda (si se ha perdido la cuenta)
function abrirTandas() {
  const aqui = DIAPOS[destino] && DIAPOS[destino].tipo !== "cortina" ? DIAPOS[destino].numero : null;
  const filas = [`<button data-n="0">Portada</button>`];
  DIAPOS.forEach((d, n) => {
    if ((d.tipo === "tema" && d.actual === 0) || d.tipo === "cumparsita") {
      const etiqueta = d.tipo === "cumparsita" ? "Último baile ·" : d.numero + ".";
      filas.push(`<button data-n="${n}" class="${d.tipo === "tema" && d.numero === aqui ? "aqui" : ""}">` +
        `<b class="${d.tipo === "cumparsita" ? "final" : d.genero}"></b>${etiqueta} ` +
        `${esc(d.orquesta.replace(/^Orquesta de /, ""))} <i>${esc(d.subtitulo)}</i></button>`);
    }
  });
  const caja = document.getElementById("tandas");
  caja.innerHTML = `<h3>Ir a la tanda… <small style="font-size:.6em;color:var(--suave)">` +
    `(empieza por su primer tema; toca fuera para cerrar)</small></h3><div class="rejilla">${filas.join("")}</div>`;
  caja.classList.add("visible");
}

function ponerBloqueo(si) {
  bloqueado = si; guarda("bloqueado", si);
  document.body.classList.toggle("bloqueado", si);
  document.getElementById("b-bloqueo").innerHTML = si ? "🔒 Toques bloqueados<small>toca para desbloquear</small>"
                                                      : "🔓 Bloquear toques<small>tocar la pantalla no pasa diapos</small>";
}

function ponerSimple(si) {
  simple = si; guarda("simple", si);
  document.body.classList.toggle("simple", si);
  document.getElementById("b-simple").innerHTML = si ? "Simple ✓<small>toca para ver cada tema</small>"
                                                    : "Simple<small>una diapo por tanda</small>";
  const n = destino, ini = inicio; destino = -1; ir(n, ini);   // repinta; el reloj sigue desde cuando empezó
}

setInterval(tic, 250);

// Pedir un texto con un teclado en pantalla (cumpleaños, mensaje)
function pedir(pregunta, valor, hecho, opciones = []) {
  const v = panel("pedir-valor");
  panel("pedir-texto").textContent = pregunta;
  // plantillas: tocar una la pone en el cuadro (las que acaban en espacio o en ", !" esperan que se complete)
  const caja = panel("pedir-opciones");
  caja.innerHTML = opciones.map(o => `<button>${esc(o)}</button>`).join("");
  caja.querySelectorAll("button").forEach((b, k) => b.onclick = e => {
    e.stopPropagation();
    const o = opciones[k];
    v.value = o === "Sin mensaje" ? "" : o;
    v.focus();
    const hueco = o.indexOf(", !");
    const pos = hueco >= 0 ? hueco + 2 : v.value.length;
    v.setSelectionRange(pos, pos);
  });
  v.value = valor || "";
  panel("pedir").classList.add("visible");
  setTimeout(() => v.focus(), 50);
  const cerrar = ok => { panel("pedir").classList.remove("visible");
                         panel("pedir-si").onclick = panel("pedir-no").onclick = v.onkeydown = null;
                         if (ok) hecho(v.value.trim()); };
  panel("pedir-si").onclick = e => { e.stopPropagation(); cerrar(true); };
  panel("pedir-no").onclick = e => { e.stopPropagation(); cerrar(false); };
  v.onkeydown = e => { e.stopPropagation(); if (e.key === "Enter") cerrar(true); if (e.key === "Escape") cerrar(false); };
}

// 🎂 Cumpleaños con confeti (el reloj sigue: al cerrar, todo sigue donde iba)
function cumple(nombre) {
  const caja = panel("cumple");
  caja.querySelectorAll("i").forEach(i => i.remove());
  panel("cumple-quien").textContent = nombre;
  const colores = ["#d9a441", "#6fbf8a", "#e0784a", "#c9a0ff", "#f6efe4", "#e05a5a"];
  for (let k = 0; k < 70; k++) {
    const i = document.createElement("i");
    i.style.left = Math.random() * 100 + "vw";
    i.style.background = colores[k % colores.length];
    i.style.animationDuration = 3 + Math.random() * 4 + "s";
    i.style.animationDelay = -Math.random() * 6 + "s";
    caja.appendChild(i);
  }
  caja.classList.add("visible");
}

function aviso(texto, grande = false) {
  const a = panel("aviso");
  a.textContent = texto; a.classList.add("visible"); a.classList.toggle("grande", grande);
  clearTimeout(aviso.t);
  aviso.t = setTimeout(() => a.classList.remove("visible"), grande ? 20000 : Math.max(4000, texto.length * 80));
}

// 🎤 Ecualizador con el micrófono (opcional): si no hay permiso, siguen latiendo al BPM
// ---------------------------------------------------------------- micrófono (compartido)
let entrada = null;                  // {ctx, fuente}
async function microfono() {
  if (entrada) return entrada;
  const flujo = await navigator.mediaDevices.getUserMedia(
    {audio: {echoCancellation: false, noiseSuppression: false, autoGainControl: true}});
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  if (ctx.state === "suspended") await ctx.resume();
  entrada = {ctx, fuente: ctx.createMediaStreamSource(flujo)};
  return entrada;
}

// Ecualizador con el micrófono: las barras con la música real
let microActivo = false;
function ecualizadorMicro({ctx, fuente}) {
  if (microActivo) return;
  const analizador = ctx.createAnalyser();
  analizador.fftSize = 64;
  fuente.connect(analizador);
  const datos = new Uint8Array(analizador.frequencyBinCount);
  microActivo = true;
  document.body.classList.add("micro");
  const bandas = [1, 2, 3, 5, 7, 10, 14];
  (function mover() {
    analizador.getByteFrequencyData(datos);
    document.querySelectorAll(".eq").forEach(eq => eq.querySelectorAll("i").forEach((i, k) => {
      const v = pausado ? 0.15 : Math.max(0.12, datos[bandas[k]] / 255);
      i.style.transform = `scaleY(${v.toFixed(2)})`;
    }));
    requestAnimationFrame(mover);
  })();
}

// ---------------------------------------------------------------- reconocer la canción por el sonido
// Lo mismo que src/diapos/huellas.py: espectrograma a 8 kHz, picos, parejas de picos -> códigos; los códigos
// que coinciden con los de una canción con el mismo desfase votan por esa canción y ese segundo.
const H = {F: 8000, N: 1024, SALTO: 256, VF: 15, VT: 15, PICOS: 25, PAREJAS: 6, DTMIN: 1, DTMAX: 64, BMIN: 6, BMAX: 480};
const HANN = Float32Array.from({length: H.N}, (_, n) => 0.5 - 0.5 * Math.cos(2 * Math.PI * n / (H.N - 1)));

const fft = (() => {                 // FFT real de 1024 puntos -> magnitud en dB (N/2 + 1 bandas)
  const N = H.N, bits = Math.log2(N), rev = new Uint16Array(N);
  const co = new Float64Array(N / 2), si = new Float64Array(N / 2), re = new Float64Array(N), im = new Float64Array(N);
  for (let i = 0; i < N; i++) { let r = 0; for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b); rev[i] = r; }
  for (let i = 0; i < N / 2; i++) { co[i] = Math.cos(-2 * Math.PI * i / N); si[i] = Math.sin(-2 * Math.PI * i / N); }
  return (x, salida) => {
    for (let i = 0; i < N; i++) { re[rev[i]] = x[i]; im[rev[i]] = 0; }
    for (let tam = 2; tam <= N; tam <<= 1) {
      const mitad = tam >> 1, paso = N / tam;
      for (let i = 0; i < N; i += tam) for (let j = 0; j < mitad; j++) {
        const k = j * paso, a = i + j, b = a + mitad;
        const tr = re[b] * co[k] - im[b] * si[k], ti = re[b] * si[k] + im[b] * co[k];
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
      }
    }
    for (let i = 0; i <= N / 2; i++) salida[i] = 20 * Math.log10(Math.hypot(re[i], im[i]) + 1e-6);
  };
})();

function huella(m) {                 // [[código, columna], …] de unas muestras a 8 kHz
  const n = m.length < H.N ? 0 : 1 + Math.floor((m.length - H.N) / H.SALTO);
  if (!n) return [];
  const B = H.BMAX - H.BMIN, zona = new Float32Array(B * n);
  const marco = new Float32Array(H.N), col = new Float32Array(H.N / 2 + 1);
  for (let t = 0; t < n; t++) {
    const o = t * H.SALTO;
    for (let i = 0; i < H.N; i++) marco[i] = m[o + i] * HANN[i];
    fft(marco, col);
    for (let b = 0; b < B; b++) zona[b * n + t] = col[b + H.BMIN];
  }
  const mf = new Float32Array(B * n), mx = new Float32Array(B * n);
  for (let t = 0; t < n; t++) for (let b = 0; b < B; b++) {
    let v = -Infinity;
    for (let k = Math.max(0, b - H.VF), f = Math.min(B - 1, b + H.VF); k <= f; k++) if (zona[k * n + t] > v) v = zona[k * n + t];
    mf[b * n + t] = v;
  }
  for (let b = 0; b < B; b++) for (let t = 0; t < n; t++) {
    let v = -Infinity;
    for (let k = Math.max(0, t - H.VT), f = Math.min(n - 1, t + H.VT); k <= f; k++) if (mf[b * n + k] > v) v = mf[b * n + k];
    mx[b * n + t] = v;
  }
  const ordenada = Float32Array.from(zona).sort();
  const umbral = ordenada[Math.floor(ordenada.length / 2)] + 10;
  let picos = [];
  for (let b = 0; b < B; b++) for (let t = 0; t < n; t++) {
    const v = zona[b * n + t];
    if (v === mx[b * n + t] && v > umbral) picos.push([t, b + H.BMIN, v]);
  }
  const maximo = Math.max(1, Math.floor(n * H.SALTO / H.F * H.PICOS));
  if (picos.length > maximo) picos = picos.sort((a, c) => c[2] - a[2]).slice(0, maximo);
  picos.sort((a, c) => a[0] - c[0] || a[1] - c[1]);
  const salida = [];
  for (let i = 0; i < picos.length; i++) {
    const [t1, f1] = picos[i];
    let parejas = 0;
    for (let j = i + 1; j < picos.length; j++) {
      const dt = picos[j][0] - t1;
      if (dt < H.DTMIN) continue;
      if (dt > H.DTMAX || parejas >= H.PAREJAS) break;
      salida.push([((f1 & 511) << 15) | ((picos[j][1] & 511) << 6) | (dt & 63), t1]);
      parejas++;
    }
  }
  return salida;
}

let indiceHuellas = null;            // código -> [diapo * 65536 + columna, …]
function prepararIndice() {
  if (indiceHuellas) return indiceHuellas;
  indiceHuellas = new Map();
  const bytes = b64 => Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer;
  for (const [diapo, [c64, t64]] of Object.entries(HUELLAS)) {
    const codigos = new Uint32Array(bytes(c64)), cols = new Uint16Array(bytes(t64)), d = Number(diapo) * 65536;
    for (let i = 0; i < codigos.length; i++) {
      let lista = indiceHuellas.get(codigos[i]);
      if (!lista) indiceHuellas.set(codigos[i], lista = []);
      lista.push(d + cols[i]);
    }
  }
  return indiceHuellas;
}

function reconocer(h) {              // {diapo, segundo (al final del trozo), votos} o null
  const indice = prepararIndice(), votos = new Map();
  let ultimo = 0;
  for (const [, t] of h) if (t > ultimo) ultimo = t;
  for (const [codigo, t] of h) {
    const lista = indice.get(codigo);
    if (!lista) continue;
    for (const x of lista) {
      const clave = Math.floor(x / 65536) * 1000000 + ((x % 65536) - t + 500000);
      votos.set(clave, (votos.get(clave) || 0) + 1);
    }
  }
  let mejor = null;
  for (const [clave, v] of votos) {
    const total = v + (votos.get(clave - 1) || 0) + (votos.get(clave + 1) || 0);
    if (!mejor || total > mejor.votos) {
      mejor = {diapo: Math.floor(clave / 1000000), desfase: (clave % 1000000) - 500000, votos: total};
    }
  }
  if (!mejor) return null;
  return {diapo: mejor.diapo, segundo: (mejor.desfase + ultimo) * H.SALTO / H.F, votos: mejor.votos};
}

// Lo que se oye: los últimos ESCUCHA segundos a 8 kHz (remuestreado del micrófono)
const ESCUCHA = 8;
const oido = {buf: new Float32Array(ESCUCHA * H.F), w: 0, lleno: 0, acc: 0, n: 0, fase: 0};
function grabar({ctx, fuente}) {
  const nodo = ctx.createScriptProcessor(4096, 1, 1);
  const ratio = ctx.sampleRate / H.F;
  nodo.onaudioprocess = e => {
    const x = e.inputBuffer.getChannelData(0);
    for (let i = 0; i < x.length; i++) {   // media de cada grupo de muestras -> 8 kHz
      oido.acc += x[i]; oido.n++; oido.fase += 1;
      if (oido.fase >= ratio) {
        oido.fase -= ratio;
        oido.buf[oido.w] = oido.acc / oido.n; oido.w = (oido.w + 1) % oido.buf.length;
        oido.lleno = Math.min(oido.buf.length, oido.lleno + 1); oido.acc = 0; oido.n = 0;
      }
    }
  };
  const mudo = ctx.createGain(); mudo.gain.value = 0;
  fuente.connect(nodo); nodo.connect(mudo); mudo.connect(ctx.destination);
  oido.nodo = nodo;
}
function ultimosSegundos() {
  const b = oido.buf, salida = new Float32Array(b.length);
  salida.set(b.subarray(oido.w)); salida.set(b.subarray(0, oido.w), b.length - oido.w);
  return salida;
}

// Diapo y segundo dentro de ella para una canción reconocida (en modo simple, la diapo es la de la tanda)
function dondeVa(diapo, segundo) {
  const d = DIAPOS[diapo];
  // en la cortina el reloj es la espera hasta la tanda, no el segundo de la canción: empieza a contar ahora
  // (y el oído reconocerá cuándo empieza de verdad la tanda)
  if (d.tipo === "cortina") return [diapo, 0];
  if (!(simple && d.tipo === "tema" && d.actual > 0)) return [diapo, segundo];
  let base = diapo - d.actual, antes = 0;
  for (let k = base; k < diapo; k++) antes += (DIAPOS[k].duracion || 0) + PAUSA;
  return [base, antes + segundo];
}

// Las reglas: el reloj manda; el oído solo corrige si oye otra cosa (o el tema va desfasado)
let reconociendo = false, oidas = [];
function escuchar() {
  if (!reconociendo || oido.lleno < oido.buf.length || pausado || enVivo || ensayo) return;
  const r = reconocer(huella(ultimosSegundos()));
  const estado = document.getElementById("estado").querySelector("span");
  if (!r || r.votos < 3) { estado.textContent = "🎤 escuchando…"; oidas = []; return; }
  r.cuando = Date.now();
  oidas = oidas.concat([r]).slice(-3);
  // ¿coinciden con las anteriores (misma canción y el segundo avanza lo mismo que el reloj)?
  const coherentes = oidas.filter(o => o.diapo === r.diapo &&
    Math.abs((r.segundo - o.segundo) - (r.cuando - o.cuando) / 1000) <= 1.5).length;
  const [diapo, segundo] = dondeVa(r.diapo, r.segundo);
  const titulo = DIAPOS[r.diapo].tipo === "cortina" ? "cortina" : (DIAPOS[r.diapo].temas || [])[DIAPOS[r.diapo].actual]?.titulo;
  if (diapo === destino) {
    // el tema que toca: corregir el reloj si va desfasado
    if ((coherentes >= 2 || r.votos >= 6) && largo && DIAPOS[diapo].tipo !== "cortina") {
      const desfase = segundo * 1000 - lleva();
      if (Math.abs(desfase) > 2500) { inicio = ahora() - segundo * 1000; pintarReloj(); }
    }
    estado.textContent = `🎤 ✓ ${titulo || ""}`;
    ultimoAcierto = Date.now();
    return;
  }
  // otra canción: saltar solo si se confirma (y más confirmaciones si es un salto raro)
  const necesarias = Math.abs(diapo - destino) <= 4 ? 2 : 3;
  estado.textContent = `🎤 ¿${titulo || ""}? (${coherentes}/${necesarias})`;
  if (coherentes >= necesarias) {
    ir(diapo, ahora() - segundo * 1000);
    estado.textContent = `🎤 → ${titulo || ""}`;
    ultimoAcierto = Date.now();
    oidas = [];
  }
}

// 🎤 Reconocer canción: se enciende sola al abrir (si se dejó encendida) y el botón la enciende o apaga
let grabando = false;
function ponerBotonMicro() {
  document.getElementById("b-micro").innerHTML = reconociendo
    ? "🎤 Reconociendo ✓<small>toca para apagarlo (seguirá el reloj)</small>"
    : "🎤 Reconocer canción<small>escucha y corrige solo; si no, sigue el reloj</small>";
}

async function activarReconocer(automatico = false) {
  if (reconociendo && !automatico) {               // apagar
    reconociendo = false; guarda("reconocer", false); ponerBotonMicro();
    document.getElementById("estado").querySelector("span").textContent = "por tiempo · toca al empezar cada tanda";
    aviso("🎤 Apagado: sigue el reloj");
    return;
  }
  if (!Object.keys(HUELLAS).length) {
    if (!automatico) aviso("Esta presentación no lleva las huellas de audio: créala de nuevo desde TangoTags");
    return;
  }
  const estado = document.getElementById("estado").querySelector("span");
  try {
    const e = await microfono();
    ecualizadorMicro(e);
    if (!grabando) {
      prepararIndice();
      grabar(e);
      grabando = true;
      setInterval(escuchar, 4000);
    }
    reconociendo = true; microFallo = false; guarda("reconocer", true); ponerBotonMicro();
    if (e.ctx.state === "suspended") estado.textContent = "🎤 toca la pantalla una vez para empezar a escuchar";
    else { estado.textContent = "🎤 escuchando…"; aviso("🎤 Escuchando: irá sola a lo que suene (el reloj sigue de respaldo)"); }
  } catch (err) {
    estado.textContent = "por tiempo · toca al empezar cada tanda";
    microFallo = true;
    // decir por qué (para poder arreglarlo)
    let porque;
    if (!window.isSecureContext || !navigator.mediaDevices) {
      porque = "este navegador no deja usar el micrófono en un archivo abierto así (" + location.protocol +
               "). Prueba con Firefox o sirviéndola desde la propia tablet";
    } else if (err && err.name === "NotAllowedError") {
      porque = "permiso denegado. Mira Ajustes de Android → Aplicaciones → Chrome → Permisos → Micrófono → " +
               "Permitir, y en Chrome el candado/ajustes del sitio → Micrófono → Permitir";
    } else if (err && err.name === "NotFoundError") {
      porque = "no se encuentra ningún micrófono";
    } else {
      porque = (err && (err.name + ": " + err.message)) || "error desconocido";
    }
    aviso("🎤 No se pudo usar el micrófono: " + porque + ". Sigue el reloj como siempre.");
  }
}

// ---------------------------------------------------------------- punto de estado (abajo a la derecha)
// verde: sabe lo que suena (en vivo, o el micrófono lo ha reconocido hace poco); amarillo: por tiempo; rojo: el
// micrófono no funciona
let ultimoAcierto = 0, microFallo = false;
function ponerPunto() {
  document.getElementById("estado").dataset.punto =
    enVivo || (reconociendo && Date.now() - ultimoAcierto < 45000) ? "verde"
    : microFallo && Object.keys(HUELLAS).length ? "rojo" : "amarillo";
}
setInterval(ponerPunto, 1000);

// ---------------------------------------------------------------- batería: avisar al 20 % y al 10 %
let bateria = null, avisadaBateria = 1;
function mirarBateria() {
  if (!bateria || bateria.charging) { avisadaBateria = 1; return; }
  const umbral = [0.1, 0.2].find(u => bateria.level <= u && avisadaBateria > u);
  if (umbral !== undefined) {
    avisadaBateria = umbral;
    aviso(`🔋 La tablet tiene ${Math.round(bateria.level * 100)} % de batería: enchúfala`, true);
  }
}
if (navigator.getBattery) {
  navigator.getBattery().then(b => {
    bateria = b;
    b.addEventListener("levelchange", mirarBateria); b.addEventListener("chargingchange", mirarBateria);
    mirarBateria();
  }).catch(() => {});
}

// ---------------------------------------------------------------- ✓ ¿Todo listo? (al abrir y en ⋯ Más)
async function comprobar() {
  const cosas = [];
  const pon = (ok, que, detalle = "") => cosas.push(
    `<li class="${ok === true ? "si" : ok === false ? "no" : "medio"}"><b>${ok === true ? "✓" : ok === false ? "✗" : "!"}</b>` +
    `<span>${que}</span>${detalle ? `<small>${detalle}</small>` : ""}</li>`);
  // sin internet
  if (location.protocol === "file:") pon(true, "Funciona sin internet", "abierta como archivo de este aparato");
  else if (hayServidor) pon(true, "Conectada al portátil (en vivo)", "sigue sola a lo que suena en Mixxx");
  else {
    let guardada = false;
    try { guardada = !!(await caches.match(location.pathname, {ignoreSearch: true})); } catch (e) {}
    pon(guardada, guardada ? "Guardada para usar sin internet" : "Aún no está guardada para usar sin internet",
        guardada ? "si se recarga o se cierra Chrome sin red, vuelve a abrir" : "ábrela una vez con wifi y recarga la página");
  }
  // micrófono
  if (!Object.keys(HUELLAS).length) pon(null, "Sin reconocimiento por sonido", "esta presentación no lo lleva: va por tiempo");
  else if (reconociendo && entrada && entrada.ctx.state === "running") {
    const reciente = ultimoAcierto && Date.now() - ultimoAcierto < 60000;
    pon(true, "Micrófono escuchando", reciente ? "ya ha reconocido lo que suena" : "aún no ha reconocido nada (normal si no suena música)");
  } else if (reconociendo) pon(null, "Micrófono preparado", "toca la pantalla una vez para que empiece a escuchar");
  else pon(false, "Micrófono apagado", microFallo ? "no se pudo usar: ⋯ Más → 🎤 dice por qué. Sigue el reloj" : "⋯ Más → 🎤 Reconocer canción");
  // pantalla
  const completa = !!(document.fullscreenElement || document.webkitFullscreenElement)
    || matchMedia("(display-mode: fullscreen)").matches || matchMedia("(display-mode: standalone)").matches;
  pon(completa, "Pantalla completa", completa ? "" : "se pone sola al tocar la pantalla");
  const despierta_ = !!(pantallaDespierta && !pantallaDespierta.released);
  pon(despierta_ ? true : null, despierta_ ? "La pantalla no se apagará" : "La pantalla podría apagarse sola",
      despierta_ ? "" : "toca la pantalla una vez; si aun así se apaga, sube el tiempo en Ajustes → Pantalla");
  // batería
  if (bateria) {
    const p = Math.round(bateria.level * 100);
    pon(bateria.charging || p > 40 ? true : p > 20 ? null : false, `Batería ${p} %`,
        bateria.charging ? "cargando" : p > 40 ? "sin enchufar: mejor enchúfala si puedes" : "¡enchúfala!");
  }
  // modo
  pon(true, "Si algo falla, no pasa nada", "va por tiempo: toca la pantalla cuando empiece cada tanda");
  panel("listo-cosas").innerHTML = cosas.join("");
}
let listoTocado = false;
function abrirListo() {
  listoTocado = false;
  panel("listo-cerrar").textContent = "Toca una vez para activar lo que falta (pantalla completa, micrófono…)";
  panel("listo").classList.add("visible");
  comprobar();
  clearInterval(abrirListo.t);
  abrirListo.t = setInterval(() => panel("listo").classList.contains("visible") ? comprobar() : clearInterval(abrirListo.t), 1000);
  clearTimeout(abrirListo.cierra);
  abrirListo.cierra = setTimeout(() => panel("listo").classList.remove("visible"), 45000);   // no tapar la noche
}
panel("listo").addEventListener("click", e => {
  e.stopPropagation(); despierta();
  if (!listoTocado) { listoTocado = true; panel("listo-cerrar").textContent = "Toca otra vez para cerrar"; comprobar(); return; }
  e.currentTarget.classList.remove("visible");
});

// ---------------------------------------------------------------- 🎬 ensayo rápido
function ensayar(si) {
  if (pausado) pausa();
  ensayo = si; baseReal = baseEnsayo = Date.now();
  document.body.classList.toggle("ensayo", si);
  destino = -1;
  if (si) { ir(paso(0, 1)); aviso("🎬 Ensayo: la noche pasa 60 veces más deprisa. ■ Terminar arriba"); }
  else { ir(lee("diapo", 0)); aviso("Ensayo terminado: vuelve donde estaba"); }
}

// La hora, discreta en la esquina
function ponerHora() {
  const h = new Date();
  document.getElementById("hora").textContent = `${h.getHours()}:${String(h.getMinutes()).padStart(2, "0")}`;
}
ponerHora(); setInterval(ponerHora, 10000);

ponerBloqueo(bloqueado);
document.body.classList.toggle("simple", simple);
document.getElementById("b-simple").innerHTML = simple ? "Simple ✓<small>toca para ver cada tema</small>"
                                                      : "Simple<small>una diapo por tanda</small>";
mensaje = lee("mensaje", "");
// Arranque: la diapo del enlace (#n) o la última en la que estaba (si se cerró o se recargó)
actual = -1; destino = -1;
ir(location.hash.length > 1 ? (parseInt(location.hash.slice(1)) || 0) : lee("diapo", 0));
vivo(); setInterval(vivo, 1500);

// Publicada (https): guardarla en la tablet para que, si se recarga sin internet, abra la copia guardada
if (window.isSecureContext && location.protocol.startsWith("http") && "serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").then(async () => {
    try {
      const cache = await caches.open("milongas-v1");
      if (!(await cache.match(location.pathname, {ignoreSearch: true}))) await cache.add(location.pathname);
    } catch (e) {}
  }).catch(() => {});
}

// Al abrir: la ayuda solo la primera vez en esta tablet (y se cierra sola a los 20 s para no tapar nada),
// y si la presentación lleva huellas, empieza a escuchar sola (salvo que se apagara a propósito)
if (!lee("ayuda_vista", false)) {
  document.getElementById("ayuda").classList.add("visible");
  setTimeout(() => { document.getElementById("ayuda").classList.remove("visible"); guarda("ayuda_vista", true); }, 20000);
} else {
  setTimeout(abrirListo, 600);        // ¿todo listo? (da tiempo a que arranque el micrófono)
}
ponerBotonMicro();
if (location.protocol === "file:" || !enVivo) {
  if (Object.keys(HUELLAS).length && lee("reconocer", true)) activarReconocer(true);
}
</script></body></html>
"""
