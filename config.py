import os
from os.path import join

# Define the path conversion based on the computer
path_map = {
    "WINDOW-COMPUTER": "E:\\Dropbox",
    "CAD065": "D:\\Dropbox",
    "LAPTOP-ABRSCER9": "C:\\Users\\diana\\Dropbox"
}
# Identify the current computer name
computer_name = os.getenv('COMPUTERNAME')
dropbox_path = path_map[computer_name]

# Define the root path of the project
project_root = os.path.dirname(os.path.abspath(__file__))

directorio_raiz = dropbox_path + "\\MUSICA\\MP3\\TANGO\\other_stuff\\"
m3u_start_path = join(dropbox_path, "MUSICA", "MP3", "TANGO", "other_stuff")

archivotest = directorio_raiz + "pythontest.csv"

# Define paths relative to the project root
icons = {
    "archivo": "album.png",
    "directorio": "album-list.png",
    "correr": "search-window.png",
    "play": "play_resize.png",
    "stop": "pause_resize.png",
    "transfer": "transfer.png",
    "info": "info-circle_resize.png",
    "trash": "trash.png",
    "searchdb": "searchdb.png",
    "presentacion": "presentation.png",
    "playlist": "playlist.png",
    "convert_playlist": "convert_playlist.png"
}

# Combine with project root
icon_paths = {name: os.path.join(project_root, "icons", filename) for name, filename in icons.items()}

data_folder = os.path.join(project_root, "data")
dbpath = os.path.join(data_folder, 'db.csv')
csv_grabaciones = os.path.join(data_folder, 'todo.csv')
mp3_dir = os.path.join(dropbox_path, "MUSICA", "MP3", "TANGO", "other_stuff", "tangolinkdatabase", "MP3")
output_folder = os.path.join(project_root, "output")

image_folder = os.path.join(project_root, "images")
background_image_path = os.path.join(image_folder, "background_tango.png")

background_image_path = join(image_folder, "background_tango.png")

filetofind_list = []
numero_canciones = 0
articulos_preposiciones_comunes = [
    "a", "de", "del", "que", "en", "para", "por", "y", "no", "te", "se",
    "el", "la", "los", "las", "un", "una", "unos", "unas", "mi", "me"
]
palabras_comunes_artista = [
    'd', 'orquesta', 'tipica', 'de', 'quinteto', 'cuarteto', 'sexteto', 'los'
]

db = None
dic_art = {}

