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
import io
import json
import os

from src.config.config import background_image_folder
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
                    "clave": f"{c['artist']} - {c['title']}", "archivo": _archivo(c['ruta']),
                    "proxima": None if proxima is None else {
                        "orquesta": proxima.titulo_orquesta, "subtitulo": proxima.subtitulo,
                        "genero": "final" if proxima.es_cumparsita else _genero(proxima.genero),
                        "foto": foto(proxima.orquesta), "iniciales": _iniciales(proxima.orquesta or "?"),
                        "numero": None if proxima.es_cumparsita else numero + 1, "total": len(reales)},
                })
            continue
        if not t.es_cumparsita:
            numero += 1
        temas = [{"titulo": c["title"], "ano": c["ano"], "autores": compositor_para_diapo(c["composer"]),
                  "cantor": c["artist2"]} for _, c in t.canciones.iterrows()]
        for k, (_, c) in enumerate(t.canciones.iterrows()):
            salida.append({
                "tipo": "cumparsita" if t.es_cumparsita else "tema", "numero": numero, "total": len(reales),
                "orquesta": t.titulo_orquesta, "subtitulo": t.subtitulo, "genero": _genero(t.genero),
                "foto": foto(t.orquesta), "iniciales": _iniciales(t.orquesta or "?"),
                "temas": temas, "actual": k, "duracion": round(float(c["duration"] or 0), 1), "bpm": _bpm(c), "clave": f"{c['artist']} - {c['title']}", "archivo": _archivo(c['ruta']),
            })
    return salida, imagenes


def crear_web(tandas, datos, destino):
    lista, imagenes = diapos(tandas, datos)
    fondo = os.path.join(background_image_folder, "background_tango_degradado.png")
    try:
        fondo_uri = _imagen_base64(fondo, ancho=1600, calidad=80)
    except Exception:
        fondo_uri = ""
    html = (PLANTILLA
            .replace("__TITULO__", f"{datos['milonga']} · {fecha_larga(datos['fecha'])}")
            .replace("__DIAPOS__", json.dumps(lista, ensure_ascii=False))
            .replace("__IMAGENES__", json.dumps(imagenes))
            .replace("__FONDO__", fondo_uri)
            .replace("__FIRMA__", f"TDJ {FIRMA_DJ} · {datos['milonga']}"))
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(html)
    return destino


PLANTILLA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title>
<style>
  :root { --tango:#d9a441; --vals:#6fbf8a; --milonga:#e0784a; --final:#c9a0ff; --texto:#f6efe4; --suave:#cdbfae; }
  html,body { margin:0; height:100%; background:#0d0907; color:var(--texto); overflow:hidden;
    font-family: Georgia, "Palatino Linotype", "Book Antiqua", serif; }
  #fondo { position:fixed; inset:-2vw; background:#0d0907 url("__FONDO__") center/cover no-repeat;
    filter:brightness(.28) blur(6px) saturate(.8); }
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
  .cortina .sonando { font:500 1.7vw system-ui, sans-serif; letter-spacing:.25em; text-transform:uppercase; color:var(--suave); }
  .cortina h1 { font-size:4.4vw; } .cortina h2 { margin-bottom:6vh; }
  .proxima { display:inline-flex; align-items:center; gap:2.5vw; padding:2.5vh 3vw; border-radius:2vw; background:rgba(0,0,0,.45); text-align:left; }
  .proxima img, .proxima .emblema { width:14vw; height:14vw; font-size:5vw; }
  .proxima .que { font:500 1.5vw system-ui, sans-serif; letter-spacing:.2em; text-transform:uppercase; color:var(--suave); }
  .proxima .orq { font-size:3.2vw; font-weight:700; margin:.6vh 0; }
  .proxima .sub { font-size:1.8vw; font-style:italic; color:var(--suave); }
  #firma { position:fixed; left:2vw; bottom:1.6vh; font:400 1.1vw system-ui, sans-serif; color:rgba(246,239,228,.45); }
  #estado { position:fixed; right:1.5vw; bottom:1.6vh; font:400 1vw system-ui, sans-serif; color:rgba(246,239,228,.45); }
  #estado b { display:inline-block; width:.9vw; height:.9vw; border-radius:50%; background:#777; margin-right:.5vw; vertical-align:-.1vw; }
  #estado.vivo b { background:#46d36b; box-shadow:0 0 1vw #46d36b; }
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
    background:rgba(13,9,7,.9); border:1px solid var(--tango); font:500 18px system-ui, sans-serif; display:none; }
  #aviso.visible { display:block; }
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
<div id="fondo"></div><div id="velo"></div>
<div id="diapo"></div>
<div id="firma">© __FIRMA__</div>
<div id="hora"></div>
<div id="estado" title="Verde: sigue al ordenador en vivo. Si no, por tiempo: toca al empezar cada tanda"><b></b><span>por tiempo · toca al empezar cada tanda</span></div>
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
  <button id="b-micro">🎤 Ecualizador real<small>las barras con el micrófono</small></button>
  <button id="b-ayuda">? Ayuda<small>cómo funciona</small></button>
  <button id="b-completa">⛶ Pantalla completa</button>
  <button id="b-cerrar">✕ Cerrar</button>
