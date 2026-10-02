import re
import os
import pandas as pd
import pygame
import ftfy
import num2words as nw
from unidecode import unidecode
from pptx.util import Pt
from src.config.config import *
from src.constants.enums import TagLabels
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.easymp4 import EasyMP4
EasyMP4.RegisterTextKey('composer', '©wrt')
from mutagen.asf import ASF
from mutagen.aiff import AIFF
from mutagen.easyid3 import EasyID3
from mutagen.id3 import TIT2, TPE1, TDRC, TCON, TCOM, ID3NoHeaderError
from mutagen.wave import WAVE
from datetime import datetime
import difflib
from tinytag import TinyTag
from dateutil import parser


def convertir_segundos(segundos, formato='x\'x\'\''):
    """
    Convierte segundos con decimales a un formato de tiempo especificado.

    Args:
        segundos (float): Tiempo en segundos.
        formato (str): Formato de salida. Puede ser:
                       - "x'x''": Formato de minutos y segundos (ej. 2'6'').
                       - "x minutos y x segundos": Texto completo (ej. 2 minutos y 6 segundos).
                       - "x min x sec": Abreviado (ej. 2 min 6 sec).
                       - "h:m:s": Formato reloj (ej. 1:02:06).

    Returns:
        str: Tiempo formateado según el estilo especificado.
    """
    horas = int(segundos // 3600)  # División entera para obtener las horas
    minutos = int((segundos % 3600) // 60)  # Minutos restantes
    segundos_restantes = round(segundos % 60)  # Segundos restantes redondeados

    if formato == "x'x''":
        if horas > 0:
            return f"{horas}h {minutos}'{segundos_restantes}''"
        else:
            return f"{minutos}'{segundos_restantes}''"
    elif formato == "x minutos y x segundos":
        if horas > 0:
            return f"{horas} horas, {minutos} minutos y {segundos_restantes} segundos"
        else:
            return f"{minutos} minutos y {segundos_restantes} segundos"
    elif formato == "x min x sec":
        if horas > 0:
            return f"{horas} h {minutos} min {segundos_restantes} sec"
        else:
            return f"{minutos} min {segundos_restantes} sec"
    elif formato == "h:m:s":
        return f"{horas}:{minutos:02}:{segundos_restantes:02}"
    else:
        raise ValueError("Formato no reconocido. Usa uno de: 'x'x''', 'x minutos y x segundos', 'x min x sec', 'h:m:s'.")

# # Ejemplos de uso
# segundos_con_decimales = 3725.8  # 1 hora, 2 minutos y 5.8 segundos
#
# # Estilo x'x''
# print(convertir_segundos(segundos_con_decimales, "x'x''"))  # Salida: "1h 2'6''"
#
# # Estilo x minutos y x segundos
# print(convertir_segundos(segundos_con_decimales, "x minutos y x segundos"))  # Salida: "1 horas, 2 minutos y 6 segundos"
#
# # Estilo x min x sec
# print(convertir_segundos(segundos_con_decimales, "x min x sec"))  # Salida: "1 h 2 min 6 sec"
#
# # Estilo reloj h:m:s
# print(convertir_segundos(segundos_con_decimales, "h:m:s"))  # Salida: "1:02:06"


def separar_artistas(artistas):
    """'Orquesta / Cantor' -> ('Orquesta', 'Cantor'). Entiende también ; feat. canta: con."""
    from src.utils.buscar_artista import separar_orquesta_cantor
    if not isinstance(artistas, str):
        return "", ""
    return separar_orquesta_cantor(artistas)


def unir_artistas(orquesta, cantor, caracter_separacion):
    # Verificamos si cantor es NaN o si es una cadena vacía o de espacios
    if cantor and not (isinstance(cantor, float) and math.isnan(cantor)) and cantor.strip():
        artista = f'{orquesta}{caracter_separacion}{cantor.strip()}'
    else:
        artista = orquesta

    return artista


def coincidencias_a_colores(bool_coincidencias, perfect_match):
    # Definir colores para cada tipo de coincidencia
    colores = {
        'EXACTO': 'lightgreen',
        'COINCIDENCIA': 'yellow',
        'PARCIAL': 'orange',
        'NEGATIVO': 'red'
    }

    # Crear un DataFrame vacío basado en los índices de los Series en bool_coincidencias
    indices = next(iter(bool_coincidencias.values())).index
    df_colores = pd.DataFrame(index=indices)

    # Si hay un perfect match, asignar todos los colores a gris y retornar
    if perfect_match:
        df_colores = pd.DataFrame('grey', index=indices, columns=[
            'ORQUESTA', 'TITULO', 'CANTOR', 'FECHA', 'ESTILO', 'COMPOSITOR'
        ])
        return df_colores

    # Mapear los colores para cada categoría relevante
    mapping = {
        'ORQUESTA': [TagLabels.ORQUESTA_EXACTA, TagLabels.ORQUESTA, TagLabels.ORQUESTA_PARCIAL,
                     TagLabels.ORQUESTA_NEGATIVO],
        'TITULO': [TagLabels.TITULO_EXACTO, TagLabels.TITULO, TagLabels.TITULO_PARCIAL, TagLabels.TITULO_NEGATIVO],
        'CANTOR': [TagLabels.CANTOR_EXACTO, TagLabels.CANTOR, TagLabels.CANTOR_PARCIAL, TagLabels.CANTOR_NEGATIVO],
        'FECHA': [TagLabels.FECHA_EXACTA, TagLabels.FECHA, TagLabels.FECHA_PARCIAL, TagLabels.FECHA_NEGATIVA],
        'ESTILO': [TagLabels.ESTILO_EXACTO, TagLabels.ESTILO, TagLabels.ESTILO_PARCIAL, TagLabels.ESTILO_NEGATIVO],
        'COMPOSITOR': [TagLabels.COMPOSITOR_AUTOR_EXACTO, TagLabels.COMPOSITOR_AUTOR,
                       TagLabels.COMPOSITOR_AUTOR_PARCIAL, TagLabels.COMPOSITOR_AUTOR_NEGATIVO]
    }

    # Procesar cada grupo de coincidencias
    for categoria, etiquetas in mapping.items():
        exacta, normal, parcial, negativo = etiquetas

        # Inicializar con el color de "Ninguna Coincidencia"
        df_colores[categoria] = colores['NEGATIVO']  # Asignar por defecto

        # Aplicar colores basados en las coincidencias
        for i in indices:
            if bool_coincidencias[exacta][i]:
                df_colores.at[i, categoria] = colores['EXACTO']
            elif bool_coincidencias[normal][i]:
                df_colores.at[i, categoria] = colores['COINCIDENCIA']
            elif bool_coincidencias[parcial][i]:
                df_colores.at[i, categoria] = colores['PARCIAL']
            elif bool_coincidencias[negativo][i]:
                df_colores.at[i, categoria] = colores['NEGATIVO']

    return df_colores


def update_tags(file_path, title=None, artist=None, year=None, genre=None, composer=None):
    """
    Escribe las tags en el archivo. Los valores vacíos o None no se tocan.
    Soporta mp3, flac, m4a, wma, wav y aif/aiff. Devuelve True si se guardó bien.
    """
    return escribir_tags(file_path, dict(title=title, artist=artist, year=year, genre=genre, composer=composer))


def escribir_tags(file_path, valores, borrar_vacios=False):
    """
    valores: {'title'|'artist'|'year'|'genre'|'composer': texto}.
    Con borrar_vacios=True un valor "" borra esa tag (se usa para deshacer cambios).
    """
    valores = {('date' if k == 'year' else k): (str(v) if v else "") for k, v in valores.items() if v is not None}
    if not borrar_vacios:
        valores = {k: v for k, v in valores.items() if v}
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            try:
                audio = EasyID3(file_path)
            except ID3NoHeaderError:
                audio = MP3(file_path, ID3=EasyID3)
                audio.add_tags()
        elif ext == '.flac':
            audio = FLAC(file_path)
        elif ext in ('.m4a', '.mp4', '.aac'):
            audio = EasyMP4(file_path)
        elif ext in ('.wav', '.aif', '.aiff'):
            # WAV y AIFF guardan las tags en un bloque ID3 sin interfaz "Easy"
            audio = WAVE(file_path) if ext == '.wav' else AIFF(file_path)
            if audio.tags is None:
                audio.add_tags()
            frames = {'title': TIT2, 'artist': TPE1, 'date': TDRC, 'genre': TCON, 'composer': TCOM}
            for clave, valor in valores.items():
                nombre = frames[clave].__name__
                if valor:
                    audio.tags.setall(nombre, [frames[clave](encoding=3, text=valor)])
                else:
                    audio.tags.delall(nombre)
            audio.save()
            return True
        elif ext == '.wma':
            audio = ASF(file_path)
            asf_keys = {'title': 'Title', 'artist': 'Author', 'date': 'WM/Year',
                        'genre': 'WM/Genre', 'composer': 'WM/Composer'}
            valores = {asf_keys[k]: v for k, v in valores.items()}
        else:
            print(f"Formato no soportado: {file_path}")
            return False

        for clave, valor in valores.items():
            if valor:
                audio[clave] = valor
            elif clave in audio:
                del audio[clave]
        audio.save()
        return True

    except Exception as e:
        print(f"Error escribiendo tags en '{file_path}': {e}")
        return False


def crear_reemplazo_tags_linea(
    ruta_archivo, tags, coincidencias, coincidencia_preferida, artists1, artists2, coincidencia_titulo
):
    """
    Crea un diccionario de reemplazo de tags para una coincidencia preferida.

    :param ruta_archivo: Ruta del archivo.
    :param tags: Objeto con los tags actuales (title, artist, year, genre, composer).
    :param coincidencias: DataFrame con las coincidencias.
    :param coincidencia_preferida: Índice de la coincidencia preferida.
    :param artists1: Artista original.
    :param artists2: Cantor original.
    :return: Diccionario con los reemplazos de tags.
    """
    if coincidencia_preferida is not None:
        data = {
            'archivo': [ruta_archivo],
            'old_title': [tags.title],
            'new_title': [coincidencias.titulo.iloc[coincidencia_preferida]],
            'old_artist': [artists1],
            'new_artist': [coincidencias.artista.iloc[coincidencia_preferida]],
            'old_cantor': [artists2],
            'new_cantor': [coincidencias.cantor.iloc[coincidencia_preferida]],
            'old_year': [tags.year],
            'new_year': [coincidencias.fecha.iloc[coincidencia_preferida]],
            'old_genre': [tags.genre],
            'new_genre': [coincidencias.estilo.iloc[coincidencia_preferida]],
            'old_composer': [tags.composer],
            'new_composer': [coincidencias.compositor_autor.iloc[coincidencia_preferida]],
            'coincidencia_titulo': [coincidencia_titulo]
        }
        return pd.DataFrame(data)
    else:
        return pd.DataFrame()  # Return an empty DataFrame if no preferred match


def link_to_music(link):
    path = link.split('/', 3)[-1]
    local_path = os.path.join(mp3_dir, path)
    return local_path


def convert_numbers_to_words(text):
    # Find all numbers in the text
    numbers = re.findall(r'\d+', text)
    # Replace each number with its word form
    for number in numbers:
        text = text.replace(number, nw.num2words(number, lang='es'))

    return text


def contain_most_words(database, text, columna):
    # Normalize and preprocess the input text
    text = unidecode(convert_numbers_to_words(text)).lower().strip()
    text = text.replace("(", "").replace(")", "")
    text_words = set(word for word in text.lower().split() if word not in articulos_preposiciones_comunes)

    # Lists to store counts of common words
    lista_numero_palabras_comun = []

    for index, row in database.iterrows():
        # Normalize and preprocess the row text
        words = unidecode(str(row[columna]))
        words = words.replace("(", "").replace(")", "")
        words_words = set(words.lower().split())

        # Calculate the number of common words
        common_words = text_words.intersection(words_words)
        numero_de_palabras_en_comun = len(common_words)
        lista_numero_palabras_comun.append((index, numero_de_palabras_en_comun))

    # Find the maximum number of common words
    maximo_palabras = max(lista_numero_palabras_comun, key=lambda x: x[1])[1]

    # Create a boolean Series aligned with the DataFrame's index
    coincidencias = pd.Series(False, index=database.index)
    if maximo_palabras > 0:
        # Find indices with the maximum number of common words
        indices_mas_palabras = [index for index, value in lista_numero_palabras_comun if value == maximo_palabras]
        coincidencias.loc[indices_mas_palabras] = True

    return coincidencias

def get_file_name_without_extension(file_path):
    # Extract the file name with extension
    file_name_with_ext = os.path.basename(file_path)
    # Split the file name and extension, and return the file name
    file_name, _ = os.path.splitext(file_name_with_ext)
    return file_name


def buscar_titulo(database, tag):
    """
    Busca un título en una base de datos utilizando diversas estrategias de coincidencia, con optimizaciones de rendimiento.

    Proceso paso a paso:
    1. Normaliza y limpia el título original a buscar.
    2. Realiza coincidencias exactas y normalizadas:
       - Coincidencia exacta con el título original.
       - Coincidencia exacta con el título normalizado.
    3. Busca coincidencias parciales y patrones en los títulos:
       - Coincidencias al inicio de los títulos.
       - Coincidencias en cualquier parte de los títulos.
       - Coincidencias donde los títulos empiezan con el término buscado.
    4. Coincidencia basada en la mayor cantidad de palabras coincidentes.
    5. Devuelve el tipo de coincidencia y las entradas correspondientes.

    :param database: DataFrame que contiene los títulos donde buscar.
    :param tag: Objeto con el título a buscar y metadatos adicionales.
    :return: Tupla que contiene un indicador del tipo de coincidencia y un DataFrame con las entradas coincidentes.
    """

    # Normaliza y limpia el título original; si está vacío, usa el nombre del archivo sin extensión
    titulo_original = ftfy.fix_text(str(tag.title)).strip() if tag.title and isinstance(tag.title,
                                                                                        str) else get_file_name_without_extension(
        tag._filename)
    titulo_buscar_min = unidecode(convert_numbers_to_words(titulo_original)).lower().strip()

    # Verifica si el título es válido para la búsqueda
    if titulo_buscar_min == "":
        return 0, pd.DataFrame()  # No hay título válido para buscar

    # Coincidencias exactas

    # Paso 2.1: Coincidencia exacta del título original
    # Variable clave: coincidencias (boolean series que compara los títulos originales)
    coincidencias = database["titulo"] == titulo_original
    if coincidencias.any():
        return 6, database[coincidencias].copy()  # Retorna 6 si hay coincidencias exactas con el título original

    # Paso 2.2: Coincidencia exacta con el título normalizado
    # Variable clave: coincidencias (boolean series que compara los títulos normalizados)
    coincidencias = database["titulo_min"] == titulo_buscar_min
    if coincidencias.any():
        return 5, database[coincidencias].copy()  # Retorna 5 si hay coincidencias exactas con el título normalizado

    # Coincidencias parciales y patrones en los títulos

    # Paso 3.1: Coincidencias al inicio de los títulos
    # Variable clave: coincidencias (boolean series que verifica si los títulos comienzan con el término de búsqueda usando regex)
    coincidencias = database["titulo_min"].str.contains(f'^{titulo_buscar_min}', case=False, na=False, regex=False)
    if coincidencias.any():
        return 4, database[
            coincidencias].copy()  # Retorna 4 si el término de búsqueda coincide al inicio de algún título


    # Paso 3.3: Coincidencias donde los títulos empiezan con el término buscado
    # Variable clave: coincidencias (boolean series que verifica si los títulos comienzan exactamente con el término de búsqueda)
    coincidencias = database["titulo_min"].str.startswith(titulo_buscar_min, na=False)
    if coincidencias.any():
        # Encuentra la coincidencia más larga por la longitud del título
        indice_mejor_coincidencia = database.loc[coincidencias, "titulo_min"].str.len().idxmax()
        coincidencias = database.index == indice_mejor_coincidencia

        # Guarda información residual si está configurado
        if guardar_residuos:
            titulo_coincidencia = database.loc[coincidencias, 'titulo_min'].iloc[0]
            nuevos_residuos = [tag.title, titulo_coincidencia, tag.title[len(titulo_coincidencia):], tag._filename]
            residuos.append(nuevos_residuos)

        return 3, database[
            coincidencias].copy()  # Retorna 2 si encuentra el título más largo que empieza con el término de búsqueda

    # Paso 3.2: Coincidencias en cualquier parte de los títulos
    # Variable clave: coincidencias (boolean series que verifica si los títulos contienen el término de búsqueda en cualquier parte)
    coincidencias = database["titulo_min"].str.contains(titulo_buscar_min, case=False, na=False, regex=False)
    if coincidencias.any():
        return 2, database[
            coincidencias].copy()  # Retorna 3 si el término de búsqueda se encuentra en cualquier parte del título


    # Coincidencia basada en palabras

    # Paso 4.1: Coincidencia basada en la mayor cantidad de palabras coincidentes
    # Variable clave: coincidencias (series booleana generada por la función personalizada `contain_most_words`)
    coincidencias = pd.Series(contain_most_words(database, titulo_buscar_min, "titulo_min"), index=database.index)
    if coincidencias.any():
        return 1, database[
            coincidencias].copy()  # Retorna 1 si hay coincidencias basadas en la mayor cantidad de palabras coincidentes

    # Si no se encontraron coincidencias
    return 0, pd.DataFrame()  # Retorna 0 si no se encontraron coincidencias


def compare_tags(artista_coincidencia, titulo_coincidencia, database, tag):
    """
    Compara las tags del archivo con cada fila candidata de la base de datos.
    Todo se compara ya formateado (formato_tags), así 'Tango' == 'tango' y
    '12/03/1941' == '1941-03-12'. Para cada campo solo una etiqueta queda en True:
    EXACTO (verde), normal (amarillo, parecido), PARCIAL (naranja) o NEGATIVO (rojo).
    """
    from src.utils.formato_tags import (formatear_artista, formatear_cantores, formatear_fecha,
                                        formatear_estilo, normalizar_compositor_autor,
                                        separar_compositor_autor, formatear_titulo)
    from src.utils.buscar_artista import separar_orquesta_cantor, normalizar_nombre

    idx = database.index
    serie = lambda valores: pd.Series(list(valores), index=idx, dtype=bool)
    constante = lambda valor: pd.Series([valor] * len(idx), index=idx, dtype=bool)
    columna = lambda nombre: database[nombre].astype(str) if nombre in database else pd.Series([""] * len(idx), index=idx)
    simple = lambda t: unidecode(str(t or "")).lower().strip()

    for campo in ("year", "genre", "composer", "title"):
        setattr(tag, campo, getattr(tag, campo, None) or "")
    orquesta_tag, cantor_tag = separar_orquesta_cantor(tag.artist)
    c = {}

    # Orquesta: el nivel lo da la búsqueda del artista
    c[TagLabels.ORQUESTA_EXACTA] = serie(normalizar_nombre(o) == normalizar_nombre(orquesta_tag)
                                         and artista_coincidencia >= 2 for o in columna("artista"))
    c[TagLabels.ORQUESTA] = constante(artista_coincidencia >= 2)
    c[TagLabels.ORQUESTA_PARCIAL] = constante(artista_coincidencia == 1)
    c[TagLabels.ORQUESTA_NEGATIVO] = constante(True)

    # Título: el nivel lo da buscar_titulo
    c[TagLabels.TITULO_EXACTO] = serie(titulo_coincidencia == 6 or formatear_titulo(t) == formatear_titulo(tag.title)
                                       for t in columna("titulo"))
    c[TagLabels.TITULO] = constante(titulo_coincidencia in [2, 3, 4, 5])
    c[TagLabels.TITULO_PARCIAL] = constante(titulo_coincidencia == 1)
    c[TagLabels.TITULO_NEGATIVO] = constante(True)

    # Cantor
    cantor_f = formatear_cantores(cantor_tag)
    cantores_bd = [formatear_cantores(x) for x in columna("cantor")]
    c[TagLabels.CANTOR_EXACTO] = serie(x == cantor_f for x in cantores_bd)
    c[TagLabels.CANTOR] = serie(bool(x and cantor_f) and (simple(cantor_f) in simple(x) or simple(x) in simple(cantor_f))
                                for x in cantores_bd)
    c[TagLabels.CANTOR_PARCIAL] = constante(not cantor_f)   # el archivo no dice cantor
    c[TagLabels.CANTOR_NEGATIVO] = constante(True)

    # Fecha
    fecha_f = formatear_fecha(tag.year)
    ano_tag = fecha_f[:4]
    try:
        muerte = fallecimiento[simple(orquesta_tag)]
    except KeyError:
        muerte = None
    fecha_imposible = bool(muerte and parse_year(fecha_f) and muerte < parse_year(fecha_f))
    fechas_bd = [formatear_fecha(x) for x in columna("fecha")]
    c[TagLabels.FECHA_EXACTA] = serie(bool(f) and f == fecha_f for f in fechas_bd)
    c[TagLabels.FECHA] = serie(bool(f and ano_tag) and f[:4] == ano_tag for f in fechas_bd)
    c[TagLabels.FECHA_PARCIAL] = serie(not ano_tag or not f or fecha_imposible for f in fechas_bd)
    c[TagLabels.FECHA_NEGATIVA] = constante(True)

    # Estilo: 'tango vals' y 'vals' son parecidos
    estilo_f = formatear_estilo(tag.genre)
    familia = lambda e: "vals" if "vals" in e else "milonga" if "milonga" in e else e
    estilos_bd = [formatear_estilo(x) for x in columna("estilo")]
    c[TagLabels.ESTILO_EXACTO] = serie(bool(e) and e == estilo_f for e in estilos_bd)
    c[TagLabels.ESTILO] = serie(bool(e and estilo_f) and familia(e) == familia(estilo_f) for e in estilos_bd)
    c[TagLabels.ESTILO_PARCIAL] = serie(not e or not estilo_f for e in estilos_bd)
    c[TagLabels.ESTILO_NEGATIVO] = constante(True)

    # Compositor: parecido si coincide la música o la letra; parcial si alguno no se sabe
    comp_f = normalizar_compositor_autor(tag.composer)
    musica_tag, letra_tag = separar_compositor_autor(comp_f)
    comps_bd = [normalizar_compositor_autor(x) for x in columna("compositor_autor")]
    desconocido = "Musica: ? - Letra: ?"

    def parecido(x):
        m, l = separar_compositor_autor(x)
        return bool((m and simple(m) == simple(musica_tag)) or (l and simple(l) == simple(letra_tag)))

    c[TagLabels.COMPOSITOR_AUTOR_EXACTO] = serie(x == comp_f and x != desconocido for x in comps_bd)
    c[TagLabels.COMPOSITOR_AUTOR] = serie(parecido(x) for x in comps_bd)
    c[TagLabels.COMPOSITOR_AUTOR_PARCIAL] = serie(x == desconocido or comp_f == desconocido for x in comps_bd)
    c[TagLabels.COMPOSITOR_AUTOR_NEGATIVO] = constante(True)

    # Solo una etiqueta en True por grupo (la mejor)
    grupos = [
        [TagLabels.ORQUESTA_EXACTA, TagLabels.ORQUESTA, TagLabels.ORQUESTA_PARCIAL, TagLabels.ORQUESTA_NEGATIVO],
        [TagLabels.TITULO_EXACTO, TagLabels.TITULO, TagLabels.TITULO_PARCIAL, TagLabels.TITULO_NEGATIVO],
        [TagLabels.CANTOR_EXACTO, TagLabels.CANTOR, TagLabels.CANTOR_PARCIAL, TagLabels.CANTOR_NEGATIVO],
        [TagLabels.FECHA_EXACTA, TagLabels.FECHA, TagLabels.FECHA_PARCIAL, TagLabels.FECHA_NEGATIVA],
        [TagLabels.ESTILO_EXACTO, TagLabels.ESTILO, TagLabels.ESTILO_PARCIAL, TagLabels.ESTILO_NEGATIVO],
        [TagLabels.COMPOSITOR_AUTOR_EXACTO, TagLabels.COMPOSITOR_AUTOR, TagLabels.COMPOSITOR_AUTOR_PARCIAL,
         TagLabels.COMPOSITOR_AUTOR_NEGATIVO],
    ]
    for exacto, normal, parcial, negativo in grupos:
        c[normal] = c[normal] & ~c[exacto]
        c[parcial] = c[parcial] & ~(c[exacto] | c[normal])
        c[negativo] = c[negativo] & ~(c[exacto] | c[normal] | c[parcial])

    # Perfecta = el archivo ya tiene la misma información, en nuestro formato.
    # No cuentan como cambio: el género en otras mayúsculas ('Tango') ni el compositor en el formato
    # antiguo equivalente ('Musica: X' frente a 'Musica: X - Letra: ?').
    # Sí cuentan: otra fecha o fecha en otro formato, el artista con otro separador, compositor vacío.
    compositor_actual = str(tag.composer or "").strip()
    actual = {"title": formatear_titulo(tag.title), "artist": str(tag.artist or "").strip(),
              "year": str(tag.year or "").strip(), "genre": estilo_f,
              "composer": normalizar_compositor_autor(compositor_actual) if compositor_actual else ""}

    def sin_cambios(fila):
        from src.utils.formato_tags import tags_desde_coincidencia, combinar_compositor
        nuevas = tags_desde_coincidencia(fila)
        if compositor_actual:
            nuevas["composer"] = combinar_compositor(compositor_actual, nuevas["composer"])
        return all(not v or v == actual[k] for k, v in nuevas.items())

    c[TagLabels.TODO] = serie(sin_cambios(fila) for _, fila in database.iterrows())
    perfect_match = bool(c[TagLabels.TODO].any())
    perfect_match_index = c[TagLabels.TODO].idxmax() if perfect_match else None
    return c, perfect_match, perfect_match_index


def stop_music():
    pygame.mixer.music.stop()


def obtener_autores(lista):
    # Convertimos la lista en un conjunto para eliminar duplicados
    autores = set()

    for sublista in lista:
        for item in sublista:
            if isinstance(item, str) and item != 'nan':
                # Dividimos el string por ' y ' y ', ' para manejar los casos de varios autores
                partes = item.split(' y ')
                for parte in partes:
                    sub_partes = parte.split(', ')
                    for sub_parte in sub_partes:
                        autores.add(sub_parte.strip())

    # Si no hay autores, devolvemos 'instrumental'
    if not autores:
        return 'instrumental'

    # Convertimos el conjunto a lista para ordenarlos de manera consistente
    autores = list(autores)

    # Ordenamos para mantener consistencia
    autores.sort()

    # Según la cantidad de autores, retornamos la cadena deseada
    if len(autores) == 1:
        return autores[0]
    elif len(autores) == 2:
        return ' y '.join(autores)
    else:
        return ', '.join(autores[:-1]) + ' y ' + autores[-1]

def get_largest_paragraph(text):
    """
    Separates the input text into paragraphs based on newline characters and returns the largest paragraph.

    Parameters:
        text (str): The input string containing paragraphs separated by newline characters.

    Returns:
        str: The largest paragraph based on the length of characters.
    """
    # Split the text into paragraphs using newline as the separator
    paragraphs = text.split('\n')

    # Remove empty paragraphs (in case of multiple consecutive newline characters)
    paragraphs = [para.strip() for para in paragraphs if para.strip()]

    # Find the largest paragraph based on length
    largest_paragraph = max(paragraphs, key=len) if paragraphs else ""

    return largest_paragraph


def guardar_archivo_output(tipo, dataframe, encabezados=None):
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    filename = f'{tipo}_{timestamp}.csv'
    file_path = os.path.join(output_folder, filename)

    # Open the file to write data
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        # If custom headers are provided, write them manually
        if encabezados is not None:
            file.write(encabezados + '\n')  # Write the custom header line with the origin
            # Write the DataFrame without the default headers since they are custom
            dataframe.to_csv(file, index=False, sep=';', header=True)
        else:
            # Write the DataFrame with its own headers
            dataframe.to_csv(file, index=False, sep=';', header=True)

    print(f'{tipo.capitalize()} guardados en: {file_path}')

    return file_path


def leer_tags(ruta_archivo):
    tags = TinyTag.get(ruta_archivo)
    return tags


from datetime import datetime

def parse_year(tag_year):
    # Definir los formatos de fecha que se van a intentar
    formatos_fecha = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y", "%Y%m%d"]

    # Si el valor es un entero, lo tratamos como un año
    if isinstance(tag_year, int):
        return datetime(tag_year, 1, 1).date()

    # Si es una cadena, intentamos convertirla a una fecha usando múltiples formatos
    elif isinstance(tag_year, str):
        tag_year = tag_year.strip()  # Limpiamos espacios

        # Intentamos cada formato de fecha
        for formato in formatos_fecha:
            try:
                parsed_date = datetime.strptime(tag_year, formato).date()
                return parsed_date
            except ValueError:
                # Si falla, seguimos intentando con otros formatos
                continue

    # Si no se pudo convertir a fecha válida, retornamos None
    return None


def extract_year(date_str):
    # Define a regular expression pattern to match the year
    pattern = r'\b(\d{4})\b'

    # Match the pattern
    match = re.search(pattern, date_str)

    # If there's a match, return the year
    if match:
        return match.group(1)
    else:
        return ""


def load_m3u_file_helper(m3u_file_path):
    """Helper function to load M3U file with proper encoding handling."""
    try:
        # Try to load the file with UTF-8 encoding
        with open(m3u_file_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file if line.strip() and not line.startswith("#")]
    except UnicodeDecodeError:
        # Fallback to the system's default encoding if UTF-8 fails
        with open(m3u_file_path, 'r', encoding='cp1252', errors='ignore') as file:
            return [line.strip() for line in file if line.strip() and not line.startswith("#")]


