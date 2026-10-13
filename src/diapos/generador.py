"""
Generación de la presentación de las tandas (sin interfaz).

    canciones = leer_playlist(ruta_m3u)          # DataFrame, una fila por canción
    tandas = agrupar_tandas(canciones)           # lista de Tanda
    crear_presentacion(tandas, datos, destino)   # .pptx

Una tanda son canciones seguidas del mismo género. Lo que no es tango/vals/milonga
(normalmente una cortina) genera una diapo de cortina.
"""
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR
from pptx.util import Cm, Pt
from tinytag import TinyTag
from unidecode import unidecode

from src.config.config import (
    dropbox_path, image_folder, background_image_folder, background_tango_degradado, DEFAULT_FONT_NAME,
)
from src.utils.buscar_artista import separar_orquesta_cantor
from src.utils.formato_tags import separar_compositor_autor, formatear_fecha
from src.utils.musicbee_playlist import leer_mbp
from src.utils.funciones_para_diapos import add_text_to_slide, add_resized_image_to_slide, transformar_posiciones
from src.utils.utils import obtener_autores, convertir_segundos, load_m3u_file_helper

FIRMA_DJ = "Edmundo Fraga"

# Nombres que no llevan "Orquesta de" delante
SIN_PREFIJO = ["Orquesta", "Quinteto", "Sexteto", "Cuarteto", "Trío", "Trio", "Hugo Diaz", "Hugo Díaz", "Nelly Omar"]

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


@dataclass
class Tanda:
    genero: str
    canciones: pd.DataFrame
    orquesta: str = ""                 # "" si hay varias orquestas
    titulo_orquesta: str = ""
    subtitulo: str = ""
    misma_orquesta: bool = True
    es_cortina: bool = False
    es_cumparsita: bool = False        # La Cumparsita sola al final: el último baile, no es una tanda
    duracion: float = 0.0
    avisos: list = field(default_factory=list)


def compositor_para_diapo(compositor):
    """'Musica: X - Letra: ?' -> 'Musica: X'. Si no se sabe nada -> ''."""
    musica, letra = separar_compositor_autor(compositor)
    partes = []
    if musica:
        partes.append(f"Musica: {musica}")
    if letra:
        partes.append(f"Letra: {letra}")
    return " - ".join(partes)


def resolver_ruta(linea):
    """Rutas de playlists hechas en otro ordenador: rehacer con el Dropbox de este."""
    if os.path.exists(linea) or "Dropbox" not in linea:
        return linea
    alternativa = os.path.join(dropbox_path, linea.split("Dropbox", 1)[1].lstrip("\\/"))
    return alternativa if os.path.exists(alternativa) else linea


def leer_playlist(ruta_m3u):
    """Playlist .m3u/.m3u8 o de MusicBee (.mbp) -> (DataFrame de canciones, lista de rutas que no existen)."""
    filas, faltan = [], []
    lineas = leer_mbp(ruta_m3u) if ruta_m3u.lower().endswith(".mbp") else load_m3u_file_helper(ruta_m3u)
    for linea in lineas:
        ruta = resolver_ruta(linea)
        if not os.path.exists(ruta):
            faltan.append(linea)
            continue
        try:
            t = TinyTag.get(ruta)
        except Exception:
            faltan.append(linea)
            continue
        orquesta, cantor = separar_orquesta_cantor(t.artist or "")
        fecha = formatear_fecha(t.year)
        filas.append({
            "ruta": ruta, "title": t.title or os.path.splitext(os.path.basename(ruta))[0],
            "artist": t.artist or "", "artist1": orquesta, "artist2": cantor,
            "year": t.year or "", "ano": fecha[:4], "genre": (t.genre or "").strip().lower(),
            "composer": t.composer or "", "duration": float(t.duration or 0), "bitrate": float(t.bitrate or 0),
        })
    return pd.DataFrame(filas), faltan


def es_tanda(genero):
    return any(g in genero for g in ("tango", "vals", "milonga"))


def subtitulo_genero(genero, autores):
    """'Vals con Héctor Mauré', 'Milonga instrumental', 'Con Alberto Echagüe'..."""
    if "vals" in genero:
        base = "Vals "
    elif "milonga" in genero:
        base = "Milonga "
    elif genero == "tango":
        return "Instrumental" if autores == "instrumental" else f"Con {autores}"
    else:
        return ""
    return base + ("instrumental" if autores == "instrumental" else f"con {autores}")


