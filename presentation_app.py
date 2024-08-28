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
from unidecode import unidecode
import os
from os.path import join
from src.config.config import dropbox_path, image_folder, m3u_start_path, background_image_path, data_folder, output_folder, orchestra_folder, background_image_folder, merged_images_folder, DEFAULT_FONT_NAME
from src.utils.utils import extract_year, separar_artistas, obtener_autores
from src.utils.funciones_para_diapos import *
# add_text_to_slide, calculate_positions, adjust_text_size
class PresentationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Presentation Creator")
        self.root.state('zoomed')
        # Set the window to be on top
        # self.root.attributes('-topmost', True)
        # self.root.after_idle(lambda: self.root.attributes('-topmost', False))  # Allow interaction with other windows

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
        self.nombre_milonga_entry.insert(0, "Milonga de la Fuente")

        tk.Label(root, text="Fecha:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.fecha_entry = tk.Entry(root, width=50)
        self.fecha_entry.grid(row=1, column=1, padx=10, pady=10)
        self.fecha_entry.insert(0, "24 de Agosto de 2024")

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
        # self.root.attributes('-topmost', False)

        # Open file dialog
        self.m3u_file_path = filedialog.askopenfilename(
            initialdir=m3u_start_path,
            filetypes=[("M3U files", "*.m3u"), ("All files", "*.*")]
        )

        # # Return focus to the popup window
        # self.root.attributes('-topmost', True)

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

        # #orchestra = PilImage.open(self.orchestra_path).convert("RGBA")
        #
        # maximum_in_width = 0.4 * base.width
        # maximum_in_height = base.height
        #
        # resize_factor = maximum_in_height / orchestra.height
        #
        # if (resize_factor * orchestra.width) > maximum_in_width:
        #     resize_factor = maximum_in_width / orchestra.width
        #
        # new_width = int(orchestra.width * resize_factor)
        # new_height = int(orchestra.height * resize_factor)
        #
        # # Resize the orchestra image
        # orchestra = orchestra.resize((new_width, new_height), PilImage.Resampling.LANCZOS)

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
        # position = (0, combined.height - orchestra.height)  # Centering
        # combined.paste(orchestra, position, orchestra)  # The third argument is the mask to maintain transparency

        # Save the gradient and the combined image
        # gradient_rgba.save(self.path_gradiente, "PNG")
        # self.merged_image_path = join(image_folder, "merged_background.png")

        self.merged_image_path = join(background_image_folder, "background_tango_degradado.png")

        combined.save(self.merged_image_path, "PNG")

    def create_slide_for_tanda(self, prs, tanda_number, titulo, subtitulo, genero, lista_canciones, positions_initial):

        # self.apply_gradient_overlay()

        # Titulo cortina, Artista cortina, Orquesta tango, Firma DJ, Estilo y Cantores, Canciones, años, autores
        fuentes = [100, 50, 55, 35, 20, 50, 20, 12]

         # NAME OF THE ORCHESTRA
        orchestra_value = titulo
        orchestra_value_min = unidecode(orchestra_value).lower()
        self.tanda_gender = genero
        lista_canciones = lista_canciones

        # Determine the background image based on genre
        if 'tango' not in self.tanda_gender:
            self.merged_image_path = join(background_image_folder, "background_cortina.png")
        else:
            # self.merged_image_path = join(merged_images_folder, f'{orchestra_value_min}_background.png')
            self.merged_image_path = join(background_image_folder, "background_tango_degradado.png")

        # Add a slide with a title and content layout
        slide_layout = prs.slide_layouts[5]  # Use a blank layout
        slide = prs.slides.add_slide(slide_layout)

        # Set the merged background image with gradient
        slide.shapes.add_picture(self.merged_image_path, 0, 0, width=prs.slide_width, height=prs.slide_height)


        img_path = join(image_folder, 'orquestas', f'{orchestra_value_min}.png')

        if os.path.exists(img_path):
            add_resized_image_to_slide(slide,img_path, positions_initial["maxima_anchura_image"], prs)

        positions_calculated = calculate_positions(prs, positions_initial)


        if 'tango' not in self.tanda_gender:
            title, year, composer = lista_canciones[0]

            cortina_title = slide.shapes.add_textbox(positions_calculated["cortina_title"][0],
                                                     positions_calculated["cortina_title"][1],
                                                     positions_calculated["cortina_title"][2],
                                                     positions_calculated["cortina_title"][3])
            title_frame = cortina_title.text_frame
            title_frame.clear()

            title_paragraph1 = title_frame.paragraphs[0]
            run_orquesta = title_paragraph1.add_run()
            run_orquesta.text = f'{orchestra_value}'
            run_orquesta.font.size = Pt(fuentes[0])
            run_orquesta.font.color.rgb = RGBColor(255, 255, 255)
            run_orquesta.font.bold = True
            run_orquesta.font.name = DEFAULT_FONT_NAME  # Aplicar la fuente desde config.py

            # Ajustar el tamaño del texto según el ancho y altura disponibles
            adjust_text_size(title_frame,
                             max_width_cm=positions_calculated["cortina_title"][2],
                             max_font_size=fuentes[0], fuente=DEFAULT_FONT_NAME)

            cortina_subtitle = slide.shapes.add_textbox(positions_calculated["cortina_subtitle"][0],
                                                        positions_calculated["cortina_subtitle"][1],
                                                        positions_calculated["cortina_subtitle"][2],
                                                        positions_calculated["cortina_subtitle"][3])
            text_frame = cortina_subtitle.text_frame
            text_frame.clear()

            paragraph1 = text_frame.paragraphs[0]
            run_titulo = paragraph1.add_run()
            run_titulo.text = title
            run_titulo.font.size = Pt(fuentes[1])
            run_titulo.font.color.rgb = RGBColor(255, 255, 255)
            run_titulo.font.bold = True
            run_titulo.font.name = DEFAULT_FONT_NAME  # Aplicar la fuente desde config.py

            run_fecha = paragraph1.add_run()
            run_fecha.text = f'   ({year})'
            run_fecha.font.color.rgb = RGBColor(255, 255, 255)
            run_fecha.font.name = DEFAULT_FONT_NAME  # Aplicar la fuente desde config.py

            # Ajustar el tamaño del texto según el ancho y altura disponibles
            adjust_text_size(text_frame,
                             max_width_cm=positions_calculated["cortina_subtitle"][2],
                             max_font_size=fuentes[1], fuente=DEFAULT_FONT_NAME)

        else:
            initial_text = '' if orchestra_value.startswith("Orquesta") else 'Orquesta de '
            full_text = f'{initial_text}{orchestra_value}'

            add_text_to_slide(
                slide,
                full_text,
                positions_calculated["tanda_orquesta_shadow"],
                positions_calculated["offset_shadow"],
                fuentes[2],
                DEFAULT_FONT_NAME,
                (255, 255, 255),  # Color blanco
                True,  # Negrita activada
                True  # Sombra activada
            )

            add_text_to_slide(
                slide,
                subtitulo,
                positions_calculated["tanda_cantor_shadow"],
                positions_calculated["offset_shadow"],
                fuentes[3],
                DEFAULT_FONT_NAME,
                (255, 255, 255),  # Color blanco
                True,  # Negrita activada
                True  # Sombra activada
            )

            add_text_to_slide(
                slide,
                f'© TDJ Edmundo Fraga\n{self.nombre_milonga_entry.get()}\n{self.fecha_entry.get()}',
                positions_calculated["firma_tgdj_box"],
                positions_calculated["offset_shadow"],
                fuentes[4],
                DEFAULT_FONT_NAME,
                (255, 255, 255),  # Color blanco
                False,  # Negrita activada
                True,  # Sombra activada
                border_color_rgb = (0, 0, 0),
                border_width_pt = 2
            )

            linea_divisoria = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                                         positions_calculated["linea_divisoria"][0],
                                                         positions_calculated["linea_divisoria"][1],
                                                         positions_calculated["linea_divisoria"][0] +
                                                         positions_calculated["linea_divisoria"][2],
                                                         positions_calculated["linea_divisoria"][1] +
                                                         positions_calculated["linea_divisoria"][3])
            linea_divisoria.line.color.rgb = RGBColor(255, 255, 255)
            linea_divisoria.line.width = Pt(7)

            for rows in lista_canciones:
                title, year, composer = rows

                add_text_to_slide(
                    slide,
                    title,
                    positions_calculated["canciones_start"],
                    positions_calculated["offset_shadow"],
                    fuentes[5],
                    'Bernard MT Condensed',
                    (255, 255, 255),  # Color blanco
                    False,  # Negrita activada
                    True,  # Sombra activada
                    extra_paragraph_text = composer,
                    extra_run_text = f'   ({year})',
                    extra_paragraph_settings ={'font_name':DEFAULT_FONT_NAME, 'tamano_fuente':fuentes[7], 'font_color_rgb':RGBColor(255, 255, 255), 'is_bold':False, 'is_italic':False},
                    extra_run_settings = {'font_name':DEFAULT_FONT_NAME, 'tamano_fuente':fuentes[6], 'font_color_rgb':RGBColor(255, 255, 255), 'is_bold':False, 'is_italic':False},
                )

                positions_calculated["canciones_start"][1] = positions_calculated["canciones_start"][1] + positions_calculated["canciones_start"][4]


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
            titulo = self.result.iloc[tanda_number - 1]['orchestra_value']
            subtitulo = ''
            genero = self.tanda_gender = self.result.iloc[tanda_number - 1]['unique_value']
            autores = obtener_autores(self.canciones_tanda(tanda_number, ['artist2']))
            if 'vals' in genero:
                subtitulo = "Vals "
                if autores == 'instrumental':
                    subtitulo = subtitulo + 'instrumental'
                else:
                    subtitulo = subtitulo + 'con ' + autores
            elif 'milonga' in genero:
                subtitulo = "Milonga "
                if autores == 'instrumental':
                    subtitulo = subtitulo + 'instrumental'
                else:
                    subtitulo = subtitulo + 'con ' + autores
            else:
                if autores == 'instrumental':
                    subtitulo = 'Instrumental'
                else:
                    subtitulo = subtitulo + 'Con ' + autores

            canciones = self.canciones_tanda(tanda_number, ['title', 'ano', 'composer'])

            positions_initial = {
                "cortina_title": {"left": Cm(5), "top": Cm(5), "right": Cm(1), "height": Cm(5)},
                "cortina_subtitle": {"left": Cm(8), "top": Cm(10), "right": Cm(1), "height": Cm(5)},
                "tanda_orquesta_shadow": {"left": Cm(1.6), "top": Cm(0), "right": Cm(1), "height": Cm(3)},
                "tanda_cantor_shadow": {"left": Cm(3), "top": Cm(2.3), "right": Cm(1), "height": Cm(2)},
                "firma_tgdj_box": {"left": Cm(1), "top": Cm(15.5), "right": Cm(24), "height": Cm(2.8)},
                "linea_divisoria": {"left": Cm(13.5), "top": Cm(4.5), "right": Cm(1), "height": Cm(0)},
                "canciones_start": {"left": Cm(13.5), "top": Cm(4.5), "right": Cm(1), "height": Cm(3), "spacing": Cm(2.5)},
                "offset_shadow": Cm(0.05),
                "maxima_anchura_image": 1
        }

            self.create_slide_for_tanda(prs, tanda_number, titulo, subtitulo, genero, canciones, positions_initial)

        # Save the presentation
        try:
            prs.save(output_file)
            os.startfile(output_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save the presentation:\n{e}")
