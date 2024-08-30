import re
import pandas as pd
import pygame
import ftfy
import num2words as nw
from unidecode import unidecode
from pptx.util import Pt, Cm
from src.config.config import *
from src.constants.enums import TagLabels
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

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
    artistas = ftfy.fix_text(convert_numbers_to_words(artistas))
    # Define regex pattern to capture different cases
    pattern = re.compile(r" / | feat\. | canta: ")
    
    # Split the input string using the defined pattern
    artists = re.split(pattern, artistas)
    
    # Assign artists based on the length of the split result
    artists1 = artists[0].strip()  # Main artist
    artists2 = artists[1].strip() if len(artists) > 1 else ""  # Second artist, if any
    
    return artists1, artists2


def palabras_mas_comunes(db, columna):
    dataframe = db.copy()
    # Paso 2: Eliminar puntuaciones y dividir en palabras
    dataframe[columna] = dataframe[columna].apply(lambda x: re.findall(r'\b\w+\b', x))
    # Paso 3: Contar la frecuencia de las palabras
    word_count = Counter()
    dataframe[columna].apply(lambda x: word_count.update(x))
    # Obtener las palabras más comunes
    most_common_words = word_count.most_common()


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


def convert_date_format(date_str):
    """
    Convert a date from DD/MM/YYYY format to YYYY-MM-DD format.
    Args:
        date_str (str): Date string in DD/MM/YYYY format.
    Returns:
        str: Date string in YYYY-MM-DD format.
    """
    pattern_yyyymmdd = r'^[0-9]{4}-(0[0-9]|1[0-2])-(0[0-9]|[12][0-9]|3[01])$'

    if re.match(pattern_yyyymmdd, date_str):
        if date_str.endswith('-00-00'):
            # Remove the last three characters
            return date_str[:-6]
        if date_str.endswith('-00'):
            # Remove the last three characters
            return date_str[:-3]
        new_date_str = date_str
    else:
        # Parse the input date string
        date_object = datetime.strptime(date_str, "%d/%m/%Y")

        # Convert to the desired format
        new_date_str = date_object.strftime("%Y-%m-%d")

    return new_date_str


def update_tags(file_path, title=None, artist=None, year=None, genre=None, composer=None):
    # Get the file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext == '.mp3':
        # Load the MP3 file
        audio = MP3(file_path, ID3=EasyID3)
    elif ext == '.flac':
        # Load the FLAC file
        audio = FLAC(file_path)
    elif ext == '.m4a':
        # Load the M4A file
        audio = MP4(file_path)
    else:
        print(f"Unsupported file format: {ext}")
        return

    # Update tags
    if title:
        if ext == '.m4a':
            audio['\xa9nam'] = title  # Tag for composer in M4A files
        else:
            audio['title'] = title
    if artist:
        if ext == '.m4a':
            audio['\xa9ART'] = artist  # Tag for composer in M4A files
        else:
            audio['artist'] = artist
    if year:
        if ext == '.m4a':
            audio['\xa9day'] = year  # Tag for composer in M4A files
        else:
            audio['date'] = year
    if genre:
        if ext == '.m4a':
            audio['\xa9gen'] = genre  # Tag for composer in M4A files
        else:
            audio['genre'] = genre
    if composer:
        if ext == '.m4a':
            audio['\xa9wrt'] = composer  # Tag for composer in M4A files
        else:
            audio['composer'] = composer

    # Save changes
    audio.save()


def capitalize_uppercase_words(text):
    words = text.split()
    transformed_words = []
    for word in words:

        if word == "DE" or word == "De":
            word = "de"
        if word == "DEL" or word == "Del":
            word = "del"
        if word == "DI" or word == "Di":
            word = "di"
        if word.isupper():
            word = word.capitalize()
            chars = list(word)
            for i in range(len(chars) - 1):
                # Check if the current character is a quote or hyphen
                if chars[i] in ["'", "-"]:
                    # Capitalize the next character
                    chars[i + 1] = chars[i + 1].upper()
            word = ''.join(chars)
            transformed_words.append(word)
        else:
            transformed_words.append(word)

    return ' '.join(transformed_words)


def extraer_cuatro_numeros(cadena):
    # Usamos la expresión regular \d{4} para encontrar cuatro dígitos consecutivos
    resultado = re.search(r'\d{4}', cadena)
    if resultado:
        return resultado.group()
    else:
        return None


def link_to_music(link):
    path = link.split('/', 3)[-1]
    local_path = os.path.join(mp3_dir, path)
    return local_path


def es_par(numero):
    """Devuelve True si el número es par, de lo contrario False."""
    return numero % 2 == 0


def convert_numbers_to_words(text):
    # Find all numbers in the text
    numbers = re.findall(r'\d+', text)
    # Replace each number with its word form
    for number in numbers:
        text = text.replace(number, nw.num2words(number, lang='es'))

    return text


def contain_most_words(database, text, columna):
    text = unidecode(convert_numbers_to_words(text)).lower().strip()
    text = text.replace("(", "").replace(")", "")
    text_words = set(text.lower().split())
    lista_numero_palabras_comun = []
    words_filas = []

    for index, row in database.iterrows():
        words = row[columna]
        words = words.replace("(", "").replace(")", "")
        words_words = set(words.lower().split())
        words_filas.append([index, words_words])
        common_words = text_words.intersection(words_words)
        numero_de_palabras_en_comun = len(common_words)
        lista_numero_palabras_comun.append((index, numero_de_palabras_en_comun))

    # Encuentra el máximo número de palabras en común
    maximo_palabras = max(lista_numero_palabras_comun, key=lambda x: x[1])[1]

    # Encuentra los índices que tienen ese máximo número de palabras en común
    if maximo_palabras > 0:
        indices_mas_palabras = [index for index, value in lista_numero_palabras_comun if value == maximo_palabras]
    else:
        indices_mas_palabras = []

    return indices_mas_palabras


