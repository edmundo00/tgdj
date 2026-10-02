import os
import configparser
from PIL import ImageFont
import pandas as pd
from datetime import datetime


def get_average_char_width(font_path, font_size):
    # Cargar la fuente desde la ruta especificada
    font = ImageFont.truetype(font_path, font_size)
    sample_text = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    total_width = sum(font.getbbox(char)[2] - font.getbbox(char)[0] for char in sample_text)
    return total_width / len(sample_text)

def load_resources_paths():
    # Load Icons
    icons = {
        'archivo': os.path.join(ICON_FOLDER, 'album.png'),
        'directorio': os.path.join(ICON_FOLDER, 'album-list.png'),
        'correr': os.path.join(ICON_FOLDER, 'search-window.png'),
        'play': os.path.join(ICON_FOLDER, 'play.png'),
        'stop': os.path.join(ICON_FOLDER, 'pause.png'),
        'transfer': os.path.join(ICON_FOLDER, 'transfer.png'),
        'info': os.path.join(ICON_FOLDER, 'info-circle.png'),
        'trash': os.path.join(ICON_FOLDER, 'trash.png'),
        'searchdb': os.path.join(ICON_FOLDER, 'searchdb.png'),
        'presentacion': os.path.join(ICON_FOLDER, 'presentation.png'),
        'playlist': os.path.join(ICON_FOLDER, 'playlist.png'),
        'convert_playlist': os.path.join(ICON_FOLDER, 'convert_playlist.png'),
        'merge': os.path.join(ICON_FOLDER, 'merge.png'),
        'musicbee': os.path.join(ICON_FOLDER, 'musicbee.png'),
        'createdb': os.path.join(ICON_FOLDER, 'createdb.png'),
        'loaddb': os.path.join(ICON_FOLDER, 'loaddb.png'),
        'comparedb': os.path.join(ICON_FOLDER, 'comparedb.png'),
        'filterdb': os.path.join(ICON_FOLDER, 'filterdb.png')
    } 

    # Load Images
    images = {
        'background': os.path.join(IMAGE_FOLDER, 'background_tango.png')
        # Add more images if needed
    }

    return icons, images

def _raiz_proyecto():
    """Carpeta con config.ini, data/ y resources/. En el .exe se busca hacia arriba desde el ejecutable."""
    import sys
    if getattr(sys, "frozen", False):
        carpeta = os.path.dirname(sys.executable)
        while True:
            if os.path.exists(os.path.join(carpeta, "config.ini")):
                return carpeta
            superior = os.path.dirname(carpeta)
            if superior == carpeta:
                return os.path.dirname(sys.executable)
            carpeta = superior
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


PROJECT_ROOT = _raiz_proyecto()

# Path to the configuration file
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# Initialize the configparser
config = configparser.ConfigParser()

# Read the config file
config.read(CONFIG_FILE)

# Function to get the appropriate music path
def get_music_path():
    # Get current computer name or user name
    user_name = os.getenv('USERNAME', 'default')

    # Try to get the path defined under UserPaths for the current user
    music_path = config.get('UserPaths', user_name, fallback=None)

    # If no user-specific path is found, use the generic one
    if not music_path:
        music_path = config.get('Paths', 'music_path', fallback=None)

    if not music_path:
        raise ValueError("Music path not set in the config file. Please update the config.ini.")

    return music_path

# General paths and variables
MUSIC_PATH = get_music_path()
RESOURCES_PATH = os.path.join(PROJECT_ROOT, 'resources')

ICON_FOLDER = os.path.join(RESOURCES_PATH, 'icons')
IMAGE_FOLDER = os.path.join(RESOURCES_PATH, 'images')
FONTS_FOLDER = os.path.join(RESOURCES_PATH, 'fonts')

DATA_FOLDER = os.path.join(PROJECT_ROOT, 'data')

OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, 'output')

DB_ORIGINAL_CSV_PATH = os.path.join(DATA_FOLDER, 'mergeddb.csv')
# tangodb.csv es mergeddb.csv limpia (python -m src.utils.mejorar_bd o menú Archivo de la app)
DB_CSV_PATH = os.path.join(DATA_FOLDER, 'tangodb.csv')
if not os.path.exists(DB_CSV_PATH):
    DB_CSV_PATH = DB_ORIGINAL_CSV_PATH

DEFAULT_FONT_PATH = os.path.join(FONTS_FOLDER,"coopbl.ttf")
DEFAULT_FONT_NAME = "Cooper Black"  # Cambia "Arial" por la fuente deseada
DEFAULT_CHAR_WIDTH = get_average_char_width(DEFAULT_FONT_PATH, 100)