def intervalo_anos(anos):
    validos = sorted(int(a) for a in anos if str(a).isdigit())
    if not validos:
        return ""
    return f"({validos[0]})" if validos[0] == validos[-1] else f"({validos[0]} - {validos[-1]})"


def es_cumparsita(titulo):
    t = unidecode(str(titulo or "")).lower().strip()
    return t.startswith("la cumparsita") or t.startswith("cumparsita")


def agrupar_tandas(canciones):
    if canciones.empty:
        return []
    grupo = canciones["genre"].ne(canciones["genre"].shift()).cumsum()
    grupos = [df.reset_index(drop=True) for _, df in canciones.groupby(grupo, sort=False)]
    # La Cumparsita al final va sola aunque no lleve cortina delante: no es parte de la última tanda
    ultimo = grupos[-1]
    if len(ultimo) > 1 and es_tanda(ultimo["genre"].iloc[0]) and es_cumparsita(ultimo["title"].iloc[-1]):
        grupos[-1:] = [ultimo.iloc[:-1].reset_index(drop=True), ultimo.iloc[-1:].reset_index(drop=True)]
    tandas = []
    for df in grupos:
        genero = df["genre"].iloc[0]
        orquestas = df["artist1"].unique()
        t = Tanda(genero=genero, canciones=df, misma_orquesta=len(orquestas) == 1,
                  es_cortina=not es_tanda(genero), duracion=float(df["duration"].sum()))
        t.orquesta = orquestas[0] if t.misma_orquesta else ""
        if t.es_cortina:
            t.titulo_orquesta = t.orquesta or "Cortina"
        else:
            if not t.misma_orquesta:
                t.avisos.append("Mezcla orquestas: " + ", ".join(orquestas))
            nombre = t.orquesta or " / ".join(orquestas)
            t.titulo_orquesta = nombre if any(nombre.startswith(p) for p in SIN_PREFIJO) else f"Orquesta de {nombre}"
            autores = obtener_autores([[c] for c in df["artist2"] if c])
            t.subtitulo = f"{subtitulo_genero(genero, autores)} {intervalo_anos(df['ano'])}".strip()
            if not genero:
                t.avisos.append("Sin género")
        tandas.append(t)
    final = tandas[-1]
    if not final.es_cortina and len(final.canciones) == 1 and es_cumparsita(final.canciones["title"].iloc[0]):
        final.es_cumparsita = True
    return tandas


def duracion_texto(inicio, fin):
    try:
        h1, h2 = datetime.strptime(inicio, "%H:%M"), datetime.strptime(fin, "%H:%M")
    except ValueError:
        return "formato inválido"
    if h2 <= h1:
        h2 += timedelta(days=1)
    horas, resto = divmod((h2 - h1).seconds, 3600)
    return f"{horas} horas y {resto // 60} minutos"


def fecha_larga(fecha):
    """date -> '30 de marzo de 2025'."""
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def nombre_archivo(datos):
    return f"{datos['fecha']:%y%m%d} {datos['milonga']}.pptx"


# ---------------------------------------------------------------------------- PowerPoint
POSICIONES_PORTADA = {
    "Milonga": {"left": Cm(1), "top": Cm(0), "right": Cm(1), "height": Cm(3)},
    "Fecha_Milonga": {"left": Cm(1.75), "top": Cm(2.5), "right": Cm(1), "height": Cm(2)},
    "Duracion_Milonga": {"left": Cm(1), "top": Cm(17.25), "right": Cm(1), "height": Cm(2)},
    "firma": {"left": Cm(1), "top": Cm(15.5), "right": Cm(24), "height": Cm(2.8)},
    "linea_divisoria": {"left": Cm(13.5), "top": Cm(4.5), "right": Cm(1), "height": Cm(0)},
    "tandas_start": {"left": Cm(3), "top": Cm(3.75), "right": Cm(1), "height": Cm(15)},
    "tandas_spacing": Cm(0.575),
    "offset_shadow": Cm(0.06),
    "maxima_anchura_image": 1,
    "fuentes": {
        "Milonga": {"tamaño": 60, "tipo_fuente": "Arial"},
        "Fecha_Milonga": {"tamaño": 20, "tipo_fuente": "Arial"},
        "Duracion_Milonga": {"tamaño": 16, "tipo_fuente": "Arial"},
        "tandas": {"tamaño": 12, "tipo_fuente": "Bernard MT Condensed"},
        "duracion_estimada": {"tamaño": 16, "tipo_fuente": "Arial"},
        "firma": {"tamaño": 20, "tipo_fuente": "Arial"},
    },
}