def get_file_name_without_extension(file_path):
    # Extract the file name with extension
    file_name_with_ext = os.path.basename(file_path)
    # Split the file name and extension, and return the file name
    file_name, _ = os.path.splitext(file_name_with_ext)
    return file_name

def compare_tags(database, tag):
    coincidencias = {}
    
    artista_original, cantor_original = separar_artistas(tag.artist)
    titulo_original = ftfy.fix_text(tag.title).strip()
    if titulo_original is None:
        titulo_original = get_file_name_without_extension(tag._file_name)
    artista_buscar  = unidecode(artista_original).lower()
    cantor_buscar = unidecode(cantor_original).lower()
    titulo_buscar = unidecode(convert_numbers_to_words(titulo_original)).lower().strip()

    #Check all the tags in the database
    coincidencias[TagLabels.TITULO] = database["titulo_min"].str.contains(titulo_buscar, case=False, na=False, regex=False)
    coincidencias[TagLabels.TITULO_EXACTO] = database["titulo"] == titulo_original
    coincidencias[TagLabels.TITULO_PALABRAS] = contain_most_words(database, titulo_buscar, "titulo_min")

    # Handle cases where artist or cantor might be None or empty
    if artista_original:
        coincidencias[TagLabels.ARTISTA] = database["artista_min"].str.contains(artista_buscar, case=False, na=False, regex=False)
        coincidencias[TagLabels.ARTISTA_EXACTO] = database["artista"] == artista_original
        
    else:
        coincidencias[TagLabels.ARTISTA] = False
        coincidencias[TagLabels.ARTISTA_EXACTO] = False

    if cantor_original:
        coincidencias[TagLabels.CANTOR] = database["cantor_min"].str.contains(cantor_buscar, case=False, na=False, regex=False)
        coincidencias[TagLabels.CANTOR_EXACTO] = database["cantor"] == cantor_original
    else:
        coincidencias[TagLabels.CANTOR] = False
        coincidencias[TagLabels.CANTOR_EXACTO] = False

    # Check year (fecha and ano)
    if tag.year is None:
        tag.year = ""
    
    coincidencias[TagLabels.FECHA] = database["fecha"] == tag.year
    coincidencias[TagLabels.ANO] = database["fecha_ano"] == extraer_cuatro_numeros(tag.year)
    
    # Check genre (genero)
    coincidencias[TagLabels.GENERO] = database.estilo.str.contains(tag.genre, case=False, na=False, regex=False) if tag.genre else False

    # Check composer/author (compositor_autor)
    coincidencias[TagLabels.COMPOSITOR_AUTOR] = database["compositor_autor"] == tag.composer

    # Check all fields (todo)
    coincidencias[TagLabels.TODO] = coincidencias[TagLabels.TITULO]  & \
                            (coincidencias[TagLabels.ARTISTA_EXACTO]) & \
                            (coincidencias[TagLabels.CANTOR_EXACTO]) & \
                            (coincidencias[TagLabels.FECHA] | coincidencias[TagLabels.ANO]) & \
                            (coincidencias[TagLabels.GENERO]) & \
                            (coincidencias[TagLabels.COMPOSITOR_AUTOR])
    return coincidencias


def stop_music():
    pygame.mixer.music.stop()


def concaternar_autores(compositor, autor):
    # if not isinstance(compositor, str):
    #     compositor = "?"
    # if not isinstance(autor, str):
    #     autor = "?"
    if compositor != "" and autor != "":
        concatenacion = "Musica: " + compositor + " - Letra: " + autor
    elif compositor != "":
        concatenacion = "Musica: " + compositor
    elif autor != "":
        concatenacion = "Letra: " + autor
    else:
        concatenacion = "Desconocido"

    return concatenacion


def adjust_text_size(text_frame, max_width_cm, max_font_size=100, min_font_size=10):
    # Convertir las medidas de cm a puntos (pt)
    max_width_pt = max_width_cm / 11500

    font_size = max_font_size
    text = ''.join(run.text for paragraph in text_frame.paragraphs for run in paragraph.runs)
    text_length = len(text)

    while font_size >= min_font_size:
        # Aplicar el tamaño de la fuente
        for paragraph in text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(font_size)
                run.font.name = DEFAULT_FONT_NAME

        # Cálculo del ancho estimado del texto basado en el tamaño de la fuente y la longitud del texto
        char_width = (DEFAULT_CHAR_WIDTH / 100) * font_size
        estimated_text_width = char_width * text_length

        # Si el ancho estimado del texto es menor o igual al ancho máximo permitido, se rompe el bucle
        if estimated_text_width <= max_width_pt:
            break

        font_size -= 1

    # Aplicar el tamaño de fuente final
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(font_size)
            run.font.name = DEFAULT_FONT_NAME


def obtener_intervalo_anos(lista):
    # Filtramos sublistas vacías y convertimos los años a enteros, ignorando strings vacíos
    años_int = [int(sublista[0]) for sublista in lista if sublista and sublista[0].isdigit()]
    # Si la lista resultante está vacía, retornamos un mensaje de error o un valor predeterminado
    if not años_int:
        return "No hay años válidos en la lista"

    # Encontramos el año mínimo y máximo
    año_min = min(años_int)
    año_max = max(años_int)
    # Retornamos el string en el formato deseado
    return f"({año_min} - {año_max})"



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