project_root = PROJECT_ROOT

#directorio_raiz = dropbox_path + "\\MUSICA\\MP3\\TANGO\\other_stuff\\"
directorio_raiz = MUSIC_PATH
dropbox_path=MUSIC_PATH
m3u_start_path = os.path.join(dropbox_path, "TDJ", "playlists","trabajo")
presentations_start_path = os.path.join(dropbox_path, "TDJ", "Presentacion")
musicbee_start_folder = os.path.join(dropbox_path, "TDJ", "MUSICBEE DATABASES")

data_folder = DATA_FOLDER
mp3_dir = os.path.join(dropbox_path, "TDJ", "tangolinkdatabase", "MP3")
output_folder = os.path.join(project_root, "output")

image_folder = IMAGE_FOLDER
icon_paths, image_paths = load_resources_paths()
background_image_path = image_paths['background']


background_image_folder = os.path.join(IMAGE_FOLDER,"backgounds")
background_image_path = os.path.join(IMAGE_FOLDER,"backgounds" ,"background_tango.png")
background_tango_degradado = os.path.join(background_image_folder, "background_tango_degradado.png")


articulos_preposiciones_comunes = [
    "a", "de", "del", "que", "en", "para", "por", "y", "no", "te", "se",
    "el", "la", "los", "las", "un", "una", "unos", "unas", "mi", "me"
]


default_milonga_data = {
    'nombre': "El Taller",
    'fecha': "30 de Marzo de 2025",
    'hora_inicio': '18:00',
    'hora_final': '21:30'
}


# Default settings for checkbuttons
DEFAULT_DATE_CHECKED = True
guardar_residuos = False


musicbee_tags = {
    "title": "65",
    "artist": "32",
    "album": "30",
    "year": "88",
    "genre": "59",
    "composer": "43",
}


residuos = []


