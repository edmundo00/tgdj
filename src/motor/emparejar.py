"""
Motor de emparejado: dada una canción (ruta + tags), la busca en la base de datos y decide su estado.
No sabe nada de ventanas: lo usan la tabla de etiquetado y (más adelante) la biblioteca en segundo plano.

    motor = Motor()                                   # usa la base de datos cargada (Database)
    cancion = motor.emparejar(ruta)                   # o motor.emparejar(ruta, tags=[...])
    cancion.categoria   -> perfecta | preferida | dudosa | sin_titulo | sin_artista
    cancion.seleccion   -> posición de la opción sugerida (o None)
    cambios_de(cancion) -> (tags actuales, tags nuevas, solo lo que cambiaría)

Estados:
    perfecta     el archivo ya tiene la misma información (nunca se marca para cambiar)
    preferida    hay una opción clara: viene marcada ("sugerida")
    dudosa       varias opciones posibles: hay que elegir
    sin_titulo   el artista está en la BD pero el título no
    sin_artista  el artista no está en la BD
"""
import os
import re
from types import SimpleNamespace

import pandas as pd

from src.config.database import Database
from src.constants.enums import TagLabels
from src.utils.buscar_artista import indice_para
from src.utils.formato_tags import tags_desde_coincidencia, combinar_compositor, formatear_fecha
from src.utils.utils import (
    leer_tags, separar_artistas, buscar_titulo, compare_tags, coincidencias_a_colores, fecha_es_de_cd,
    crear_reemplazo_tags_linea,
)

CAMPOS = ("title", "artist", "year", "genre", "composer")
NOMBRE_CAMPO = {"title": "título", "artist": "artista", "year": "fecha", "genre": "género", "composer": "compositor"}
REVISADA = re.compile(r"^Musica: .+ - Letra: .+$")


def texto(valor):
    return "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor)


def ya_revisada(compositor):
    """Las canciones que ya pasaron por la BD tienen el compositor en el formato nuevo completo."""
    return bool(REVISADA.match(texto(compositor).strip()))


def tags_de_lista(lista):
    """[title, artist, year, genre, composer, ruta, (album)] -> objeto con atributos."""
    return SimpleNamespace(title=lista[0], artist=lista[1], year=lista[2], genre=lista[3], composer=lista[4],
                           _filename=lista[5], album=lista[6] if len(lista) > 6 else "")


def leer_tags_lista(ruta):
    """Tags del archivo como lista (formato que acepta Motor.emparejar), o None si no se pueden leer."""
    try:
        t = leer_tags(ruta)
        return [t.title, t.artist, t.year, t.genre, t.composer, ruta, getattr(t, "album", "")]
    except Exception:
        return None


def tags_actuales(cancion):
    return {k: texto(getattr(cancion.tags, k, "")) for k in CAMPOS}


def coincidencias(cancion):
    c = getattr(cancion, "coincidencias", None)
    return c if c is not None else pd.DataFrame()


def categoria_de(cancion):
    if getattr(cancion, "perfect_match", False):
        return "perfecta"
    if getattr(cancion, "artist_not_found", False):
        return "sin_artista"
    if getattr(cancion, "title_not_found", False):
        return "sin_titulo"
    if getattr(cancion, "hay_coincidencia_preferida", False):
        return "preferida"
    return "dudosa"


def cambios_de(cancion):
    """(tags actuales, tags nuevas, solo lo que cambia) si se aplica la opción marcada."""
    actuales = tags_actuales(cancion)
    c = coincidencias(cancion)
    if cancion.seleccion is None or c.empty:
        return actuales, {}, {}
    nuevas = tags_desde_coincidencia(c.iloc[cancion.seleccion])
    if actuales["composer"]:   # no perder lo que el archivo sabe y la base de datos no
        nuevas["composer"] = combinar_compositor(actuales["composer"], nuevas["composer"])
    # Solo se escriben los campos con valor nuevo y distinto
    return actuales, nuevas, {k: v for k, v in nuevas.items() if v and v != actuales[k]}


def contexto_disco(canciones):
    """
    Para las canciones en las que hay que elegir: las demás canciones del mismo disco (álbum, o
    carpeta si no hay álbum) ya identificadas dicen de qué años es el disco. Se marcan las opciones
    que caen en ese rango (± 1 año) en cancion.disco. No se elige nada.
    """
    def disco_de(a):
        album = texto(getattr(a.tags, "album", "")).strip()
        return ("album", album.lower()) if album else ("carpeta", os.path.dirname(a.ruta_archivo))

    anos_por_disco = {}
    for a in canciones:
        ano = None
        if a.categoria == "perfecta":
            ano = formatear_fecha(getattr(a.tags, "year", ""))[:4]
        elif a.categoria == "preferida" and a.seleccion is not None:
            ano = formatear_fecha(coincidencias(a).iloc[a.seleccion].get("fecha", ""))[:4]
        if ano and not getattr(a, "motivo_fecha", ""):
            anos_por_disco.setdefault(disco_de(a), []).append(int(ano))

    for a in canciones:
        a.disco = None
        anos = anos_por_disco.get(disco_de(a), [])
        if a.categoria != "dudosa" or len(anos) < 2:
            continue
        desde, hasta = min(anos), max(anos)
        encajan = set()
        for pos, (_, c) in enumerate(coincidencias(a).iterrows()):
            f = formatear_fecha(c.get("fecha", ""))[:4]
            if f and desde - 1 <= int(f) <= hasta + 1:
                encajan.add(pos)
        if encajan:
            tipo, _ = disco_de(a)
            donde = f"del álbum «{getattr(a.tags, 'album', '')}»" if tipo == "album" else "de la misma carpeta"
            rango = f"{desde}" if desde == hasta else f"{desde}–{hasta}"
            a.disco = {"encajan": encajan, "texto": f"las otras {len(anos)} canciones {donde} son de {rango}"}


