"""
La ficha «por el sonido» de cada canción, dentro del emparejado de siempre.

El Shazam propio (herramientas/ordenar_musica: huellas → grupos → fichas) deja data/fichas_sonido.csv:
por archivo (ruta dentro de TDJ\\MUSICA), la fila de tangodb que le corresponde y cómo se supo:
    sonido  = suena igual que un extracto de El Recodo (lo más seguro)
    tags    = todas las copias que suenan igual apuntaban a la misma ficha
(las «dudosas» y «sin ficha» no se usan).

emparejar.Cancion llama a aplicar(cancion) después de buscar por los tags: si el archivo tiene ficha por el
sonido, esa opción va PRIMERA y es la sugerida (o «perfecta» si el archivo ya la tiene). Así sale sola en
Mi biblioteca, al cargar una carpeta, una playlist… sin ningún botón aparte.
"""
import csv
import os
import re
import unicodedata

from src.config.config import DATA_FOLDER

FICHAS_CSV = os.path.join(DATA_FOLDER, "fichas_sonido.csv")
FUENTES_FIABLES = ("sonido", "tags")
NOMBRE_FUENTE = {"sonido": "🔊 Reconocida por el sonido (igual que el extracto de El Recodo).",
                 "tags": "🔊 Reconocida por el sonido: todas las copias que suenan igual dicen esta ficha."}
_cache = {"mtime": None, "fichas": {}}


def _texto(v):
    return "" if v is None or (isinstance(v, float) and v != v) else str(v)


def rel_de(ruta):
    """Ruta dentro de TDJ\\MUSICA, en minúsculas (igual en D:\\Dropbox y C:\\Dropbox), o None."""
    p = os.path.normcase(os.path.normpath(str(ruta)))
    i = p.find(os.sep + "tdj" + os.sep + "musica" + os.sep)
    return p[i + len(os.sep + "tdj" + os.sep + "musica" + os.sep):] if i >= 0 else None


def fichas():
    """{rel en minúsculas: info} (se relee solo si el archivo cambió)."""
    try:
        mtime = os.path.getmtime(FICHAS_CSV)
    except OSError:
        return {}
    if _cache["mtime"] != mtime:
        d = {}
        with open(FICHAS_CSV, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                if r["fuente"] in FUENTES_FIABLES and r["fila_bd"]:
                    d[os.path.normcase(r["rel"])] = dict(fila=int(r["fila_bd"]), fuente=r["fuente"],
                                                         copias=int(r["copias"]), maestra=int(r["maestra"]),
                                                         nota=r["nota"])
        _cache.update(mtime=mtime, fichas=d)
    return _cache["fichas"]


def ficha_de(ruta):
    rel = rel_de(ruta)
    return fichas().get(rel) if rel else None


def _n(s):
    s = unicodedata.normalize("NFKD", str(s).lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)))


def mejor_fila(db, fila):
    """
    El Recodo a veces pone al cantor como artista y al director como «Dir. X» en cantor
    («Ada Falcón / Dir. Francisco Canaro»). Si la misma grabación (mismo título y fecha) está también como
    «Francisco Canaro / Ada Falcón», se usa esa, que es el formato «Orquesta / Cantor».
    """
    f = db.loc[fila]
    m = re.match(r"(?i)dir\.?\s*(.+)", _texto(f.get("cantor", "")).strip())
    if not m:
        return fila
    director, cantor = _n(m.group(1)), _n(f.get("artista", ""))
    mismas = db[(db["titulo_min"] == f["titulo_min"]) & (db["fecha"] == f["fecha"])]
    for i, otra in mismas.iterrows():
        if i != fila and _n(otra["artista"]) == director and cantor in _n(otra["cantor"]):
            return i
    return fila


def _sin_perder_tildes(fila_bd, tags):
    """Si la base de datos dice lo mismo pero con menos tildes o signos («Jorge Falcon»), se queda lo del
    archivo: el sonido decide QUÉ grabación es, no cómo se escribe peor."""
    from src.utils.formato_tags import tags_desde_coincidencia
    from src.utils.utils import separar_artistas
    especiales = lambda s: sum(not c.isascii() for c in s)
    nuevas = tags_desde_coincidencia(fila_bd)
    fila_bd = fila_bd.copy()
    titulo, artista = _texto(getattr(tags, "title", "")), _texto(getattr(tags, "artist", ""))
    if titulo and _n(titulo) == _n(nuevas["title"]) and especiales(titulo) > especiales(nuevas["title"]):
        fila_bd["titulo"] = titulo
    if artista and _n(artista) == _n(nuevas["artist"]) and especiales(artista) > especiales(nuevas["artist"]):
        fila_bd["artista"], fila_bd["cantor"] = separar_artistas(artista)
    return fila_bd


def aplicar(cancion):
    """Si la canción tiene ficha por el sonido: es la primera opción y la sugerida (o perfecta)."""
    info = ficha_de(cancion.ruta_archivo)
    if info is None:
        return
    db = cancion.db
    fila = mejor_fila(db, info["fila"]) if info["fila"] in db.index else None
    if fila is None:
        return
    import pandas as pd
    from src.motor.emparejar import cambios_de
    buena = _sin_perder_tildes(db.loc[fila], cancion.tags)
    otras = cancion.coincidencias
    otras = otras.drop(index=fila, errors="ignore") if otras is not None and not otras.empty else db.iloc[0:0]
    cancion.coincidencias = pd.concat([buena.to_frame().T, otras])
    cancion.por_sonido = info
    cancion.artist_not_found = cancion.title_not_found = False
    cancion.hay_coincidencia_preferida, cancion.coincidencia_preferida = True, 0
    cancion.seleccion = 0
    _, _, dif = cambios_de(cancion)
    cancion.perfect_match = not dif
    if cancion.perfect_match:
        cancion.coincidencias = cancion.coincidencias.iloc[:1]
    partes = [NOMBRE_FUENTE.get(info["fuente"], "🔊 Reconocida por el sonido.")]
    if info["copias"] > 1:
        partes.append(f"Hay {info['copias']} archivos con este mismo sonido"
                      + ("; este es la copia buena." if info["maestra"] else "; este NO es la copia buena."))
    cancion.explicacion = " ".join(partes)


def version():
    """Para version_reglas: si cambian las fichas, Mi biblioteca vuelve a emparejar."""
    try:
        st = os.stat(FICHAS_CSV)
        return f"sonido|{st.st_size}|{int(st.st_mtime)}"
    except OSError:
        return "sonido|-"