# Fechas de fallecimiento de los principales directores de orquesta de tango (en formato datetime)
fallecimiento = {
    'carlos di sarli': datetime.strptime('12-01-1960', '%d-%m-%Y').date(),
    'juan d\'arienzo': datetime.strptime('14-01-1976', '%d-%m-%Y').date(),
    'osvaldo pugliese': datetime.strptime('25-07-1995', '%d-%m-%Y').date(),
    'anibal troilo': datetime.strptime('18-05-1975', '%d-%m-%Y').date(),
    'alfredo de angelis': datetime.strptime('31-03-1992', '%d-%m-%Y').date(),
    'francisco canaro': datetime.strptime('14-12-1964', '%d-%m-%Y').date(),
    'rodolfo biagi': datetime.strptime('24-09-1969', '%d-%m-%Y').date(),
    'ricardo tanturi': datetime.strptime('24-01-1973', '%d-%m-%Y').date(),
    'miguel calo': datetime.strptime('24-05-1972', '%d-%m-%Y').date(),
    'lucio demare': datetime.strptime('06-03-1974', '%d-%m-%Y').date(),
    'edgardo donato': datetime.strptime('15-02-1963', '%d-%m-%Y').date(),
    'julio de caro': datetime.strptime('11-03-1980', '%d-%m-%Y').date(),
    'pedro laurenz': datetime.strptime('07-07-1972', '%d-%m-%Y').date(),
    'osvaldo fresedo': datetime.strptime('18-11-1984', '%d-%m-%Y').date(),
    'angel d\'agostino': datetime.strptime('16-01-1991', '%d-%m-%Y').date(),
    'ricardo malerba': datetime.strptime('29-06-1974', '%d-%m-%Y').date(),
    'francisco lomuto': datetime.strptime('23-12-1950', '%d-%m-%Y').date(),
    'astor piazzolla': datetime.strptime('04-07-1992', '%d-%m-%Y').date(),
    'alberto castillo': datetime.strptime('23-07-2002', '%d-%m-%Y').date(),
    'enrique mario francini': datetime.strptime('27-08-1978', '%d-%m-%Y').date(),
    'armando pontier': datetime.strptime('25-12-1983', '%d-%m-%Y').date(),
    'horacio salgan': datetime.strptime('19-08-2016', '%d-%m-%Y').date(),
    'leopoldo federico': datetime.strptime('28-12-2014', '%d-%m-%Y').date(),
    'atilio stampone': datetime.strptime('02-11-2022', '%d-%m-%Y').date(),
    'roberto firpo': datetime.strptime('14-06-1969', '%d-%m-%Y').date(),
    'hector varela': datetime.strptime('30-01-1987', '%d-%m-%Y').date(),
    'jose garcia': datetime.strptime('27-09-1975', '%d-%m-%Y').date(),
    'juan maglio (pacho)': datetime.strptime('14-07-1934', '%d-%m-%Y').date(),
    'enrique rodriguez': datetime.strptime('04-09-1971', '%d-%m-%Y').date(),
    'florindo sassone': datetime.strptime('31-01-1982', '%d-%m-%Y').date(),
    'francisco racciatti': datetime.strptime('22-07-1969', '%d-%m-%Y').date(),
    'jose basso': datetime.strptime('19-08-1987', '%d-%m-%Y').date(),
    'juan carlos cobian': datetime.strptime('10-12-1953', '%d-%m-%Y').date(),
    'carlos garcia': datetime.strptime('21-11-2006', '%d-%m-%Y').date(),
    'rafael canaro': datetime.strptime('28-01-1972', '%d-%m-%Y').date(),
    'luciano leocata': datetime.strptime('20-04-1950', '%d-%m-%Y').date(),
    'francisco pracanico': datetime.strptime('29-03-1971', '%d-%m-%Y').date(),
    'eduardo arolas': datetime.strptime('29-09-1924', '%d-%m-%Y').date(),
    'sebastian piana': datetime.strptime('17-07-1994', '%d-%m-%Y').date(),
    'osvaldo requena': datetime.strptime('24-04-2010', '%d-%m-%Y').date(),
    'domingo federico': datetime.strptime('17-04-2000', '%d-%m-%Y').date(),
    'donato racciatti': datetime.strptime('02-05-1995', '%d-%m-%Y').date(),
    'adolfo carabelli': datetime.strptime('25-01-1947', '%d-%m-%Y').date(),
    'alfredo gobbi': datetime.strptime('21-05-1965', '%d-%m-%Y').date(),
    'orquesta tipica victor': datetime.strptime('04-05-1944', '%d-%m-%Y').date(),
    'francini-pontier': datetime.strptime('27-08-1978', '%d-%m-%Y').date(),
    'osvaldo manzi': datetime.strptime('24-03-1976', '%d-%m-%Y').date(),
    'roberto goyeneche': datetime.strptime('27-08-1994', '%d-%m-%Y').date(),
    'francisco rotundo': datetime.strptime('26-09-1973', '%d-%m-%Y').date(),
    'edmundo rivero': datetime.strptime('18-01-1986', '%d-%m-%Y').date(),
    'enrique alessio': datetime.strptime('22-01-1980', '%d-%m-%Y').date(),
    'fulvio salamanca': datetime.strptime('31-05-1999', '%d-%m-%Y').date(),
    'alberto marino': datetime.strptime('06-06-1989', '%d-%m-%Y').date(),
    'angel vargas': datetime.strptime('07-07-1959', '%d-%m-%Y').date(),
    'osmar maderna': datetime.strptime('28-04-1951', '%d-%m-%Y').date(),
    'hugo diaz': datetime.strptime('23-10-1977', '%d-%m-%Y').date(),
    'argentino ledesma': datetime.strptime('06-08-2004', '%d-%m-%Y').date(),
    'floreal ruiz': datetime.strptime('17-04-1978', '%d-%m-%Y').date(),
    'nelly omar': datetime.strptime('20-12-2013', '%d-%m-%Y').date(),
    'miguel villasboas': datetime.strptime('13-09-1990', '%d-%m-%Y').date(),
    'carlos gardel': datetime.strptime('24-06-1935', '%d-%m-%Y').date(),
    'juan bautista guido': datetime.strptime('23-02-1950', '%d-%m-%Y').date(),
    'emilio balcarce': datetime.strptime('08-04-2011', '%d-%m-%Y').date(),
    'agustin magaldi': datetime.strptime('08-09-1938', '%d-%m-%Y').date(),
    'pedro maffia': datetime.strptime('16-10-1967', '%d-%m-%Y').date(),
    'alberto moran': datetime.strptime('14-08-1997', '%d-%m-%Y').date(),
    'jorge vidal': datetime.strptime('14-09-2010', '%d-%m-%Y').date(),
    'joaquin do reyes': datetime.strptime('15-08-1976', '%d-%m-%Y').date()
}


# # Ejemplo de comparación
# if fallecimiento['Osvaldo Pugliese'] > fallecimiento['Aníbal Troilo']:
#     print("Osvaldo Pugliese falleció después que Aníbal Troilo")
# else:
#     print("Osvaldo Pugliese falleció antes que Aníbal Troilo")