</div></div>
<div id="pedir"><div>
  <div id="pedir-texto"></div>
  <input id="pedir-valor" type="text" autocomplete="off">
  <div class="fila"><button id="pedir-no">Cancelar</button><button id="pedir-si">Aceptar</button></div>
</div></div>
<div id="cumple"><div class="que">¡Feliz cumpleaños!</div><div class="quien" id="cumple-quien"></div>
  <div class="baila">Un vals para celebrarlo</div></div>
<div id="aviso"></div>
<div id="tandas"></div>
<div id="ayuda" class="visible"><div>
  <h3>Cómo funciona</h3>
  <p><b>Sin conexión ni cables (modo «por tiempo»):</b></p>
  <ol>
    <li>Cuando suena la <b>cortina</b>, la pantalla anuncia la próxima tanda. Si no tocas, <b>al minuto</b> empieza sola la tanda.</li>
    <li>Mejor: cuando empieza el <b>primer tema</b> de la tanda, <b>toca la pantalla una vez</b> (en la parte derecha). Si la cortina va a durar más, ⏸ Pausa.</li>
    <li>Los temas avanzan <b>solos</b> según su duración (la barrita dorada de abajo) y al acabar la tanda vuelve a la cortina.</li>
  </ol>
  <p><b>Botones</b> (abajo, grandes; se apagan solos y vuelven al tocar): <b>◀</b> anterior · <b>⏸ Pausa</b> / <b>▶ Seguir</b> (para el reloj: si hablan, cortina larga…) · <b>▶</b> siguiente · <b>≡ Tandas</b> ir directo a una tanda si te pierdes · <b>⋯ Más</b>: 🎂 cumpleaños con confeti · 💬 mensaje en las cortinas · 🔓 bloquear toques (tocar la pantalla sin querer no pasa nada) · Simple (una diapo por tanda) · 🎤 ecualizador con el micrófono · ? ayuda · ⛶ pantalla completa.</p>
  <p><b>Reproductor</b> (encima de los botones): lo que lleva el tema, lo que queda y lo que dura. Si no cuadra con Mixxx, <b>toca o arrastra la barra</b> hasta el punto en que va el tema (por ejemplo, si en Mixxx va por 1:30, ponla en 1:30).</p>
  <p>En la cortina se ve cuándo empezará sola la tanda. Si se cierra o se recarga, al abrirla vuelve a la misma diapo.</p>
  <p>Tocar la pantalla: a la <b>derecha</b> avanza, en el <b>tercio izquierdo</b> retrocede. En un ordenador: flechas, espacio, F = pantalla completa.</p>
  <p><b>Con red</b> (misma wifi, o el punto de acceso de un móvil aunque no tenga datos): en TangoTags, Crear diapos → «📽 Proyectar en vivo», y abrir aquí la dirección que indica. El punto de abajo se pone verde y sigue sola al tema que suena en Mixxx.</p>
  <p class="cerrar">Toca para empezar (y pasar a pantalla completa)</p>
</div></div>
<script>
const DIAPOS = __DIAPOS__;
const IMG = __IMAGENES__;
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

const ahora = () => (pausado ? enPausa : Date.now());
const lleva = () => Math.max(0, Math.min(largo, ahora() - inicio));      // ms que lleva sonando

