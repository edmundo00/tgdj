import pandas as pd
from tinytag import TinyTag
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image as PilImage, ImageTk
from pptx.util import Cm, Pt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR
import os
from os.path import join
import re
from unidecode import unidecode
import num2words as nw
import pygame
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3
from datetime import datetime
from collections import Counter

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
icono_archivo = os.path.join(project_root, "icons", "album.png")
icono_directorio = os.path.join(project_root, "icons", "album-list.png")
icono_correr = os.path.join(project_root, "icons", "search-window.png")
icono_play = os.path.join(project_root, "icons", "play_resize.png")
icono_stop = os.path.join(project_root, "icons", "pause_resize.png")
icono_transfer = os.path.join(project_root, "icons", "transfer.png")
icono_info = os.path.join(project_root, "icons", "info-circle_resize.png")
icono_trash = os.path.join(project_root, "icons", "trash.png")
icono_searchdb = os.path.join(project_root, "icons", "searchdb.png")
icono_presentacion = os.path.join(project_root, "icons", "presentation.png")
icono_playlist = os.path.join(project_root, "icons", "playlist.png")

data_folder = os.path.join(project_root, "data")
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


def separar_artistas(artistas):
    artists = artistas.split(" / ")
    artists1 = artists[0]
    if len(artists) > 1:
        artists2 = artists[1]
    else:
        artists2 = ""
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
        raise ValueError(f"Invalid date format: {date_str}")


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

    text = unidecode(text).lower()

    return text


def contain_most_words(database, text, columna):
    text = unidecode(convert_numbers_to_words(text)).lower()
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


def coincide(database, tag, que_coincide, talcual=False):
    lista_de_booleanos = []

    artista_original, cantor_original = separar_artistas(tag.artist)

    tituloabuscar = unidecode(convert_numbers_to_words(tag.title)).lower().strip()
    artistaabuscar = unidecode(convert_numbers_to_words(artista_original)).lower()
    cantorabuscar = unidecode(convert_numbers_to_words(cantor_original)).lower()

    if que_coincide == 'titulo':
        valor_buscado = tag.title
        if talcual:
            lista_de_booleanos = database["titulo"] == tag.title
        else:
            lista_de_booleanos = database["titulo_min"].str.contains(tituloabuscar, case=False, na=False, regex=False)

    if que_coincide == 'artista':
        valor_buscado = artista_original
        if talcual:
            lista_de_booleanos = database["artista"] == artista_original
        else:
            lista_de_booleanos = database["artista_min"].str.contains(artistaabuscar, case=False, na=False,
                                                                      regex=False)
    if que_coincide == 'cantor':
        valor_buscado = cantor_original
        if talcual:
            lista_de_booleanos = database["cantor"] == cantor_original
        else:
            lista_de_booleanos = database["cantor_min"].str.contains(cantorabuscar, case=False, na=False,
                                                                     regex=False)

    if tag.year == None:
        tag.year = ""
    if que_coincide == 'fecha':
        valor_buscado = tag.year
        lista_de_booleanos = database["fecha"] == tag.year

    if que_coincide == 'ano':
        lista_de_booleanos = database["fecha_ano"] == extraer_cuatro_numeros(tag.year)
        valor_buscado = extraer_cuatro_numeros(tag.year)

    if que_coincide == 'genero':
        valor_buscado = tag.genre
        if talcual:
            lista_de_booleanos = database["estilo"] == tag.genre
        else:
            lista_de_booleanos = database.estilo.str.contains(artistaabuscar, case=False, na=False,
                                                              regex=False)

    if que_coincide == 'compositor_autor':
        valor_buscado = tag.composer
        lista_de_booleanos = database["compositor_autor"] == tag.composer

    if que_coincide == 'todo':
        ti = database["titulo"]
        ar = database["artista"]
        ca = database["cantor"]
        fe = database["fecha"]
        es = database["estilo"]
        co = database["compositor_autor"]

        lista_de_booleanos = (ti == tag.title) & (ar == artista_original) & (ca == cantor_original) & (
                    fe == tag.year) & (es == tag.genre) & (co == tag.composer)

    return lista_de_booleanos


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


class PresentationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Presentation Creator")
        self.root.state('zoomed')
        # Set the window to be on top
        self.root.attributes('-topmost', True)
        self.root.after_idle(lambda: self.root.attributes('-topmost', False))  # Allow interaction with other windows

        # Default paths

        output_folder = join(dropbox_path, "MUSICA", "MP3", "TANGO", "other_stuff", "Presentacion")


        self.merged_image_folder = image_folder
        self.m3u_file_path = None
        self.audio_files = []
        # self.audio_tags = []

        # Create Menu
        menubar = tk.Menu(root)
        root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_m3u_file)
        menubar.add_cascade(label="File", menu=file_menu)

        preferences_menu = tk.Menu(menubar, tearoff=0)
        preferences_menu.add_command(label="Preferences", command=self.open_preferences)
        menubar.add_cascade(label="Preferences", menu=preferences_menu)

        tk.Label(root, text="Nombre de la Milonga:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.nombre_milonga_entry = tk.Entry(root, width=50)
        self.nombre_milonga_entry.grid(row=0, column=1, padx=10, pady=10)
        self.nombre_milonga_entry.insert(0, "Arrabal")

        tk.Label(root, text="Fecha:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.fecha_entry = tk.Entry(root, width=50)
        self.fecha_entry.grid(row=1, column=1, padx=10, pady=10)
        self.fecha_entry.insert(0, "18 de Septiembre del 2024")

        self.update_background_thumbnail()

        load_m3u_button = ttk.Button(root, text="Load M3U File", command=self.open_m3u_file)
        load_m3u_button.grid(row=3, column=0, columnspan=2, pady=10)

        self.create_button = ttk.Button(root, text="Crear Presentación", command=self.create_presentation,
                                        state=tk.DISABLED)
        self.create_button.grid(row=5, column=0, columnspan=2, pady=20)

        self.tree = ttk.Treeview(root, columns=("Title", "Artist", "Genre"), show='headings')
        self.tree.heading("Title", text="Title")
        self.tree.heading("Artist", text="Artist")
        self.tree.heading("Genre", text="Genre")
        self.tree.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.estructura_frame = ttk.LabelFrame(root, text="Estructura")
        self.estructura_frame.grid(row=0, column=2, rowspan=6, padx=10, pady=10, sticky="nsew")

        self.estructura_tree = ttk.Treeview(self.estructura_frame, columns=("Col1", "Col2", "Col3", "Col4"),
                                            show='headings')
        self.estructura_tree.heading("Col1", text="Genero")
        self.estructura_tree.heading("Col2", text="Orquesta")
        self.estructura_tree.heading("Col3", text="Columna 3")
        self.estructura_tree.heading("Col4", text="Numero de canciones")  # New column heading
        self.estructura_tree.pack(expand=True, fill='both', padx=10, pady=10)

        root.grid_rowconfigure(4, weight=1)
        root.grid_columnconfigure(1, weight=1)
        root.grid_columnconfigure(2, weight=1)

    def create_structure(self):
        # Check if 'genre' column exists and is not empty
        if 'genre' not in self.df.columns or self.df['genre'].empty:
            print("The 'genre' column is missing or empty.")
            return

        # Original list
        original_list = self.df['genre']

        # Create a new DataFrame from the 'genre' and 'artist1' columns
        df_genres = pd.DataFrame({'genre': original_list, 'artist1': self.df['artist1']})

        # Identify when the genre value changes
        df_genres['change'] = df_genres['genre'].ne(df_genres['genre'].shift())

        # Create a group identifier based on consecutive identical genre values
        df_genres['group'] = df_genres['change'].cumsum()

        # Check if all orchestras in the same group are the same
        df_genres['same_orchestra'] = df_genres.groupby('group')['artist1'].transform(lambda x: x.nunique() == 1)

        # Collect DataFrames for each group in a list
        group_data_list = [self.df.loc[indices].reset_index(drop=True) for group, indices in
                           df_genres.groupby('group').groups.items()]

        # Group by the group identifier and calculate the unique values, counts, positions, same_orchestra status, and store the DataFrame for each group
        self.result = df_genres.groupby('group').agg(
            unique_value=('genre', 'first'),
            repetition_count=('genre', 'size'),
            position=('group', 'idxmin'),
            same_orchestra=('same_orchestra', 'first'),
            orchestra_value=('artist1', lambda x: x.iloc[0] if x.nunique() == 1 else "")
        ).reset_index(drop=True)

        # Attach the group DataFrames to the result DataFrame
        self.result['group_data'] = group_data_list

        # Clear the current content of the estructura_tree
        for i in self.estructura_tree.get_children():
            self.estructura_tree.delete(i)

        # Configure tag styles for the Treeview
        self.estructura_tree.tag_configure("SameOrchestra.Treeview", background="honeydew", foreground="black")
        self.estructura_tree.tag_configure("DifferentOrchestra.Treeview", background="red", foreground="white")

        # Insert new rows into the estructura_tree with the new column data
        for _, row in self.result.iterrows():

            if row['same_orchestra']:
                row_style = "SameOrchestra.Treeview"
            else:
                row_style = "DifferentOrchestra.Treeview"

            # Here you could do something with row['group_data'] if needed

            self.estructura_tree.insert("", "end", values=(
                row['unique_value'], row['orchestra_value'], '', row['repetition_count'], row['same_orchestra']),
                                        tags=(row_style,))

        # Save the result DataFrame to an CSV file
        save_csv_path = os.path.join(data_folder, "self_result.csv")
        self.result.to_csv(save_csv_path, index=False)

        # Load the CSV file into a DataFrame
        # load_path = os.path.join(dropbox_path, "MUSICA", "MP3", "TANGO", "other_stuff", "PYTHON",
        #                          "tgdj", "data", "self_result.csv")
        # self.result = pd.read_csv(load_path)

    def canciones_tanda(self, tanda, tags):
        # Check if the result has at least 'tanda' rows
        if len(self.result) < tanda:
            print(f"The result DataFrame has less than {tanda} rows.")
            return None

        # Access the specified row (index tanda-1 since indexing is 0-based)
        selected_row = self.result.iloc[tanda - 1]

        # Extract the DataFrame from the group_data column
        group_df = selected_row['group_data']

        # Initialize a list to store the tags for each row
        list_of_values = []

        # Loop through each row in group_df
        for index, row in group_df.iterrows():
            # Extract the values of the specified tags in the current row
            selected_values = [row[tag] for tag in tags]
            # Append the list of values to the list_of_values
            list_of_values.append(selected_values)

        return list_of_values

    def open_m3u_file(self):
        # Temporarily make the window non-topmost to allow file dialog interaction
        self.root.attributes('-topmost', False)

        # Open file dialog
        self.m3u_file_path = filedialog.askopenfilename(
            initialdir=m3u_start_path,
            filetypes=[("M3U files", "*.m3u"), ("All files", "*.*")]
        )

        # Return focus to the popup window
        self.root.attributes('-topmost', True)

        if self.m3u_file_path:
            # Clear previous data
            if hasattr(self, 'df'):
                self.df = self.df.iloc[0:0]  # Clear the DataFrame but keep the columns

            self.audio_files = []  # Clear the audio files list
            # self.audio_tags = []  # Clear the audio tags list

            # Load the M3U file and extract data
            with open(self.m3u_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if os.path.exists(line):
                            self.audio_files.append(line)
                            tags = self.read_audio_tags(line)
                            # self.audio_tags.append(tags)
                        else:
                            modified_path = dropbox_path + line.split("Dropbox", 1)[1]
                            if os.path.exists(modified_path):
                                self.audio_files.append(modified_path)
                                tags = self.read_audio_tags(modified_path)
                                # self.audio_tags.append(tags)

            self.create_structure()

            if self.audio_files:
                self.display_m3u_summary()
                self.create_button.config(state=tk.NORMAL)

    def read_audio_tags(self, file_path):
        # Check if the DataFrame is already initialized, if not, initialize it
        if not hasattr(self, 'df'):
            columns = ['title', 'artist1', 'artist2', 'album', 'year', 'genre', 'composer', 'lyrics', 'bpm', 'duration',
                       'extension', 'bitrate']
            self.df = pd.DataFrame(columns=columns)

        try:
            # Extract tags from the audio file
            tags = TinyTag.get(file_path)
            self.artists1, self.artists2 = separar_artistas(tags.artist)

            # Extract file extension and bitrate
            extension = file_path.split('.')[-1]
            bitrate = tags.bitrate if tags.bitrate else "Unknown Bitrate"

            # Prepare a dictionary with the extracted tags
            tag_data = {
                "title": tags.title if tags.title else "Unknown Title",
                "artist1": self.artists1 if tags.artist else "Unknown Artist",
                "artist2": self.artists2 if tags.artist else "Unknown Artist",
                "album": tags.album if tags.album else "Unknown Album",
                "year": tags.year if tags.year else "Unknown Year",
                "genre": tags.genre if tags.genre else "Unknown Genre",
                "composer": tags.composer if tags.composer else "Unknown Composer",
                "lyrics": tags.lyrics if hasattr(tags, 'lyrics') else "Unknown Lyrics",
                "bpm": tags.bpm if hasattr(tags, 'bpm') else "Unknown BPM",
                "duration": tags.duration if tags.duration else "Unknown Duration",
                "extension": extension,
                "bitrate": bitrate
            }

            # Remove entries in tag_data where the value is None, NaN, or an empty string
            tag_data = {key: (value if value else "Unknown") for key, value in tag_data.items() if
                        value not in [None, ""]}

        except Exception as e:
            # Fallback tags in case of an error
            tag_data = {
                "title": "Unknown Title",
                "artist1": "Unknown Artist",
                "artist2": "Unknown Artist",
                "album": "Unknown Album",
                "year": "Unknown Year",
                "genre": "Unknown Genre",
                "composer": "Unknown Composer",
                "lyrics": "Unknown Lyrics",
                "bpm": "Unknown BPM",
                "duration": "Unknown Duration",
                "extension": extension if 'extension' in locals() else "Unknown Extension",
                "bitrate": bitrate if 'bitrate' in locals() else "Unknown Bitrate"
            }

        # Convert tag_data to a DataFrame and replace empty or all-NA columns
        tag_df = pd.DataFrame([tag_data])

        # Remove any columns that are all NA or have only "Unknown" values before concatenating
        tag_df.replace("Unknown", pd.NA, inplace=True)
        tag_df.dropna(axis=1, how='all', inplace=True)

        # If self.df is empty, assign tag_df directly, otherwise concatenate
        if self.df.empty:
            self.df = tag_df
        else:
            self.df = pd.concat([self.df, tag_df], ignore_index=True)

        # Apply the extract_year function to the 'year' column and create a new 'ano' column
        self.df['ano'] = self.df['year'].apply(extract_year)

    def display_m3u_summary(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        for index, row in self.df.iterrows():
            self.tree.insert("", "end", values=(row.title, row.artist1, row.genre))

    def open_preferences(self):
        pref_window = tk.Toplevel(self.root)
        pref_window.title("Preferences")
        pref_window.geometry("600x200")

        tk.Label(pref_window, text="Output Path:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        output_path_entry = tk.Entry(pref_window, width=70)
        output_path_entry.grid(row=0, column=1, padx=10, pady=10)
        output_path_entry.insert(0, output_folder)

        tk.Label(pref_window, text="Background Image:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        background_entry = tk.Entry(pref_window, width=70)
        background_entry.grid(row=1, column=1, padx=10, pady=10)
        background_entry.insert(0, background_image_path)

        tk.Label(pref_window, text="M3U Start Path:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        m3u_start_path_entry = tk.Entry(pref_window, width=70)
        m3u_start_path_entry.grid(row=2, column=1, padx=10, pady=10)
        m3u_start_path_entry.insert(0, m3u_start_path)

        def save_preferences():
            output_folder = output_path_entry.get()
            background_image_path = background_entry.get()
            m3u_start_path = m3u_start_path_entry.get()
            messagebox.showinfo("Preferences", "Preferences saved!")
            pref_window.destroy()

        save_button = ttk.Button(pref_window, text="Save", command=save_preferences)
        save_button.grid(row=3, column=0, columnspan=2, pady=20)

    def update_background_thumbnail(self):
        image = PilImage.open(background_image_path)
        image.thumbnail((100, 100))
        self.thumbnail_image = ImageTk.PhotoImage(image)

        if hasattr(self, 'thumbnail_button'):
            self.thumbnail_button.config(image=self.thumbnail_image)
        else:
            self.thumbnail_button = tk.Button(self.root, image=self.thumbnail_image,
                                              command=self.select_background_image)
            self.thumbnail_button.grid(row=2, column=0, columnspan=2, pady=10)

    def select_background_image(self):
        new_image_path = filedialog.askopenfilename(
            initialdir=os.path.dirname(background_image_path),
            filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.webp;*.bmp"), ("All files", "*.*")]
        )
        if new_image_path:
            background_image_path = new_image_path
            self.update_background_thumbnail()

    def apply_gradient_overlay(self):
        # Open the original image
        base = PilImage.open(background_image_path).convert("RGBA")

        orchestra = PilImage.open(self.orchestra_path).convert("RGBA")

        maximum_in_width = 0.4 * base.width
        maximum_in_height = base.height

        resize_factor = maximum_in_height / orchestra.height

        if (resize_factor * orchestra.width) > maximum_in_width:
            resize_factor = maximum_in_width / orchestra.width

        new_width = int(orchestra.width * resize_factor)
        new_height = int(orchestra.height * resize_factor)

        # Resize the orchestra image
        orchestra = orchestra.resize((new_width, new_height), PilImage.Resampling.LANCZOS)

        # Create a gradient overlay
        gradient = PilImage.new('L', (base.width, base.height))
        for x in range(base.width):
            # Gradient from opaque dark gray (on the left) to fully transparent (on the right)
            gradient_value = int(
                255 * (1 - x / base.width))  # Fully opaque on the left to fully transparent on the right
            for y in range(base.height):
                gradient.putpixel((x, y), gradient_value)

        # Convert gradient to RGBA
        gradient_rgba = PilImage.new('RGBA', base.size)
        for y in range(base.height):
            for x in range(base.width):
                gradient_rgba.putpixel((x, y), (
                105, 105, 105, gradient.getpixel((x, y))))  # Dark gray with varying transparency

        # Apply the gradient to the base image
        combined = PilImage.alpha_composite(base, gradient_rgba)

        # Paste the resized orchestra image onto the combined image
        position = (0, combined.height - orchestra.height)  # Centering
        combined.paste(orchestra, position, orchestra)  # The third argument is the mask to maintain transparency

        # Save the gradient and the combined image
        # gradient_rgba.save(self.path_gradiente, "PNG")
        self.merged_image_path = join(image_folder, "merged_background.png")

        combined.save(self.merged_image_path, "PNG")

    def create_slide_for_tanda(self, prs, tanda_number):
        # NAME OF THE ORCHESTRA
        orchestra_value = self.result.iloc[tanda_number - 1]['orchestra_value']
        orchestra_value_min = unidecode(orchestra_value).lower()
        self.tanda_gender = self.result.iloc[tanda_number - 1]['unique_value']
        if 'tango' not in self.tanda_gender:
            self.merged_image_path = join(self.merged_image_folder, "background_cortina.png")
        else:
            # Create a merged image with gradient overlay
            self.path_gradiente = join(self.merged_image_folder, "gradiente_background.png")
            self.orchestra_path = os.path.join(image_folder, f'{orchestra_value_min}.png')
            self.apply_gradient_overlay()

        # Add a slide with a title and content layout
        slide_layout = prs.slide_layouts[5]  # Use a blank layout
        slide = prs.slides.add_slide(slide_layout)

        # Set the merged background image with gradient
        slide.shapes.add_picture(self.merged_image_path, 0, 0, width=prs.slide_width, height=prs.slide_height)

        if 'tango' not in self.tanda_gender:
            lista = self.canciones_tanda(tanda_number, ['title', 'ano', 'composer'])
            title, year, composer = lista[0]

            posc2 = [5, 5, 25, 5]
            # Use the existing paragraph instead of adding a new one
            title_box = slide.shapes.add_textbox(Cm(posc2[0]), Cm(posc2[1]), Cm(posc2[2]), Cm(posc2[3]))
            title_frame = title_box.text_frame
            title_frame.clear()  # Clear any existing text or paragraphs

            # Modify the first (and only) paragraph
            title_paragraph1 = title_frame.paragraphs[0]
            title_paragraph1.level = 0
            run_orquesta = title_paragraph1.add_run()

            run_orquesta.text = f'{orchestra_value}'
            run_orquesta.font.size = Pt(100)
            run_orquesta.font.color.rgb = RGBColor(255, 255, 255)  # White color
            run_orquesta.font.bold = True

            posc2 = [8, 10, 22, 5]
            # Modify the first (and only) paragraph for the next text box
            text_box = slide.shapes.add_textbox(Cm(posc2[0]), Cm(posc2[1]), Cm(posc2[2]), Cm(posc2[3]))
            text_frame = text_box.text_frame
            text_frame.clear()  # Clear any existing text or paragraphs

            paragraph1 = text_frame.paragraphs[0]
            paragraph1.level = 0
            run_titulo = paragraph1.add_run()
            run_titulo.text = title
            run_titulo.font.size = Pt(50)
            run_titulo.font.color.rgb = RGBColor(255, 255, 255)  # White color
            run_titulo.font.bold = True

            # Add bullet (if necessary)
            paragraph1.space_before = Pt(12)
            paragraph1.space_after = Pt(12)
            paragraph1.font.shadow = True

            # Append the year in parentheses to the same paragraph
            run_fecha = paragraph1.add_run()
            run_fecha.text = f'   ({year})'
            run_fecha.font.size = Pt(50)
            run_fecha.font.color.rgb = RGBColor(255, 255, 255)  # White color

        else:
            initial_text = '' if orchestra_value.startswith("Orquesta") else 'Orquesta de '

            # Define el offset deseado en centímetros
            offset_cm = 0.1  # Por ejemplo, 0.1 cm

            # ORQUESTA POSICION HORIZONTAL, POSICION VERTICAL, ANCHO, ALTURA
            poso = [2, 0.5, 32, 3]

            # Añadir los cuadros de texto para simular el borde negro
            for x_offset in [-offset_cm, offset_cm]:
                for y_offset in [-offset_cm, offset_cm]:
                    shadow_box = slide.shapes.add_textbox(Cm(poso[0]) + Cm(x_offset), Cm(poso[1]) + Cm(y_offset),
                                                          Cm(poso[2]), Cm(poso[3]))
                    shadow_frame = shadow_box.text_frame
                    shadow_paragraph = shadow_frame.paragraphs[0]
                    shadow_paragraph.level = 0  # Primer nivel
                    shadow_run = shadow_paragraph.add_run()

                    shadow_run.text = f'{initial_text}{orchestra_value}'
                    shadow_run.font.size = Pt(65)
                    shadow_run.font.color.rgb = RGBColor(0, 0, 0)  # Color negro
                    shadow_run.font.bold = True

            # Añadir el cuadro de texto principal con el texto blanco
            title_box = slide.shapes.add_textbox(Cm(poso[0]), Cm(poso[1]), Cm(poso[2]), Cm(poso[3]))
            title_frame = title_box.text_frame
            title_paragraph1 = title_frame.paragraphs[0]
            title_paragraph1.level = 0
            run_orquesta = title_paragraph1.add_run()
            run_orquesta.text = f'{initial_text}{orchestra_value}'
            run_orquesta.font.size = Pt(65)
            run_orquesta.font.color.rgb = RGBColor(255, 255, 255)  # Color blanco
            run_orquesta.font.bold = True

            # tgdj  POSICION HORIZONTAL, POSICION VERTICAL, ANCHO, ALTURA
            post = [25, 16, 8, 2.5]

            # Añadir el cuadro de texto principal con el texto blanco
            tgdj_box = slide.shapes.add_textbox(Cm(post[0]), Cm(post[1]), Cm(post[2]), Cm(post[3]))
            tgdj_frame = tgdj_box.text_frame
            tgdj_paragraph1 = tgdj_frame.paragraphs[0]
            tgdj_paragraph1.level = 0
            run_tgdj = tgdj_paragraph1.add_run()
            run_tgdj.text = f'© TDJ Edmundo Fraga\n{self.nombre_milonga_entry.get()}\n{self.fecha_entry.get()}'
            run_tgdj.font.size = Pt(20)
            run_tgdj.font.color.rgb = RGBColor(255, 255, 255)  # Color blanco
            run_tgdj.font.bold = False

           # Añadir una línea
            left = Cm(14)  # posición horizontal
            top = Cm(4)  # posición vertical
            width = Cm(17)  # ancho de la línea
            height = Cm(0)  # altura de la línea
            line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, left, top, left + width, top + height)
            # Estilo de la línea
            line.line.color.rgb = RGBColor(255, 255, 255)  # color blanco
            line.line.width = Pt(10)  # ancho de la línea

            # TITULOS POSICION HORIZONTAL, POSICION VERTICAL, ANCHO, ALTURA, DISTANCIA ENTRE ELLOS
            post = [15, 5, 18, 3, 2.5]

            counter = 0
            for rows in self.canciones_tanda(tanda_number, ['title', 'ano', 'composer']):
                title, year, composer = rows

                # Añadir cuadros de texto para el título con borde negro
                for x_offset in [-offset_cm, offset_cm]:
                    for y_offset in [-offset_cm, offset_cm]:
                        shadow_box = slide.shapes.add_textbox(Cm(post[0]) + Cm(x_offset),
                                                              Cm(post[1] + counter * post[4]) + Cm(y_offset),
                                                              Cm(post[2]), Cm(post[3]))
                        shadow_frame = shadow_box.text_frame
                        shadow_paragraph = shadow_frame.paragraphs[0]
                        shadow_paragraph.level = 0
                        shadow_run_title = shadow_paragraph.add_run()

                        shadow_run_title.text = title
                        shadow_run_title.font.size = Pt(35)
                        shadow_run_title.font.color.rgb = RGBColor(0, 0, 0)  # Color negro
                        shadow_run_title.font.bold = True

                # Añadir el cuadro de texto principal con el título en blanco
                text_box = slide.shapes.add_textbox(Cm(post[0]), Cm(post[1] + counter * post[4]),
                                                    Cm(post[2]), Cm(post[3]))
                text_frame = text_box.text_frame
                paragraph1 = text_frame.paragraphs[0]
                paragraph1.level = 0

                run_titulo = paragraph1.add_run()
                run_titulo.text = title
                run_titulo.font.size = Pt(35)
                run_titulo.font.color.rgb = RGBColor(255, 255, 255)  # Color blanco
                run_titulo.font.bold = True

                run_fecha = paragraph1.add_run()
                run_fecha.text = f'   ({year})'
                run_fecha.font.size = Pt(30)
                run_fecha.font.color.rgb = RGBColor(255, 255, 255)  # Color blanco

                paragraph2 = text_frame.add_paragraph()  # Create a new paragraph for the composer
                run_compositor = paragraph2.add_run()
                run_compositor.text = composer
                run_compositor.font.size = Pt(18)
                run_compositor.font.color.rgb = RGBColor(255, 255, 255)  # Color blanco
                run_compositor.font.italic = True

                counter += 1


    def create_presentation(self):

        nombre_milonga = self.nombre_milonga_entry.get()
        fecha = self.fecha_entry.get()

        if not nombre_milonga or not fecha:
            messagebox.showwarning("Input Error", "Please fill in both 'Nombre de la Milonga' and 'Fecha'.")
            return

        if not self.m3u_file_path or not self.audio_files:
            messagebox.showwarning("Input Error", "Please load an M3U file.")
            return

        # Path to save the presentation
        output_file = join(output_folder, "presentation.pptx")

        # Create a new PowerPoint presentation
        prs = Presentation()

        # Set slide dimensions (7:4 aspect ratio)
        prs.slide_width = Cm(33.87)
        prs.slide_height = Cm(19.05)

        # Add slides for different tanda numbers
        for tanda_number in range(1, self.result.shape[0]+1):  # Adjust the range as needed
        # for tanda_number in range(1, 5):  # Adjust the range as needed
            self.create_slide_for_tanda(prs, tanda_number)

        # Save the presentation
        try:
            prs.save(output_file)
            os.startfile(output_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save the presentation:\n{e}")


class FILETOFIND:

    def __init__(self, framefiles, framedatabase, ruta_archivo, frame_number):
        self.play_icon = tk.PhotoImage(file=icono_play)
        self.stop_icon = tk.PhotoImage(file=icono_stop)
        self.info_icon = tk.PhotoImage(file=icono_info)
        self.ruta_archivo = ruta_archivo
        self.vars = []
        self.checkbuttons = []
        self.frame_number = frame_number
        self.framefiles = framefiles
        self.framedatabase = framedatabase

        self.leer_tags()

        self.buscar()

        self.representar_datos()

    def representar_datos(self):

        # Determine background color based on frame number
        color_de_fondo = 'whitesmoke' if es_par(self.frame_number) else 'lightgrey'

        # Define colors for different types of matches
        colores_por_coincidencia = {
            0: 'palegreen',  # Coincide artista y titulo
            1: 'lime',  # Coincide artista y titulo y año
            2: 'darkgray',  # Coincide artista y titulo y año y compositor y estilo
            3: 'gold',  # Coincide artista y palabras
            4: 'aquamarine',  # Coincide artista y palabras y año
            5: 'red'  # No ha encontrado nada
        }

        # Determine the frame color based on the match type
        color_de_fondo = colores_por_coincidencia.get(self.tipo_de_coincidencia, color_de_fondo)

        if self.tipo_de_coincidencia == 2:
            altura_frame = 27
        else:
            if len(self.coincidencias) == 0:
                altura_frame = 27
            else:
                altura_frame = 27 * len(self.coincidencias)

        # # Create frames for coincidencias and archivo

        self.frame_coincidencias = tk.Frame(self.framedatabase, height=altura_frame, width=root.winfo_screenwidth() / 2,
                                            bd=2, relief="sunken", bg=color_de_fondo)
        self.frame_archivo = tk.Frame(self.framefiles, bd=2, relief="sunken", height=altura_frame,
                                      width=root.winfo_screenwidth() / 2, bg=color_de_fondo)

        # Grid setup for both frames
        self.frame_coincidencias.grid(row=self.frame_number, column=0)
        self.frame_coincidencias.grid_propagate(False)
        self.frame_archivo.grid(row=self.frame_number, column=0)
        self.frame_archivo.grid_propagate(False)

        # Font styles
        fuente_10_bold = ('Arial', 12, "bold")
        fuente_10 = ('Arial', 12)

        # If no matches are found
        if self.coincidencias.empty:
            self._crear_label(self.frame_coincidencias, text=self.frame_number, row=0, col=0, font=fuente_10,
                              bg=color_de_fondo)
            self._crear_label(self.frame_coincidencias, text="NADA ENCONTRADO", row=0, col=1, font=fuente_10,
                              bg=color_de_fondo)
        else:
            # Loop through each match and create the corresponding labels and buttons
            for counter, (_, row) in enumerate(self.coincidencias.iterrows()):
                # Ensure row is a pandas Series and has the required columns
                if isinstance(row, pd.Series) and 'audio30' in row and 'audio10' in row:
                    self._crear_checkbutton(self.frame_coincidencias, counter)
                    self._crear_button(self.frame_coincidencias, image=self.info_icon,
                                       command=lambda r=row: self.show_popup_db(r), row=counter, col=1,
                                       bg=color_de_fondo)
                    labels_data = [(row['titulo'], 2), (row['artista'], 3), (row['cantor'], 4), (row['estilo'], 5),
                                   (row['fecha'], 6)]

                    for text, col in labels_data:
                        self._crear_label(self.frame_coincidencias, text=text, row=counter, col=col,
                                          font=fuente_10_bold if col == 2 else fuente_10, bg=color_de_fondo)

                    self._crear_play_buttons(self.frame_coincidencias, row, counter, bg=color_de_fondo)
                else:
                    print(f"Unexpected row format or missing columns: {row}")

            if self.hay_coincidencia_preferida:
                self.activar_checkbox(self.coincidencia_preferida)

        # Create labels and buttons for the file information
        self._crear_button(self.frame_archivo, image=self.info_icon, command=self.show_popup_file, row=0, col=1,
                           bg=color_de_fondo)
        file_labels_data = [(self.tags.title, 2), (self.artists1, 3), (self.artists2, 4), (self.tags.year, 5)]

        for text, col in file_labels_data:
            self._crear_label(self.frame_archivo, text=text, row=0, col=col,
                              font=fuente_10_bold if col == 2 else fuente_10, bg=color_de_fondo)

        self._crear_play_button_file(self.frame_archivo, self.tags._filename, len(file_labels_data) + 2,
                                     bg=color_de_fondo)

    def _crear_label(self, parent, text, row, col, font, bg):
        label = tk.Label(parent, text=text, font=font, borderwidth=1, relief="solid", bg=bg)
        label.grid(row=row, column=col, sticky="nw", padx=1, pady=1)

    def _crear_button(self, parent, image, command, row, col, bg):
        button = tk.Button(parent, image=image, relief=tk.FLAT, command=command, bg=bg)
        button.grid(row=row, column=col, sticky="nw", padx=1, pady=1)

    def _crear_checkbutton(self, parent, counter):
        self.var = tk.BooleanVar()
        self.vars.append(self.var)
        checkbutton = tk.Checkbutton(parent, variable=self.var, command=lambda i=counter: self.on_checkbox_toggle(i))
        checkbutton.grid(row=counter, column=0, sticky="nw", padx=1, pady=1)
        self.checkbuttons.append(checkbutton)

    def _crear_play_buttons(self, parent, row, counter, bg):
        if isinstance(row, pd.Series):  # Ensure row is a pandas Series
            play_buttons = [
                (link_to_music(row['audio30']), 7),
                (link_to_music(row['audio10']), 8)
            ]

            for fp, col in play_buttons:
                play_button = tk.Button(parent, image=self.play_icon, relief=tk.FLAT,
                                        command=lambda sp=fp: self.play_music(sp), bg=bg)
                play_button.grid(row=counter, column=col, sticky="nw", padx=2, pady=2)

            stop_button = tk.Button(parent, image=self.stop_icon, relief=tk.FLAT, command=stop_music, bg=bg)
            stop_button.grid(row=counter, column=9, sticky="nw", padx=2, pady=2)

    def _crear_play_button_file(self, parent, archivo, counter, bg):

        playmusic_button = tk.Button(parent, image=self.play_icon, relief=tk.FLAT,
                                     command=lambda fp=archivo: self.play_music(fp), bg=bg)
        playmusic_button.grid(row=0, column=counter, sticky="nw", padx=2, pady=2)
        stopmusic_button = tk.Button(parent, image=self.stop_icon, relief=tk.FLAT, command=stop_music,
                                     bg=bg)
        stopmusic_button.grid(row=0, column=counter + 1, sticky="nw", padx=2, pady=2)

    def leer_tags(self):
        self.tags = TinyTag.get(self.ruta_archivo)
        self.artists1, self.artists2 = separar_artistas(self.tags.artist)

    def buscar(self):
        tag = self.tags
        self.coincidencia_preferida = 0
        self.hay_coincidencia_preferida = False
        self.tipo_de_coincidencia = 5
        artista_original, cantor_original = separar_artistas(tag.artist)
        # coincide artista
        if unidecode(convert_numbers_to_words(artista_original)).lower() in dic_art:
            dbe = dic_art[unidecode(convert_numbers_to_words(artista_original)).lower()]
            coincide_titulo = coincide(dbe, tag, 'titulo', False)
            # si hay resultados de titulo
            if not coincide_titulo.sum() == 0:
                self.resultado = 'Titulo encontrado'
                self.tipo_de_coincidencia = 0
                dbet = dbe.loc[coincide_titulo]
                coincide_titulo_talcual = coincide(dbe, tag, 'titulo', True)
                # si hay resultados de titulo
                if not coincide_titulo_talcual.sum() == 0:
                    dbet = dbe.loc[coincide_titulo_talcual]
                coincide_ano = coincide(dbet, tag, 'ano', False)
                if not coincide_ano.sum() == 0:
                    resultado = 'Año encontrado'
                    self.tipo_de_coincidencia = 1
                    self.coincidencia_preferida = next((index for index, value in enumerate(coincide_ano) if value),
                                                       None)
                    self.hay_coincidencia_preferida = True
                else:
                    self.resultado = 'Año no encontrado'

            # si no hay resultados de titulo
            else:
                coinciden_palabras = contain_most_words(dbe, tag.title, "titulo_min")
                # si hay coincidencia de palabras
                if coinciden_palabras:
                    resultado = 'Palabras del titulo encontrado'
                    dbet = dbe.loc[coinciden_palabras]
                    self.tipo_de_coincidencia = 3
                    coincide_ano = coincide(dbet, tag, 'ano', False)
                    if not coincide_ano.sum() == 0:
                        resultado = 'Año encontrado'
                        self.tipo_de_coincidencia = 4
                        self.coincidencia_preferida = next((index for index, value in enumerate(coincide_ano) if value),
                                                           None)
                        self.hay_coincidencia_preferida = True
                    else:
                        self.resultado = 'Año no encontrado'
                # si no hay coincidencia de palabras
                else:
                    self.resultado = 'Titulo o palabras del titulo no encontrado'
                    self.tipo_de_coincidencia = 5
                    dbet = db.iloc[0:0]
        else:
            self.resultado = 'Artista no encontrado'
            self.tipo_de_coincidencia = 5
            dbet = db.iloc[0:0]

        if self.tipo_de_coincidencia == 1:
            if coincide(dbet, tag, 'todo', True).sum() == 1:
                dbet = dbet.loc[coincide(dbet, tag, 'todo', True)]
                self.tipo_de_coincidencia = 2
                self.hay_coincidencia_preferida = False

        if (self.tipo_de_coincidencia == 0) & (len(dbet) == 1):
            self.hay_coincidencia_preferida = True
            self.coincidencia_preferida = 0

        self.coincidencias = dbet

    def show_popup_db(self, row):

        tags = self.tags
        # Create a new Toplevel window (popup)
        popup = tk.Toplevel()
        popup.title("Additional Information")
        # popup.geometry("1000x300")

        etiquetas_datos = [["Titulo", row.titulo],
                           ["Orquesta", row.artista],
                           ["Cantor", row.cantor],
                           ["Fecha", row.fecha],
                           ["Estilo", row.estilo],
                           ["Compositor", concaternar_autores(row.compositor, row.autor)]]

        # Create and place the labels in two columns
        for i, (etiqueta, dato) in enumerate(etiquetas_datos):
            # Create label for the tag name
            label_etiqueta = tk.Label(popup, text=etiqueta + ": ", anchor="w", justify="left",
                                      font=("Helvetica", 12, "bold"))
            label_etiqueta.grid(row=i, column=0, padx=5, pady=2, sticky="w")

            # Create label for the tag data
            label_dato = tk.Label(popup, text=dato, anchor="w", justify="left", font=("Helvetica", 12))
            label_dato.grid(row=i, column=1, padx=5, pady=2, sticky="w")

        # Add a button to close the popup
        close_button = tk.Button(popup, text="Close", command=popup.destroy)
        close_button.grid(row=len(etiquetas_datos), column=0, padx=5, pady=2, sticky="w")

    def show_popup_file(self):
        tags = self.tags
        # Create a new Toplevel window (popup)
        popup = tk.Toplevel()
        popup.title("Additional Information")
        popup.geometry("1000x800")  # Adjusted size for the popup

        etiquetas_datos = [
            ["Nombre de archivo", tags._filename],
            ["Titulo", tags.title],
            ["Orquesta", self.artists1],
            ["Cantor", self.artists2],
            ["Fecha", tags.year],
            ["Estilo", tags.genre],
            ["Compositor", tags.composer]
        ]

        # Create and place the labels in two columns
        self.entry_dato_lista = []

        for i, (etiqueta, dato) in enumerate(etiquetas_datos):
            # Create label for the tag name
            label_etiqueta = tk.Label(popup, text=etiqueta + ": ", anchor="w", justify="left",
                                      font=("Helvetica", 12, "bold"))
            label_etiqueta.grid(row=i, column=0, padx=5, pady=2, sticky="w")

            # Ensure dato is a string, or convert it if necessary
            if dato is None:
                dato = ""  # Convert None to an empty string
            elif not isinstance(dato, str):
                dato = str(dato)  # Convert other types to string

            # Create entry for the tag data
            entry_dato = tk.Entry(popup, justify="left", font=("Helvetica", 12), width=100)
            entry_dato.insert(0, dato)  # Insert text into the entry
            entry_dato.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.entry_dato_lista.append(entry_dato)

        # Add a button to close the popup
        close_button = tk.Button(popup, text="Close", command=popup.destroy)
        close_button.grid(row=len(etiquetas_datos), column=0, padx=5, pady=2, sticky="w")

        update_tags_button = tk.Button(popup, text="Update tags", command=lambda: self.leer_entredas_y_tagear(popup))
        update_tags_button.grid(row=len(etiquetas_datos), column=1, padx=5, pady=2, sticky="w")

        # Crear un marco inferior con un color de fondo diferente y borde grueso usando grid
        bottom_frame = tk.Frame(popup, bg="#e0e0e0", bd=5, relief="ridge")
        bottom_frame.grid(row=len(etiquetas_datos) + 1, column=0, columnspan=2, pady=20, padx=10, sticky="nsew")

        # Expandir el bottom_frame al cambiar el tamaño del popup
        popup.grid_rowconfigure(len(etiquetas_datos) + 1, weight=1)
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_columnconfigure(1, weight=1)

        # Encabezado dentro del bottom_frame
        header_label = tk.Label(bottom_frame, text="Base de Datos", font=("Helvetica", 14, "bold"), bg="#e0e0e0")
        header_label.grid(row=0, column=0, columnspan=4, pady=10)

        def searchdb():
            def update_table():
                # Obtener filtros
                title_filter = title_entry.get().lower()
                artist_filter = artist_var.get()
                cantor_filter = cantor_var.get()
                start_date = start_date_entry.get()
                end_date = end_date_entry.get()

                # Filtrar datos
                filtered_db = db[
                    db['titulo'].str.lower().str.contains(title_filter, na=False) &
                    (db['artista'] == artist_filter if artist_filter != 'Todos' else True) &
                    (db['cantor'] == cantor_filter if cantor_filter != 'Todos' else True) &
                    (db['fecha'] >= start_date if start_date else True) &
                    (db['fecha'] <= end_date if end_date else True)
                    ]

                # Limpiar tabla
                for row in table.get_children():
                    table.delete(row)

                # Insertar nuevos datos
                for index, row in filtered_db.iterrows():
                    table.insert('', 'end', values=(row['titulo'], row['artista'], row['cantor'], row['fecha']))

            def update_cantor_dropdown(*args):
                # Filtrar cantores según el artista seleccionado
                selected_artist = artist_var.get()
                if selected_artist == "Todos":
                    filtered_cantors = db['cantor'].dropna().unique().tolist()
                else:
                    filtered_cantors = db[db['artista'] == selected_artist]['cantor'].dropna().unique().tolist()

                # Actualizar el dropdown de cantores
                cantor_var.set("Todos")
                cantor_dropdown['values'] = ['Todos'] + sorted(filtered_cantors)

                # Actualizar la tabla después de cambiar los cantores disponibles
                update_table()

            def on_filter_change(*args):
                update_table()

            # Ajustar el grid dentro del bottom_frame
            bottom_frame.grid_rowconfigure(6, weight=1)
            bottom_frame.grid_columnconfigure(1, weight=1)
            bottom_frame.grid_columnconfigure(3, weight=1)

            # Fuente personalizada
            font_style = ('Helvetica', 12)
            tree_font_style = ('Helvetica', 12)

            # Filtro de Título
            tk.Label(bottom_frame, text="Titulo:", font=font_style, bg="#e0e0e0").grid(row=1, column=0, padx=10,
                                                                                       pady=10, sticky="w")
            title_entry = tk.Entry(bottom_frame, font=font_style)
            title_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
            title_entry.bind("<KeyRelease>", lambda event: update_table())

            # Filtro de Artista
            tk.Label(bottom_frame, text="Artista:", font=font_style, bg="#e0e0e0").grid(row=2, column=0, padx=10,
                                                                                        pady=10, sticky="w")
            artist_var = tk.StringVar(bottom_frame)
            artist_var.set("Todos")
            artist_dropdown = ttk.Combobox(bottom_frame, textvariable=artist_var, font=font_style)
            artist_dropdown['values'] = ['Todos'] + sorted(db['artista'].dropna().unique().tolist())
            artist_dropdown.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
            artist_var.trace("w", update_cantor_dropdown)

            # Filtro de Cantor
            tk.Label(bottom_frame, text="Cantor:", font=font_style, bg="#e0e0e0").grid(row=3, column=0, padx=10,
                                                                                       pady=10, sticky="w")
            cantor_var = tk.StringVar(bottom_frame)
            cantor_var.set("Todos")
            cantor_dropdown = ttk.Combobox(bottom_frame, textvariable=cantor_var, font=font_style)
            cantor_dropdown['values'] = ['Todos'] + sorted(db['cantor'].dropna().unique().tolist())
            cantor_dropdown.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
            cantor_var.trace("w", on_filter_change)

            # Filtro de Fecha
            tk.Label(bottom_frame, text="Fecha desde:", font=font_style, bg="#e0e0e0").grid(row=4, column=0, padx=10,
                                                                                            pady=10, sticky="w")
            start_date_entry = tk.Entry(bottom_frame, font=font_style)
            start_date_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
            start_date_entry.bind("<KeyRelease>", lambda event: update_table())

            tk.Label(bottom_frame, text="Fecha hasta:", font=font_style, bg="#e0e0e0").grid(row=4, column=2, padx=10,
                                                                                            pady=10, sticky="w")
            end_date_entry = tk.Entry(bottom_frame, font=font_style)
            end_date_entry.grid(row=4, column=3, padx=10, pady=10, sticky="ew")
            end_date_entry.bind("<KeyRelease>", lambda event: update_table())

            # Crear canvas para scrollbar
            canvas = tk.Canvas(bottom_frame)
            canvas.grid(row=5, column=0, columnspan=4, sticky='nsew')

            # Scrollbar vertical
            scrollbar = ttk.Scrollbar(bottom_frame, orient="vertical", command=canvas.yview)
            scrollbar.grid(row=5, column=4, sticky='ns')

            # Frame dentro del canvas
            second_frame = tk.Frame(canvas)

            # Configurar scrollbar
            second_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )

            canvas.create_window((0, 0), window=second_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Crear tabla dentro del frame
            columns = ['titulo', 'artista', 'cantor', 'fecha']
            style = ttk.Style()
            style.configure("Treeview", font=tree_font_style, rowheight=25)
            style.configure("Treeview.Heading", font=('Helvetica', 14, 'bold'))

            table = ttk.Treeview(second_frame, columns=columns, show='headings', style="Treeview")
            for col in columns:
                table.heading(col, text=col.capitalize())
                table.column(col, anchor="center", width=150)

            table.pack(fill="both", expand=True)

            # Hacer que el frame que contiene la tabla se expanda
            second_frame.pack(fill="both", expand=True)

            # Llenar la tabla inicialmente
            update_table()

        # Ejecutar el popup de búsqueda de base de datos
        searchdb()

        # Iniciar el loop de tkinter
        popup.mainloop()

    # **********************************************
    # **********************************************
    # **********************************************
    # **********************************************
    # **********************************************

    def leer_entredas_y_tagear(self, popup):

        values = [entry.get() for entry in self.entry_dato_lista]

        artista_nuevo = f'{self.entry_dato_lista[2].get()} / {self.entry_dato_lista[3].get()}'

        etiquetas_actualizadas = [self.tags._filename,
                                  self.entry_dato_lista[1].get(),
                                  artista_nuevo,
                                  self.entry_dato_lista[4].get(),
                                  self.entry_dato_lista[5].get(),
                                  self.entry_dato_lista[6].get()
                                  ]
        update_tags(*etiquetas_actualizadas)
        popup.destroy()

        self.leer_tags()

        self.buscar()

        for archivos in filetofind_list:
            archivos.destroy()

        for archivos in filetofind_list:
            archivos.representar_datos()

    def activar_checkbox(self, valor):
        for i, check in enumerate(self.vars):
            if i != valor:
                check.set(False)
            else:
                check.set(True)

    def on_checkbox_toggle(self, counter):
        for i, check in enumerate(self.vars):
            if i != counter:
                check.set(False)

    def play_music(self, file_path):
        try:
            # Load and play the file
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error playing {file_path}: {e}")

    def destroy(self):
        # Destroy all widgets within this object's frame
        self.frame_coincidencias.destroy()
        self.frame_archivo.destroy()


class Ventana:
    def __init__(self, root):

        self.root = root
        # Create the main window
        self.root.title("Tkinter Window with Menu, Icon, and Status Bar")
        # Set the window to full-screen mode
        self.root.state('zoomed')
        self.presentation_window = None  # Track the presentation window

        # Create a menu bar
        self.menubar = tk.Menu(root)
        self.root.config(menu=self.menubar)

        # Create a 'File' menu and add it to the menu bar
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New")
        self.file_menu.add_command(label="Open")
        self.file_menu.add_command(label="Save")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)

        # Create an 'Edit' menu and add it to the menu bar
        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Undo")
        self.edit_menu.add_command(label="Redo")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut")
        self.edit_menu.add_command(label="Copy")
        self.edit_menu.add_command(label="Paste")

        # Create an icon bar
        self.icon_bar = tk.Frame(root, relief=tk.RAISED, bd=2)
        self.icon_bar.grid(row=0, column=0, columnspan=3, sticky="ew")

        self.new_icon = tk.PhotoImage(file=icono_archivo)
        self.open_icon = tk.PhotoImage(file=icono_directorio)
        self.save_icon = tk.PhotoImage(file=icono_correr)
        self.transfer_icon = tk.PhotoImage(file=icono_transfer)
        self.trash_icon = tk.PhotoImage(file=icono_trash)
        self.searchdb_icon = tk.PhotoImage(file=icono_searchdb)
        self.presentation_icon = tk.PhotoImage(file=icono_presentacion)
        self.playlist_icon = tk.PhotoImage(file=icono_playlist)

        self.load_button_music_file = tk.Button(self.icon_bar, image=self.new_icon, relief=tk.FLAT,
                                                command=self.load_music_file)
        self.load_button_music_file.grid(row=0, column=0, padx=2, pady=2)
        self.load_button_music_folder = tk.Button(self.icon_bar, image=self.open_icon, relief=tk.FLAT,
                                                  command=self.load_music_folder)
        self.load_button_music_folder.grid(row=0, column=1, padx=2, pady=2)
        self.save_button = tk.Button(self.icon_bar, image=self.save_icon, relief=tk.FLAT)
        self.save_button.grid(row=0, column=2, padx=2, pady=2)
        self.transfer_button = tk.Button(self.icon_bar, image=self.transfer_icon, relief=tk.FLAT,
                                         command=self.aplicartags)
        self.transfer_button.grid(row=0, column=3, padx=2, pady=2)
        self.trash_button = tk.Button(self.icon_bar, image=self.trash_icon, relief=tk.FLAT, command=self.borrar_todo)
        self.trash_button.grid(row=0, column=4, padx=2, pady=2)
        self.trash_button = tk.Button(self.icon_bar, image=self.searchdb_icon, relief=tk.FLAT, command=self.searchdb)
        self.trash_button.grid(row=0, column=5, padx=2, pady=2)
        self.presentation_button = tk.Button(self.icon_bar, image=self.presentation_icon, relief=tk.FLAT,
                                             command=self.open_presentation_popup)
        self.presentation_button.grid(row=0, column=6, padx=2, pady=2)
        self.playlist_button = tk.Button(self.icon_bar, image=self.playlist_icon, relief=tk.FLAT,
                                         command=self.open_playlist)
        self.playlist_button.grid(row=0, column=7, padx=2, pady=2)

        # Create a main content area
        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # Create a canvas widget
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Add a vertical scrollbar to the canvas
        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Configure the canvas to use the scrollbar
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Create a frame inside the canvas to hold the main content
        self.main_content = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.main_content, anchor="nw")

        # Bind the canvas to update its scroll region whenever the main_content frame changes size
        self.main_content.bind("<Configure>", self.on_frame_configure)

        # Make the canvas expandable
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Bind mousewheel scrolling to the canvas
        self.root.bind_all("<MouseWheel>", self._on_mouse_wheel)

        # Create the first subframe
        self.subframe1 = tk.Frame(self.main_content, bg='white', bd=1, relief="ridge")
        self.subframe1.grid(row=0, column=0, sticky="nsew")

        # Create the second subframe
        self.subframe2 = tk.Frame(self.main_content, bg='white', bd=1, relief="ridge")
        self.subframe2.grid(row=0, column=1, sticky="nsew")

        # Configure grid weights to ensure subframes take up half of the main frame

        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(1, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)

        # Create a status bar
        self.status_bar = tk.Label(root, text="Status: Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, columnspan=3, sticky="ew")

        # Configure grid weights to make the main content expandable
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Start the Tkinter event loop
        self.root.mainloop()

    def open_presentation_popup(self):
        if self.presentation_window is None or not tk.Toplevel.winfo_exists(self.presentation_window):
            self.presentation_window = tk.Toplevel(self.root)
            self.presentation_window.title("Create Presentation")
            app = PresentationApp(self.presentation_window)
        else:
            self.presentation_window.lift()

    def searchdb(self):
        def update_table():
            # Obtener filtros
            title_filter = title_entry.get().lower()
            artist_filter = artist_var.get()
            cantor_filter = cantor_var.get()
            start_date = start_date_entry.get()
            end_date = end_date_entry.get()

            # Filtrar datos
            filtered_db = db[
                db['titulo'].str.lower().str.contains(title_filter, na=False) &
                (db['artista'] == artist_filter if artist_filter != 'Todos' else True) &
                (db['cantor'] == cantor_filter if cantor_filter != 'Todos' else True) &
                (db['fecha'] >= start_date if start_date else True) &
                (db['fecha'] <= end_date if end_date else True)
                ]

            # Limpiar tabla
            for row in table.get_children():
                table.delete(row)

            # Insertar nuevos datos
            for index, row in filtered_db.iterrows():
                table.insert('', 'end', values=(row['titulo'], row['artista'], row['cantor'], row['fecha']))

        def update_cantor_dropdown(*args):
            # Filtrar cantores según el artista seleccionado
            selected_artist = artist_var.get()
            if selected_artist == "Todos":
                filtered_cantors = db['cantor'].dropna().unique().tolist()
            else:
                filtered_cantors = db[db['artista'] == selected_artist]['cantor'].dropna().unique().tolist()

            # Actualizar el dropdown de cantores
            cantor_var.set("Todos")
            cantor_dropdown['values'] = ['Todos'] + sorted(filtered_cantors)

            # Actualizar la tabla después de cambiar los cantores disponibles
            update_table()

        def on_filter_change(*args):
            update_table()

        # Crear ventana emergente
        popup = tk.Toplevel(self.root)
        popup.title("Search Database")
        popup.geometry("800x400")  # Tamaño inicial de la ventana

        # Ajustar el grid para expandirse
        popup.grid_rowconfigure(4, weight=1)
        popup.grid_columnconfigure(1, weight=1)
        popup.grid_columnconfigure(3, weight=1)

        # Fuente personalizada
        font_style = ('Helvetica', 12)
        tree_font_style = ('Helvetica', 12)

        # Filtro de Título
        tk.Label(popup, text="Titulo:", font=font_style).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        title_entry = tk.Entry(popup, font=font_style)
        title_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        title_entry.bind("<KeyRelease>", lambda event: update_table())

        # Filtro de Artista
        tk.Label(popup, text="Artista:", font=font_style).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        artist_var = tk.StringVar(popup)
        artist_var.set("Todos")
        artist_dropdown = ttk.Combobox(popup, textvariable=artist_var, font=font_style)
        artist_dropdown['values'] = ['Todos'] + sorted(db['artista'].dropna().unique().tolist())
        artist_dropdown.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        artist_var.trace("w", update_cantor_dropdown)

        # Filtro de Cantor
        tk.Label(popup, text="Cantor:", font=font_style).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        cantor_var = tk.StringVar(popup)
        cantor_var.set("Todos")
        cantor_dropdown = ttk.Combobox(popup, textvariable=cantor_var, font=font_style)
        cantor_dropdown['values'] = ['Todos'] + sorted(db['cantor'].dropna().unique().tolist())
        cantor_dropdown.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        cantor_var.trace("w", on_filter_change)

        # Filtro de Fecha
        tk.Label(popup, text="Fecha desde:", font=font_style).grid(row=3, column=0, padx=10, pady=10, sticky="w")
        start_date_entry = tk.Entry(popup, font=font_style)
        start_date_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        start_date_entry.bind("<KeyRelease>", lambda event: update_table())

        tk.Label(popup, text="Fecha hasta:", font=font_style).grid(row=3, column=2, padx=10, pady=10, sticky="w")
        end_date_entry = tk.Entry(popup, font=font_style)
        end_date_entry.grid(row=3, column=3, padx=10, pady=10, sticky="ew")
        end_date_entry.bind("<KeyRelease>", lambda event: update_table())

        # Crear canvas para scrollbar
        canvas = tk.Canvas(popup)
        canvas.grid(row=4, column=0, columnspan=4, sticky='nsew')

        # Scrollbar vertical
        scrollbar = ttk.Scrollbar(popup, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=4, column=4, sticky='ns')

        # Frame dentro del canvas
        second_frame = tk.Frame(canvas)

        # Configurar scrollbar
        second_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=second_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Crear tabla dentro del frame
        columns = ['titulo', 'artista', 'cantor', 'fecha']
        style = ttk.Style()
        style.configure("Treeview", font=tree_font_style, rowheight=25)
        style.configure("Treeview.Heading", font=('Helvetica', 14, 'bold'))

        table = ttk.Treeview(second_frame, columns=columns, show='headings', style="Treeview")
        for col in columns:
            table.heading(col, text=col.capitalize())
            table.column(col, anchor="center", width=150)

        table.pack(fill="both", expand=True)

        # Hacer que el frame que contiene la tabla se expanda
        second_frame.pack(fill="both", expand=True)

        # Llenar la tabla inicialmente
        update_table()

        # Iniciar el loop de tkinter
        popup.mainloop()

    # AQUI EMPIEZA LO MIO
    # AQUI EMPIEZA LO MIO
    # AQUI EMPIEZA LO MIO
    def on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mouse_wheel(self, event):
        """Scroll the canvas with the mouse wheel."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_music_file(self):
        global numero_canciones
        file_path = filedialog.askopenfilename(
            filetypes=[("MUSIC files", ".mp3 .wav .flac .ogg .m4a"), ("All files", "*.*")]
        )
        if file_path:
            # try:
            new_filetofind = FILETOFIND(self.subframe1, self.subframe2, file_path, numero_canciones)
            numero_canciones += 1
            filetofind_list.append(new_filetofind)
            # except Exception as error:
            #     messagebox.showerror("Error", f"Error al leer el archivo musica:\n{error}")

    def open_playlist(self):
        numero_canciones = 0
        # Open file dialog
        self.m3u_file_path = filedialog.askopenfilename(
            initialdir=m3u_start_path,
            filetypes=[("M3U files", "*.m3u"), ("All files", "*.*")]
        )

        if self.m3u_file_path:
            # Clear previous data
            if hasattr(self, 'df'):
                self.m3u_db = self.m3u_db.iloc[0:0]  # Clear the DataFrame but keep the columns

            self.m3u_audio_files = []  # Clear the audio files list
            # self.m3u_audio_tags = []  # Clear the audio tags list

            # Load the M3U file and extract data
            with open(self.m3u_file_path, 'r', encoding='utf-8') as file:

                for line in file:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if os.path.exists(line):
                            new_filetofind = FILETOFIND(self.subframe1, self.subframe2, line,
                                                        numero_canciones)
                            numero_canciones += 1
                            filetofind_list.append(new_filetofind)
                        else:
                            modified_path = dropbox_path + line.split("Dropbox", 1)[1]
                            if os.path.exists(modified_path):
                                new_filetofind = FILETOFIND(self.subframe1, self.subframe2, modified_path,
                                                            numero_canciones)
                                numero_canciones += 1
                                filetofind_list.append(new_filetofind)
                                # self.m3u_audio_files.append(modified_path)
                                # tags = self.read_audio_tags(modified_path)
                                # self.m3u_audio_tags.append(tags)

    def load_music_folder(self):
        folder_path = filedialog.askdirectory()
        numero_canciones = 0
        # Loop through all files in the folder
        # Create a Label for the status text
        self.status_label = tk.Label(self.status_bar, text="Progress: 0%", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT)

        # Create a Progressbar widget
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(self.status_bar, variable=self.progress_var, maximum=100, length=150)
        self.progress_bar.pack(side=tk.RIGHT, padx=10)
        contador_canciones = 0

        for filename in os.listdir(folder_path):
            self.update_progress(100 * contador_canciones / len(os.listdir(folder_path)))
            contador_canciones += 1
            if contador_canciones % 10 == 0:
                root.update()
            if filename.endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):  # Add more extensions as needed
                file_path = os.path.join(folder_path, filename)
                if file_path:
                    # try:
                    new_filetofind = FILETOFIND(self.subframe1, self.subframe2, file_path, numero_canciones)
                    numero_canciones += 1
                    filetofind_list.append(new_filetofind)
                    # except Exception as error:
                    #     messagebox.showerror("Error", f"Error al leer el archivo musica:\n{error}")
        self.progress_bar.pack_forget()
        self.status_label.pack_forget()

    def aplicartags(self):
        reemplazo_tags = []
        for archivos in filetofind_list:
            for index, check in enumerate(archivos.vars):
                if check.get():
                    update_tags(archivos.ruta_archivo, title=archivos.coincidencias.titulo.iloc[index],
                                artist=f'{archivos.coincidencias.artista.iloc[index]} / {archivos.coincidencias.cantor.iloc[index]}',
                                year=archivos.coincidencias.fecha.iloc[index],
                                genre=archivos.coincidencias.estilo.iloc[index],
                                composer=archivos.coincidencias.compositor_autor.iloc[index])

                    reemplazo_tags_linea = {
                        'archivo': archivos.ruta_archivo,
                        'old_title': archivos.tags.title,
                        'new_title': archivos.coincidencias.titulo.iloc[index],
                        'old_artist': archivos.artists1,
                        'new_artist': archivos.coincidencias.artista.iloc[index],
                        'old_cantor': archivos.artists2,
                        'new_cantor': archivos.coincidencias.cantor.iloc[index],
                        'old_year': archivos.tags.year,
                        'new_year': archivos.coincidencias.fecha.iloc[index],
                        'old_genre': archivos.tags.genre,
                        'new_genre': archivos.coincidencias.estilo.iloc[index],
                        'old_composer': archivos.tags.composer,
                        'new_composer': archivos.coincidencias.compositor_autor.iloc[index]
                    }
                    reemplazo_tags.append(reemplazo_tags_linea)
        reemplazo_tags_df = pd.DataFrame(reemplazo_tags)

        # Get the current date and time
        now = datetime.now()

        # Format the date and time to include in the filename
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        filename = f'{archivotest}_{timestamp}.csv'
        reemplazo_tags_df.to_csv(filename, index=False, sep=';')

    def borrar_todo(self):
        for archivos in filetofind_list:
            archivos.destroy()
        filetofind_list.clear()

    def update_progress(self, value):
        self.progress_var.set(int(value))
        self.status_label.config(text=f"Progress: {int(value)}%")


if __name__ == "__main__":
    # try:
    db = pd.read_csv(os.path.join(data_folder, "db.csv"), encoding="utf-8", sep=";")

    # db = pd.read_csv(csv_grabaciones, encoding="utf-8", sep=";")
    # quitar los valores ' (2)', ' (3)', ' (4)', ' (5)', ' (b)', ' (c)' del titulo
    # quitar_de_titulos = [' (2)', ' (3)', ' (4)', ' (5)', ' (b)', ' (c)']
    # for palabra in quitar_de_titulos:
    #     db['titulo'] = db['titulo'].str.replace(palabra, "", regex=False)
    #
    # # poner estilos Tango, Tango Milonga, Tango Vals.
    # replacements = [
    #     ('TANGO', 'tango'),
    #     ('VALS', 'tango vals'),
    #     ('MILONGA', 'tango milonga')
    # ]
    # replacement_dict = dict(replacements)
    # db['estilo'] = db['estilo'].replace(replacement_dict)
    # db['estilo'] = db['estilo'].apply(lambda x: x.lower())
    #
    # # reemplazar los nan con cadenas vacias
    # db = db.fillna("")
    #
    # # crear una nueva columna con compositor y autor juntos
    # db['compositor_autor'] = db.apply(
    #     lambda row: concaternar_autores(row['compositor'], row['autor']), axis=1)
    #
    # # Cambiar el formato de fecha de DD/MM/YYYY a YYYY-MM-DD o YYYY-MM o YYYY
    # db['fecha'] = db['fecha'].apply(convert_date_format)
    #
    # # crear una columna con solo el año
    # db['fecha_ano'] = db['fecha'].apply(extract_year)
    #
    # # Quitar todo el apellido en mayusculas
    # db['artista'] = db['artista'].apply(capitalize_uppercase_words)
    #
    # # CONVERTIR LOS NUMEROS A STRINGS Y QUITAR MAYUSCULAS Y ACENTOS
    # db['titulo_min'] = db['titulo'].apply(lambda x: convert_numbers_to_words(x) if pd.notna(x) else x)
    # db['artista_min'] = db['artista'].apply(lambda x: convert_numbers_to_words(x) if pd.notna(x) else x)
    # db['cantor_min'] = db['cantor'].apply(lambda x: convert_numbers_to_words(x) if pd.notna(x) else x)
    #
    # # palabras_mas_comunes(db,'artista_min')
    # db.to_csv(os.path.join(data_folder, "db.csv"),index=False,sep=';')

    dic_art = {}
    lista_artistas = db['artista_min'].unique()
    for artista in lista_artistas:
        filtered_df = db[db['artista_min'] == artista]
        dic_art[artista] = filtered_df

    # except Exception as e:
    #     messagebox.showerror("Error", f"Error al leer el archivo CSV:\n{e}")
    # # Initialize Pygame mixer
    pygame.mixer.init()
    root = tk.Tk()
    app = Ventana(root)
    root.mainloop()
