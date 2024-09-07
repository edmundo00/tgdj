import os
import configparser
import tkinter as tk
from PIL import ImageFont



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
        'merge': os.path.join(ICON_FOLDER, 'merge.png')
    } 

    # Load Images
    images = {
        'background': os.path.join(IMAGE_FOLDER, 'background_tango.png')
        # Add more images if needed
    }

    return icons, images

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

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
TEST_FILES_FOLDER = os.path.join(PROJECT_ROOT, 'tests', 'music_files')

OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, 'output')

# Add other common variables or constants here
DB_CSV_PATH = os.path.join(DATA_FOLDER, 'db.csv')

DEFAULT_FONT_PATH = os.path.join(FONTS_FOLDER,"coopbl.ttf")
DEFAULT_FONT_NAME = "Cooper Black"  # Cambia "Arial" por la fuente deseada
DEFAULT_CHAR_WIDTH = get_average_char_width(DEFAULT_FONT_PATH, 100)

# Especificar la ruta completa al archivo de la fuente

project_root = PROJECT_ROOT

#directorio_raiz = dropbox_path + "\\MUSICA\\MP3\\TANGO\\other_stuff\\"
directorio_raiz = MUSIC_PATH
dropbox_path=MUSIC_PATH
m3u_start_path = os.path.join(dropbox_path, "MUSICA", "MP3", "TANGO", "other_stuff", "playlists")

data_folder = DATA_FOLDER
csv_grabaciones = os.path.join(data_folder, 'todo.csv')
mp3_dir = os.path.join(dropbox_path, "MUSICA", "MP3", "TANGO", "other_stuff", "tangolinkdatabase", "MP3")
output_folder = os.path.join(project_root, "output")

image_folder = IMAGE_FOLDER
icon_paths, image_paths = load_resources_paths()
background_image_path = image_paths['background']

data_folder = os.path.join(project_root, "data")
dbpath = os.path.join(data_folder, 'db.csv')
csv_grabaciones = os.path.join(data_folder, 'todo.csv')
mp3_dir = os.path.join(dropbox_path, "MUSICA", "MP3", "TANGO", "other_stuff", "tangolinkdatabase", "MP3")
output_folder = os.path.join(project_root, "output")

font_folder = os.path.join(project_root, "Fonts")
orchestra_folder = os.path.join(IMAGE_FOLDER, "orquestas")

background_image_folder = os.path.join(IMAGE_FOLDER,"backgounds")
background_image_path = os.path.join(IMAGE_FOLDER,"backgounds" ,"background_tango.png")
background_tango_degradado = os.path.join(background_image_folder, "background_tango_degradado.png")

merged_images_folder = os.path.join(IMAGE_FOLDER,"orquestas_con_fondo")

archivotest = os.path.join(output_folder, "pythontest.csv")

filetofind_list = []
numero_canciones = 0
articulos_preposiciones_comunes = [
    "a", "de", "del", "que", "en", "para", "por", "y", "no", "te", "se",
    "el", "la", "los", "las", "un", "una", "unos", "unas", "mi", "me"
]
palabras_comunes_artista = [
    'd', 'orquesta', 'tipica', 'de', 'quinteto', 'cuarteto', 'sexteto', 'los'
]

# Definición de la configuración de columnas para los subframes
columnas_config = {
    'archivo': [
        {'col': 1, 'weight': 0, 'minsize': 25, 'description': 'Info', 'tipo': 'button'},
        {'col': 2, 'weight': 4, 'minsize': 240, 'description': 'Titulo', 'tipo': 'label'},
        {'col': 3, 'weight': 3, 'minsize': 150, 'description': 'Orquesta', 'tipo': 'label'},
        {'col': 4, 'weight': 3, 'minsize': 150, 'description': 'Cantor', 'tipo': 'label'},
        {'col': 5, 'weight': 0, 'minsize': 100, 'description': 'Fecha', 'tipo': 'label'},
        {'col': 6, 'weight': 0, 'minsize': 25, 'description': 'Play', 'tipo': 'play_button'},
        {'col': 7, 'weight': 0, 'minsize': 25, 'description': 'Pausa', 'tipo': 'stop_button'},
    ],
    'resultado': [
        {'col': 1, 'weight': 0, 'minsize': 20, 'description': 'Checkbox', 'tipo': 'checkbox'},
        {'col': 2, 'weight': 4, 'minsize': 240, 'description': 'Titulo', 'tipo': 'label'},
        {'col': 3, 'weight': 3, 'minsize': 150, 'description': 'Orquesta', 'tipo': 'label'},
        {'col': 4, 'weight': 3, 'minsize': 150, 'description': 'Cantor', 'tipo': 'label'},
        {'col': 5, 'weight': 0, 'minsize': 100, 'description': 'Fecha', 'tipo': 'label'},
        {'col': 6, 'weight': 0, 'minsize': 130, 'description': 'Estilo', 'tipo': 'label'},
        {'col': 7, 'weight': 0, 'minsize': 25, 'description': 'Info', 'tipo': 'button'},
        {'col': 8, 'weight': 0, 'minsize': 25, 'description': 'Play_30', 'tipo': 'play_button'},
        {'col': 9, 'weight': 0, 'minsize': 25, 'description': 'Play_10', 'tipo': 'play_button'},
        {'col': 10, 'weight': 0, 'minsize': 25, 'description': 'Pausa', 'tipo': 'stop_button'},
    ]
}

default_milonga_data = {
    'nombre': "Glorieta de los miércoles",
    'fecha': "4 de Septiembre de 2024",
    'hora_inicio': '20:00',
    'hora_final': '22:00'
}


path_map = {
    "WINDOW-COMPUTER": "E:\\Dropbox",
    "CAD065": "D:\\Dropbox",
    "LAPTOP-ABRSCER9": "C:\\Users\\diana\\Dropbox"
}


# Default settings for checkbuttons
DEFAULT_DATE_CHECKED = True
DEFAULT_PERFECT_MATCHES = False
DEFAULT_ARTIST_NOT_FOUND = True
DEFAULT_TITLE_NOT_FOUND = True
DEFAULT_REMAINING = True