// Cada cuarto de segundo: pasar a la siguiente si toca (poniéndose al día si el navegador se durmió)
function tic() {
  for (let vueltas = 0; vueltas < 60 && largo && !pausado; vueltas++) {
    const hueco = DIAPOS[destino].tipo === "tema" ? PAUSA * 1000 : 0;
    const fin = inicio + largo + hueco;              // cuándo empieza lo siguiente
    if (Date.now() < fin) break;
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
  if (pausado) { inicio += Date.now() - enPausa; pausado = false; }
  else { enPausa = Date.now(); pausado = true; }
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
  guarda("diapo", n);
  inicio = desde !== undefined ? desde : ahora();
  largo = duracionDe(n);
  pintarReloj();
  const caja = document.getElementById("diapo");
  caja.classList.add("oculta");
  setTimeout(() => { if (destino !== n) return;
                     actual = n; caja.innerHTML = pintar(DIAPOS[n]); caja.classList.remove("oculta");
                     history.replaceState(null, "", "#" + n); }, 180);
}

// Que la pantalla de la tablet no se apague (si el navegador lo permite)
async function despierta() {
  try { if ("wakeLock" in navigator) await navigator.wakeLock.request("screen"); } catch (e) {}
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

async function vivo() {
  if (location.protocol === "file:") return;
  const estado = document.getElementById("estado");
  try {
    const r = await fetch("/ahora", {cache: "no-store"});
    const j = await r.json();
    estado.className = "vivo"; estado.querySelector("span").textContent = "en vivo";
    if (!enVivo) { enVivo = true; largo = 0; pintarReloj(); }      // con conexión manda el ordenador, no el reloj
    const id = (j.ruta || "") + "|" + (j.texto || "");
    if (j.texto && id !== ultimoTexto) {
      ultimoTexto = id;
      const n = porArchivo(j.ruta) ?? buscar(j.texto);
      if (n !== null) ir(n);
      else libre(j.texto);          // algo que no está en la presentación (reserva, cumpleaños…)
    }
  } catch (e) {
    estado.className = ""; estado.querySelector("span").textContent = "por tiempo · toca al empezar cada tanda";
    if (enVivo) { enVivo = false; inicio = ahora(); largo = duracionDe(destino); }
  }
}

function pantallaCompleta() {
  const el = document.documentElement;
  if (document.fullscreenElement || document.webkitFullscreenElement) {
    (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  } else {
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
boton("b-mensaje", () => { cerrarMas(); pedir("Mensaje para las cortinas (vacío = sin mensaje):", mensaje, texto => {
  mensaje = texto; guarda("mensaje", texto); const n = destino, ini = inicio; destino = -1; ir(n, ini); }); });
boton("b-micro", () => { cerrarMas(); micro(); });
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
  e.stopPropagation(); e.currentTarget.classList.remove("visible"); despierta(); pantallaCompleta(); });
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
function pedir(pregunta, valor, hecho) {
  const v = panel("pedir-valor");
  panel("pedir-texto").textContent = pregunta;
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

function aviso(texto) {
  const a = panel("aviso");
  a.textContent = texto; a.classList.add("visible");
  clearTimeout(aviso.t); aviso.t = setTimeout(() => a.classList.remove("visible"), 4000);
}

// 🎤 Ecualizador con el micrófono (opcional): si no hay permiso, siguen latiendo al BPM
let microActivo = false;
async function micro() {
  if (microActivo) { aviso("El ecualizador ya va con el micrófono"); return; }
  try {
    const flujo = await navigator.mediaDevices.getUserMedia({audio: true});
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const analizador = ctx.createAnalyser();
    analizador.fftSize = 64;
    ctx.createMediaStreamSource(flujo).connect(analizador);
    const datos = new Uint8Array(analizador.frequencyBinCount);
    microActivo = true;
    document.body.classList.add("micro");
    aviso("🎤 Ecualizador con el micrófono");
    const bandas = [1, 2, 3, 5, 7, 10, 14];
    (function mover() {
      analizador.getByteFrequencyData(datos);
      document.querySelectorAll(".eq").forEach(eq => eq.querySelectorAll("i").forEach((i, k) => {
        const v = pausado ? 0.15 : Math.max(0.12, datos[bandas[k]] / 255);
        i.style.transform = `scaleY(${v.toFixed(2)})`;
      }));
      requestAnimationFrame(mover);
    })();
  } catch (e) {
    aviso("No se pudo usar el micrófono: el ecualizador sigue al ritmo del tema");
  }
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
</script></body></html>
"""
