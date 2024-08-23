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
from config import *
from utils import extract_year, separar_artistas

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