def resumen(cancion):
    """Lo esencial del resultado, en tipos simples (para guardarlo en la biblioteca)."""
    c = coincidencias(cancion)
    _, _, dif = cambios_de(cancion)
    return {
        "categoria": cancion.categoria,
        "opciones": [int(i) for i in c.index] if not c.empty else [],
        "sugerida": int(c.index[cancion.seleccion]) if cancion.seleccion is not None and not c.empty else None,
        "motivo_fecha": getattr(cancion, "motivo_fecha", ""),
        "cambios": dif,
    }


class Cancion:
    """Resultado de emparejar un archivo con la base de datos (antes FILETOFINDQT)."""

    def __init__(self, ruta_archivo, tags, db, dic_art, usar_fecha=True):
        self.db, self.dic_art = db, dic_art
        self.show_date_checked = usar_fecha
        self.ruta_archivo = ruta_archivo
        self.artist_not_found = True
        self.title_not_found = True
        self.titulo_coincidencia = 0
        self.perfect_match = False
        self.motivo_fecha = ""
        self.tags = leer_tags(ruta_archivo) if tags is None else tags_de_lista(tags)
        self.artists1, self.artists2 = separar_artistas(self.tags.artist)
        self.buscar()
        self.categoria = categoria_de(self)
        self.estado_guardado = None
        c = coincidencias(self)
        # Solo se marca la sugerida; una perfecta ya está bien y nunca viene marcada para cambiar
        self.seleccion = self.coincidencia_preferida if not c.empty and self.categoria == "preferida" else None
        self.disco = None

    def get_coincidencia_favorita(self):
        if not self.hay_coincidencia_preferida:
            return None
        return crear_reemplazo_tags_linea(
            ruta_archivo=self.ruta_archivo, tags=self.tags, coincidencias=self.coincidencias,
            coincidencia_preferida=self.coincidencia_preferida, artists1=self.artists1, artists2=self.artists2,
            coincidencia_titulo=self.titulo_coincidencia)

    def buscar(self):
        self.hay_coincidencia_preferida = False
        self.coincidencia_preferida = 0

        # Artista (sin artista en la tag no se puede buscar: "" coincidiría con cualquiera)
        artista_original, _ = separar_artistas(self.tags.artist)
        if artista_original.strip():
            artista_key, self.artista_coincidencia = indice_para(self.dic_art).buscar(artista_original)
        else:
            artista_key, self.artista_coincidencia = None, 0
        if not artista_key:
            self.coincidencias = self.db.iloc[0:0]
            self.artist_not_found = True
            return
        self.artist_not_found = False

        # Título entre las canciones de ese artista (o artistas)
        canciones = (self.dic_art[artista_key] if isinstance(artista_key, str)
                     else pd.concat([self.dic_art[k] for k in artista_key if k in self.dic_art]))
        self.titulo_coincidencia, candidatas = buscar_titulo(canciones, self.tags)

        # La misma grabación repetida (El Recodo y tango.info) se muestra una sola vez: la más completa
        if len(candidatas) > 1:
            from src.utils.correcciones import claves
            completa = ((candidatas["compositor_autor"].astype(str) != "").astype(int)
                        + (candidatas["fecha"].astype(str).str.len() == 10).astype(int)
                        + (candidatas.get("audio30", "").astype(str) != "").astype(int))
            candidatas = (candidatas.assign(_clave=claves(candidatas), _completa=completa)
                          .sort_values("_completa", ascending=False, kind="stable")
                          .drop_duplicates("_clave").drop(columns=["_clave", "_completa"]))
        # Opciones en orden cronológico (las sin fecha al final)
        if not candidatas.empty:
            orden = candidatas["fecha"].astype(str).replace("", "9999")
            candidatas = candidatas.loc[orden.sort_values(kind="stable").index]
            # Fecha del archivo que en realidad es la del CD: no sirve para elegir
            self.motivo_fecha = fecha_es_de_cd(self.tags.year, list(candidatas["artista"]), list(candidatas["fecha"]))

        if self.titulo_coincidencia == 0:
            self.coincidencias = self.db.iloc[0:0]
            self.title_not_found = True
            return
        self.title_not_found = False

        # Comparar campo a campo con cada opción
        self.bool_coincidencias, self.perfect_match, indice_perfecta = compare_tags(
            self.artista_coincidencia, self.titulo_coincidencia, candidatas, self.tags)
        if self.perfect_match:
            candidatas = candidatas.loc[[indice_perfecta]]
        else:
            self.hay_coincidencia_preferida, self.coincidencia_preferida = elegir_preferida(
                self.bool_coincidencias, candidatas, self.show_date_checked)
        self.coincidencias = candidatas
        self.colores_labels = coincidencias_a_colores(self.bool_coincidencias, self.perfect_match)