POSICIONES_TANDA = {
    "cortina_title": {"left": Cm(5), "top": Cm(5), "right": Cm(1), "height": Cm(5)},
    "cortina_subtitle": {"left": Cm(8), "top": Cm(10), "right": Cm(1), "height": Cm(5)},
    "tanda_orquesta_shadow": {"left": Cm(1.6), "top": Cm(0), "right": Cm(1), "height": Cm(3)},
    "tanda_cantor_shadow": {"left": Cm(3), "top": Cm(2.3), "right": Cm(1), "height": Cm(2)},
    "firma_tgdj_box": {"left": Cm(1), "top": Cm(15.5), "right": Cm(24), "height": Cm(2.8)},
    "linea_divisoria": {"left": Cm(13.5), "top": Cm(4.5), "right": Cm(1), "height": Cm(0)},
    "canciones_start": {"left": Cm(13.5), "top": Cm(4.5), "right": Cm(1), "height": Cm(3)},
    "canciones_spacing": Cm(3.5),
    "offset_shadow": Cm(0.05),
    "maxima_anchura_image": 1,
    "fuentes": {
        "cortina_titulo": {"tamaño": 100, "tipo_fuente": DEFAULT_FONT_NAME},
        "cortina_artista": {"tamaño": 50, "tipo_fuente": DEFAULT_FONT_NAME},
        "orquesta": {"tamaño": 55, "tipo_fuente": DEFAULT_FONT_NAME},
        "estilo": {"tamaño": 35, "tipo_fuente": DEFAULT_FONT_NAME},
        "canciones": {"tamaño": 50, "tipo_fuente": 'Bernard MT Condensed'},
        "anos": {"tamaño": 20, "tipo_fuente": "Arial"},
        "autores": {"tamaño": 20, "tipo_fuente": 'Arial'},
        "firma": {"tamaño": 20, "tipo_fuente": DEFAULT_FONT_NAME},
    },
}

BLANCO = (255, 255, 255)


def imagen_orquesta(orquesta):
    ruta = os.path.join(image_folder, "orquestas", f"{unidecode(orquesta).lower()}.png")
    return ruta if os.path.exists(ruta) else None


# Nota: transformar_posiciones devuelve listas nuevas, así que los diccionarios de arriba no se modifican.
# No usar copy.deepcopy sobre ellos: las medidas de python-pptx copiadas así dan un .pptx que PowerPoint no abre.


def _portada(prs, calc, datos, tandas):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.add_picture(background_tango_degradado, 0, 0, width=prs.slide_width, height=prs.slide_height)
    pos = transformar_posiciones(prs, POSICIONES_PORTADA)
    f = POSICIONES_PORTADA["fuentes"]

    def texto(t, clave, fuente):
        add_text_to_slide(slide, calc, t, pos[clave], pos["offset_shadow"], f[fuente]["tamaño"],
                          f[fuente]["tipo_fuente"], BLANCO, False, True, adjust_size=True)

    reales = [t for t in tandas if not t.es_cortina]
    musica = sum(t.duracion for t in reales)
    estimada = musica + max(len(reales) - 1, 0) * 60
    fmt = "x minutos y x segundos"
    texto(datos["milonga"], "Milonga", "Milonga")
    texto(f"{fecha_larga(datos['fecha'])} de {datos['inicio']} a {datos['fin']} duracion: "
          f"{duracion_texto(datos['inicio'], datos['fin'])}", "Fecha_Milonga", "Fecha_Milonga")
    texto(f"Duración total sin cortinas: {convertir_segundos(musica, fmt)}, "
          f"Duración total estimada: {convertir_segundos(estimada, fmt)}", "Duracion_Milonga", "Duracion_Milonga")
    for n, t in enumerate(reales, 1):
        texto(f"{n} - {t.titulo_orquesta} {t.subtitulo}, {len(t.canciones)} temas con una duración de "
              f"{convertir_segundos(t.duracion, fmt)}", "tandas_start", "tandas")
        pos["tandas_start"][1] += pos["tandas_spacing"]


def _diapo_tanda(prs, calc, datos, tanda):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    # Notas "Artista - Título": las usa Control diapos para saber qué diapo mostrar
    slide.notes_slide.notes_text_frame.text = "\n".join(
        f"{a} - {t}" for a, t in zip(tanda.canciones["artist"], tanda.canciones["title"]))
    fondo = os.path.join(background_image_folder,
                         "background_cortina.png" if tanda.es_cortina else "background_tango_degradado.png")
    slide.shapes.add_picture(fondo, 0, 0, width=prs.slide_width, height=prs.slide_height)
    imagen = imagen_orquesta(tanda.orquesta)
    if imagen:
        add_resized_image_to_slide(slide, imagen, POSICIONES_TANDA["maxima_anchura_image"], prs)
    pos = transformar_posiciones(prs, POSICIONES_TANDA)
    f = POSICIONES_TANDA["fuentes"]
    sombra = pos["offset_shadow"]

    if tanda.es_cortina:
        primera = tanda.canciones.iloc[0]
        add_text_to_slide(slide, calc, tanda.orquesta, pos["cortina_title"], sombra * 2.5,
                          f["cortina_titulo"]["tamaño"], f["cortina_titulo"]["tipo_fuente"], BLANCO, True, True,
                          adjust_size=True)
        add_text_to_slide(slide, calc, f"{primera['title']}   ({primera['ano']})", pos["cortina_subtitle"],
                          sombra * 2.5, f["cortina_artista"]["tamaño"], f["cortina_artista"]["tipo_fuente"],
                          BLANCO, True, True, adjust_size=True)
        return

    add_text_to_slide(slide, calc, tanda.titulo_orquesta, pos["tanda_orquesta_shadow"], sombra * 2.5,
                      f["orquesta"]["tamaño"], f["orquesta"]["tipo_fuente"], BLANCO, True, True, adjust_size=True)
    add_text_to_slide(slide, calc, tanda.subtitulo, pos["tanda_cantor_shadow"], sombra,
                      f["estilo"]["tamaño"], f["estilo"]["tipo_fuente"], BLANCO, True, True, adjust_size=True)
    add_text_to_slide(slide, calc, f"© TDJ {FIRMA_DJ}\n{datos['milonga']}\n{fecha_larga(datos['fecha'])}",
                      pos["firma_tgdj_box"], sombra, f["firma"]["tamaño"], f["firma"]["tipo_fuente"], BLANCO,
                      False, True, adjust_size=True, border_color_rgb=(0, 0, 0), border_width_pt=2)
    x, y, ancho, alto = pos["linea_divisoria"]
    linea = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x, y, x + ancho, y + alto)
    linea.line.color.rgb = RGBColor(*BLANCO)
    linea.line.width = Pt(7)

    for _, c in tanda.canciones.iterrows():
        add_text_to_slide(
            slide, calc, c["title"], pos["canciones_start"], sombra, f["canciones"]["tamaño"],
            f["canciones"]["tipo_fuente"], BLANCO, False, True, adjust_size=True,
            extra_paragraph_text=compositor_para_diapo(c["composer"]),
            extra_run_text=f"   ({c['ano']})" if c["ano"] else "",
            extra_paragraph_settings={"font_name": f["autores"]["tipo_fuente"], "tamano_fuente": f["autores"]["tamaño"],
                                      "font_color_rgb": RGBColor(*BLANCO), "is_bold": False, "is_italic": True},
            extra_run_settings={"font_name": f["anos"]["tipo_fuente"], "tamano_fuente": f["anos"]["tamaño"],
                                "font_color_rgb": RGBColor(*BLANCO), "is_bold": False, "is_italic": False},
        )
        pos["canciones_start"][1] += pos["canciones_spacing"]


def crear_presentacion(tandas, datos, destino, progreso=None):
    """
    datos: {'milonga': str, 'fecha': date, 'inicio': 'HH:MM', 'fin': 'HH:MM'}
    progreso: función opcional progreso(hechas, total).
    """
    from src.utils.calcular_ancho_fuentes import FontWidthCalculator
    calc = FontWidthCalculator()
    calc.crear_base_de_datos()

    prs = Presentation()
    prs.slide_width, prs.slide_height = Cm(33.87), Cm(19.05)
    _portada(prs, calc, datos, tandas)
    for n, tanda in enumerate(tandas, 1):
        _diapo_tanda(prs, calc, datos, tanda)
        if progreso:
            progreso(n, len(tandas))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    prs.save(destino)
    return destino