class Motor:
    def __init__(self, db=None, dic_art=None, usar_fecha=True):
        datos = Database()
        self.db = db if db is not None else datos.get_db()
        self.dic_art = dic_art if dic_art is not None else datos.get_dic_art()
        self.usar_fecha = usar_fecha

    def emparejar(self, ruta, tags=None):
        """tags: lista [title, artist, year, genre, composer, ruta, album] o None para leerlas del archivo."""
        return Cancion(ruta, tags, self.db, self.dic_art, self.usar_fecha)


# Puntos por campo según el tipo de coincidencia (verde 3, amarillo 2, naranja 1, rojo 0)
_GRUPOS_PUNTOS = {
    "orquesta": (TagLabels.ORQUESTA_EXACTA, TagLabels.ORQUESTA, TagLabels.ORQUESTA_PARCIAL),
    "titulo": (TagLabels.TITULO_EXACTO, TagLabels.TITULO, TagLabels.TITULO_PARCIAL),
    "cantor": (TagLabels.CANTOR_EXACTO, TagLabels.CANTOR, TagLabels.CANTOR_PARCIAL),
    "fecha": (TagLabels.FECHA_EXACTA, TagLabels.FECHA, TagLabels.FECHA_PARCIAL),
    "estilo": (TagLabels.ESTILO_EXACTO, TagLabels.ESTILO, TagLabels.ESTILO_PARCIAL),
    "compositor": (TagLabels.COMPOSITOR_AUTOR_EXACTO, TagLabels.COMPOSITOR_AUTOR, TagLabels.COMPOSITOR_AUTOR_PARCIAL),
}


def elegir_preferida(booleanos, candidatas, usar_fecha=True):
    """
    Elige la coincidencia a sugerir. Solo valen las filas con título y orquesta que coinciden,
    cantor no contradictorio y (si usar_fecha) año no contradictorio. Entre ellas gana la de más
    puntos; si varias empatan pero escribirían las mismas tags (duplicados de la BD), vale la primera.
    Devuelve (hay_preferida, posición).
    """
    get = lambda etiqueta, i: bool(booleanos[etiqueta].iloc[i])
    validas = []
    for i in range(len(candidatas)):
        titulo_ok = get(TagLabels.TITULO_EXACTO, i) or get(TagLabels.TITULO, i)
        # Título parecido solo en parte: vale si cantor y año confirman que es esa grabación
        confirmada = ((get(TagLabels.CANTOR_EXACTO, i) or get(TagLabels.CANTOR, i))
                      and (get(TagLabels.FECHA_EXACTA, i) or get(TagLabels.FECHA, i)))
        if not (titulo_ok or (get(TagLabels.TITULO_PARCIAL, i) and confirmada)):
            continue
        if not (get(TagLabels.ORQUESTA_EXACTA, i) or get(TagLabels.ORQUESTA, i)):
            continue
        if get(TagLabels.CANTOR_NEGATIVO, i):
            continue
        if usar_fecha and get(TagLabels.FECHA_NEGATIVA, i):
            continue
        puntos = sum(3 * get(e, i) + 2 * get(n, i) + get(p, i) for e, n, p in _GRUPOS_PUNTOS.values())
        validas.append((puntos, i))
    if not validas:
        return False, 0
    maximo = max(p for p, _ in validas)
    mejores = [i for p, i in validas if p == maximo]
    tags = {tuple(sorted(tags_desde_coincidencia(candidatas.iloc[i]).items())) for i in mejores}
    if len(mejores) == 1 or len(tags) == 1:
        return True, mejores[0]
    return False, 0


# Súbelo cuando cambie la lógica del motor: obliga a re-emparejar toda la biblioteca
VERSION_MOTOR = "2026-10-03.1"


def version_reglas(usar_fecha=True):
    """
    Huella de todo lo que influye en el resultado del emparejado: la base de datos de tango, tus
    grafías y correcciones, la opción de usar la fecha y la versión del motor. Si cambia, las
    canciones guardadas en la biblioteca se vuelven a emparejar.
    """
    import hashlib
    from src.config.config import DB_CSV_PATH
    from src.utils import correcciones, grafias
    h = hashlib.sha1(f"{VERSION_MOTOR}|fecha={bool(usar_fecha)}".encode())
    for ruta in (DB_CSV_PATH, grafias.ARCHIVO, correcciones.ARCHIVO):
        if os.path.exists(ruta):
            st = os.stat(ruta)
            h.update(f"{os.path.basename(ruta)}|{st.st_size}|{int(st.st_mtime)}".encode())
    return h.hexdigest()[:16]
