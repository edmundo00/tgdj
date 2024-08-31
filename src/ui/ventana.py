import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime
from presentation_app import PresentationApp
from src.ui.file_to_find import FILETOFIND
from src.utils.utils import *
from src.config.database import Database
import src.config.config as config
from src.config.config import columnas_config

import tkinter as tk

class Ventana:
    def __init__(self, root):
        self.data_store = Database()
        self.root = root

        # Inicializar los diccionarios para almacenar los frames de columnas
        self.frames_columnas_archivo = {}
        self.frames_columnas_resultado = {}


        self.root.title("Tkinter Window with Menu, Icon, and Status Bar")
        self.root.geometry('1500x800')

        # Setup layout configurations
        self.layout_configurations()

        # Create UI components
        self.create_menu_bar()
        self.create_icon_bar()
        self.create_title_frame()
        self.create_main_content_area()
        self.create_status_bar()  # Ensure this is called to add the status bar

        # Start the event loop
        self.root.mainloop()

    def layout_configurations(self):
        """Define the layout configurations for the main window."""
        self.root.grid_columnconfigure(0, weight=1)  # Expand the main column
        self.root.grid_rowconfigure(0, weight=0)  # Icon bar row
        self.root.grid_rowconfigure(1, weight=0)  # Title frame row
        self.root.grid_rowconfigure(2, weight=1)  # Main content area should expand
        self.root.grid_rowconfigure(3, weight=0)  # Status bar row

        # Specific configuration for each section's position
        self.icon_bar_row = 0
        self.icon_bar_colspan = 3
        self.title_frame_row = 1
        self.title_frame_colspan = 3
        self.main_content_row = 2
        self.main_content_colspan = 3
        self.status_bar_row = 3
        self.status_bar_colspan = 3

    def create_menu_bar(self):
        """Create the menu bar at the top of the window."""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # File menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New")
        self.file_menu.add_command(label="Open")
        self.file_menu.add_command(label="Save")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit menu
        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Undo")
        self.edit_menu.add_command(label="Redo")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut")
        self.edit_menu.add_command(label="Copy")
        self.edit_menu.add_command(label="Paste")

    def create_icon_bar(self):
        """Create the icon bar with buttons below the menu bar."""
        self.icon_bar = tk.Frame(self.root, relief=tk.RAISED, bd=2)
        self.icon_bar.grid(row=self.icon_bar_row, column=0, columnspan=self.icon_bar_colspan, sticky="ew")

        # Define icons and their commands
        icon_names = ['archivo', 'directorio', 'correr', 'transfer', 'trash', 'searchdb', 'presentacion', 'playlist',
                      'convert_playlist']
        for icon_name in icon_names:
            setattr(self, f"{icon_name}_icon", tk.PhotoImage(file=icon_paths[icon_name]))

        # Button definitions and grid placement
        buttons = [
            (self.archivo_icon, self.load_music_file),
            (self.directorio_icon, self.load_music_folder),
            (self.correr_icon, None),
            (self.transfer_icon, self.aplicartags),
            (self.trash_icon, self.borrar_todo),
            (self.searchdb_icon, self.searchdb),
            (self.presentacion_icon, self.open_presentation_popup),
            (self.playlist_icon, self.open_playlist),
            (self.convert_playlist_icon, self.convert_playlist),
        ]

        for i, (icon, command) in enumerate(buttons):
            btn = tk.Button(self.icon_bar, image=icon, relief=tk.FLAT, command=command)
            btn.grid(row=0, column=i, padx=2, pady=2)

    def create_title_frame(self):
        """Create the title frame with 'File Tags' and 'Database Tags' labels."""
        self.title_frame = tk.Frame(self.root, relief=tk.RAISED, bd=2)
        self.title_frame.grid(row=self.title_frame_row, column=0, columnspan=self.title_frame_colspan, sticky="ew")
        self.title_frame.grid_propagate(True)  # Allow resizing to content

        # Set weights and minsize explicitly for the title columns
        self.title_frame.grid_columnconfigure(0, weight=47, minsize=200)  # Control size for "File Tags"
        self.title_frame.grid_columnconfigure(1, weight=53, minsize=200)  # Control size for "Database Tags"
        self.title_frame.grid_columnconfigure(2, weight=0, minsize=30)  # Dummy space to account for scrollbar width

        # Create the labels
        file_tags_label = tk.Label(
            self.title_frame,
            text="File Tags",
            font=('Consolas', 12, 'bold'),
            bg='lightblue',
            relief=tk.SOLID,
            bd=1
        )
        file_tags_label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        database_tags_label = tk.Label(
            self.title_frame,
            text="Database Tags",
            font=('Consolas', 12, 'bold'),
            bg='lightblue',
            relief=tk.SOLID,
            bd=1
        )
        database_tags_label.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    def create_main_content_area(self):
        """Create the main content area with two subframes occupying all available space."""
        # Crear el contenedor principal para los subframes
        self.main_content = tk.Frame(self.root, bg='yellow')  # Color de fondo del main_content
        self.main_content.grid(row=self.main_content_row, column=0, columnspan=self.main_content_colspan, sticky="nsew")

        # Configuración para expandir el main_content
        self.main_content.grid_rowconfigure(0, weight=1)  # Permitir que la fila se expanda
        self.main_content.grid_columnconfigure(0, weight=1)  # Ajuste proporcional para el primer subframe
        self.main_content.grid_columnconfigure(1, weight=1)  # Ajuste proporcional para el segundo subframe

        # Crear los subframes
        self.create_subframes()

    def create_subframes(self):
        """Create subframes inside the main content area, ensuring they resize with the window."""
        # Crear el primer subframe con expansión completa
        self.subframe1 = tk.Frame(self.main_content, relief=tk.RAISED, bd=2, bg='lightblue')  # Color para subframe1
        self.subframe1.grid(row=0, column=0, sticky="nsew")  # Asegurar que se expanda correctamente

        # Asegurar que el subframe1 se expanda correctamente
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)

        # Crear fila fija de títulos para subframe1
        self.crear_titulos(self.subframe1, columnas_config['archivo'])

        # Crear área desplazable para los datos en subframe1 y asignar 'canvas1' como atributo
        scrollable_frame1 = self.create_scrollable_area(self.subframe1, 'canvas1', bg='lightgreen')

        # Crear frames dentro de subframe1 que correspondan con la configuración de 'archivo'
        self.crear_frames_en_columnas(self.subframe1, columnas_config['archivo'], scrollable_frame1,
                                      self.frames_columnas_archivo)

        # Crear el segundo subframe con expansión completa
        self.subframe2 = tk.Frame(self.main_content, relief=tk.RAISED, bd=2, bg='lightcoral')  # Color para subframe2
        self.subframe2.grid(row=0, column=1, sticky="nsew")  # Asegurar que se expanda correctamente

        # Asegurar que el subframe2 se expanda correctamente
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(1, weight=1)

        # Crear fila fija de títulos para subframe2
        self.crear_titulos(self.subframe2, columnas_config['resultado'])

        # Crear área desplazable para los datos en subframe2 y asignar 'canvas2' como atributo
        scrollable_frame2 = self.create_scrollable_area(self.subframe2, 'canvas2', bg='lightyellow')

        # Crear frames dentro de subframe2 que correspondan con la configuración de 'resultado'
        self.crear_frames_en_columnas(self.subframe2, columnas_config['resultado'], scrollable_frame2,
                                      self.frames_columnas_resultado)

    def update_scroll_region(self, event=None):
        """Actualizar la región de desplazamiento del canvas para incluir todo el contenido de main_content."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mouse_wheel(self, event):
        """Maneja el desplazamiento con la rueda del ratón en ambos canvas."""
        # Verifica que ambos canvas existan antes de intentar desplazarlos
        if hasattr(self, 'canvas1') and hasattr(self, 'canvas2'):
            self.canvas1.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self.canvas2.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def configurar_columnas(self, subframe, config):
        """Configura las columnas de un subframe según la configuración proporcionada."""
        for col_config in config:
            subframe.grid_columnconfigure(col_config['col'], weight=col_config['weight'], minsize=col_config['minsize'])

    def crear_titulos(self, subframe, config):
        """
        Crea una fila de títulos fija en la parte superior del subframe.
        """
        titulo_frame = tk.Frame(subframe, relief=tk.RAISED, bd=1, bg='lightgray')
        titulo_frame.grid(row=0, column=0, sticky="ew", columnspan=len(config))  # Abarcar todas las columnas

        for col_config in config:
            label = tk.Label(titulo_frame, text=col_config['description'], anchor="center",
                             font=('Consolas', 10, 'bold'))
            label.grid(row=0, column=col_config['col'], sticky="ew", padx=1, pady=5)

    def crear_frames_en_columnas(self, subframe, config, scrollable_frame, frame_store):
        """
        Crea una serie de frames dentro del subframe de acuerdo a la configuración proporcionada.
        Almacena los frames en un diccionario frame_store con un identificador.
        """
        for col_config in config:
            frame = tk.Frame(scrollable_frame, relief=tk.RAISED, bd=1, bg='lightblue')
            frame.grid(row=1, column=col_config['col'],
                       sticky="nsew")  # Posiciona en la segunda fila para contenido desplazable

            # Asigna un nombre al frame basado en la descripción de la columna
            frame_name = col_config['description']
            frame_store[frame_name] = frame  # Guarda el frame en el diccionario

    def create_scrollable_area(self, subframe, canvas_attr_name, **kwargs):
        """Crea un área desplazable dentro del subframe para los datos, debajo de los títulos fijos."""
        # Crear un canvas para contener el área desplazable
        canvas = tk.Canvas(subframe, **kwargs)
        scrollbar = ttk.Scrollbar(subframe, orient="vertical", command=canvas.yview)

        # Crear un frame interno para añadir widgets desplazables
        scrollable_frame = tk.Frame(canvas)

        # Configurar el evento para ajustar la región de scroll
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        # Crear una ventana en el canvas para mostrar el frame desplazable
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Configurar el canvas para que funcione con la scrollbar
        canvas.configure(yscrollcommand=scrollbar.set)

        # Configurar el layout dentro del subframe
        canvas.grid(row=1, column=0, sticky="nsew")  # Asegurar que el canvas ocupe todo el espacio
        scrollbar.grid(row=1, column=1, sticky="ns")

        # Asegurar que el subframe permita la expansión del canvas y scrollbar
        subframe.grid_rowconfigure(1, weight=1)  # Asegurar expansión vertical
        subframe.grid_columnconfigure(0, weight=1)  # Asegurar expansión horizontal

        # Guardar el canvas en el atributo correspondiente de la clase
        setattr(self, canvas_attr_name, canvas)

        # Vincular el evento de la rueda del ratón a ambos canvas
        canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

        return scrollable_frame




    def get_frames_columnas_archivo(self):
        """Devuelve los frames de columnas del subframe1 (archivo)."""
        return self.frames_columnas_archivo

    def get_frames_columnas_resultado(self):
        """Devuelve los frames de columnas del subframe2 (resultado)."""
        return self.frames_columnas_resultado











    def create_status_bar(self):
        """Create a status bar at the bottom of the window."""
        self.status_bar = tk.Label(self.root, text="Status: Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        # Set the grid for the status bar, ensuring it spans across the required columns
        self.status_bar.grid(row=self.status_bar_row, column=0, columnspan=self.status_bar_colspan, sticky="ew")





    def convert_playlist(self):
        # Abrir el cuadro de diálogo para seleccionar un archivo M3U
        m3u_file_path = filedialog.askopenfilename(
            initialdir=m3u_start_path,
            title="Select M3U Playlist",
            filetypes=[("M3U files", "*.m3u"), ("All files", "*.*")]
        )

        # Si no se selecciona ningún archivo, salir de la función
        if not m3u_file_path:
            return

        # Leer el contenido del archivo M3U y eliminar las líneas en blanco
        with open(m3u_file_path, 'r', encoding='utf-8') as file:
            m3u_lines = [line.strip() for line in file if line.strip()]

        # Crear una ventana popup para mostrar el contenido del M3U
        popup = tk.Toplevel(self.root)
        popup.title("Playlist Preview")
        popup.geometry("800x600")

        # Crear un marco para la tabla
        frame = tk.Frame(popup)
        frame.pack(fill='both', expand=True)

        # Crear una tabla Treeview para mostrar las líneas del M3U
        columns = ('#', 'Path')
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        tree.heading('#', text='#')
        tree.heading('Path', text='Path')
        tree.column('#', width=30, anchor='center')
        tree.column('Path', anchor='w')

        # Añadir un scrollbar a la tabla
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)

        # Mostrar el contenido del M3U en la tabla
        for index, line in enumerate(m3u_lines):
            if 'Dropbox' in line:
                # Cambiar el color del texto antes de "Dropbox"
                tree.insert('', 'end', values=(index + 1, line), tags=('highlight',))
                tree.tag_configure('highlight', foreground='blue')
            else:
                tree.insert('', 'end', values=(index + 1, line))

        # Crear una función para convertir y guardar la playlist
        def convert_and_save():
            # Identificar a qué ordenador corresponde el path de cada línea
            def get_computer_name_for_path(path):
                for computer_name, dropbox_path in path_map.items():
                    if path.startswith(dropbox_path):
                        return computer_name
                return None

            # Crear los archivos M3U para cada ordenador
            for computer_name, dropbox_path in path_map.items():
                new_m3u_path = m3u_file_path.replace(".m3u", f'_{computer_name}.m3u')
                with open(new_m3u_path, 'w', encoding='utf-8') as new_file:
                    for line in m3u_lines:
                        if 'Dropbox' in line:
                            # Reemplazar la parte del string antes de "Dropbox" con el path correspondiente
                            split_point = line.lower().find('dropbox')
                            original_computer = get_computer_name_for_path(line)
                            if original_computer == computer_name:
                                new_line = line
                            else:
                                new_line = dropbox_path + line[split_point + len('Dropbox'):]
                            new_file.write(new_line + '\n')
                        else:
                            new_file.write(line + '\n')

            messagebox.showinfo("Success",
                                f"Playlists converted and saved as:\n{', '.join([m3u_file_path.replace('.m3u', f'_{cn}.m3u') for cn in path_map.keys()])}")

        # Crear el botón para convertir la playlist
        convert_button = ttk.Button(popup, text="Convert Playlist", command=convert_and_save)
        convert_button.pack(pady=10)

        # Mostrar la ventana popup
        popup.transient(self.root)
        popup.grab_set()
        self.root.wait_window(popup)

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
            filtered_db = self.data_store.get_db()[
                self.data_store.get_db()['titulo'].str.lower().str.contains(title_filter, na=False) &
                (self.data_store.get_db()['artista'] == artist_filter if artist_filter != 'Todos' else True) &
                (self.data_store.get_db()['cantor'] == cantor_filter if cantor_filter != 'Todos' else True) &
                (self.data_store.get_db()['fecha'] >= start_date if start_date else True) &
                (self.data_store.get_db()['fecha'] <= end_date if end_date else True)
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
                filtered_cantors = self.data_store.get_db()['cantor'].dropna().unique().tolist()
            else:
                filtered_cantors = self.data_store.get_db()[self.data_store.get_db()['artista'] == selected_artist]['cantor'].dropna().unique().tolist()

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
        artist_dropdown['values'] = ['Todos'] + sorted(self.data_store.get_db()['artista'].dropna().unique().tolist())
        artist_dropdown.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        artist_var.trace("w", update_cantor_dropdown)

        # Filtro de Cantor
        tk.Label(popup, text="Cantor:", font=font_style).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        cantor_var = tk.StringVar(popup)
        cantor_var.set("Todos")
        cantor_dropdown = ttk.Combobox(popup, textvariable=cantor_var, font=font_style)
        cantor_dropdown['values'] = ['Todos'] + sorted(self.data_store.get_db()['cantor'].dropna().unique().tolist())
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



    def load_music_file(self):
        global numero_canciones
        file_path = filedialog.askopenfilename(
            filetypes=[("MUSIC files", ".mp3 .wav .flac .ogg .m4a"), ("All files", "*.*")]
        )
        if file_path:
            # try:
            new_filetofind = FILETOFIND(
                framefiles=self.subframe1,
                framedatabase=self.subframe2,
                frames_columnas_archivo=self.frames_columnas_archivo,  # Pasar diccionario de frames de archivo
                frames_columnas_resultado=self.frames_columnas_resultado,  # Pasar diccionario de frames de resultado
                ruta_archivo=file_path,
                frame_number=numero_canciones,
                root=self.root
            )

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
                            new_filetofind = FILETOFIND(
                                framefiles=self.subframe1,
                                framedatabase=self.subframe2,
                                frames_columnas_archivo=self.frames_columnas_archivo,
                                # Pasar diccionario de frames de archivo
                                frames_columnas_resultado=self.frames_columnas_resultado,
                                # Pasar diccionario de frames de resultado
                                ruta_archivo=line,
                                frame_number=numero_canciones,
                                root=self.root
                            )
                            numero_canciones += 1
                            filetofind_list.append(new_filetofind)
                        else:
                            modified_path = dropbox_path + line.split("Dropbox", 1)[1]
                            if os.path.exists(modified_path):
                                new_filetofind = FILETOFIND(
                                    framefiles=self.subframe1,
                                    framedatabase=self.subframe2,
                                    frames_columnas_archivo=self.frames_columnas_archivo,
                                    # Pasar diccionario de frames de archivo
                                    frames_columnas_resultado=self.frames_columnas_resultado,
                                    # Pasar diccionario de frames de resultado
                                    ruta_archivo=modified_path,
                                    frame_number=numero_canciones,
                                    root=self.root
                                )

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
                self.root.update()
            if filename.endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):  # Add more extensions as needed
                file_path = os.path.join(folder_path, filename)
                if file_path:
                    # try:
                    new_filetofind = FILETOFIND(
                        framefiles=self.subframe1,
                        framedatabase=self.subframe2,
                        frames_columnas_archivo=self.frames_columnas_archivo,
                        # Pasar diccionario de frames de archivo
                        frames_columnas_resultado=self.frames_columnas_resultado,
                        # Pasar diccionario de frames de resultado
                        ruta_archivo=file_path,
                        frame_number=numero_canciones,
                        root=self.root
                    )

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
                    if archivos.coincidencias.cantor.iloc[index] != "":
                        artist = f'{archivos.coincidencias.artista.iloc[index]} / {archivos.coincidencias.cantor.iloc[index]}'
                    else:
                        artist = f'{archivos.coincidencias.artista.iloc[index]}'

                    update_tags(
                        archivos.ruta_archivo,
                        title=archivos.coincidencias.titulo.iloc[index],
                        artist=artist,
                        year=archivos.coincidencias.fecha.iloc[index],
                        genre=archivos.coincidencias.estilo.iloc[index],
                        composer=archivos.coincidencias.compositor_autor.iloc[index]
                    )
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
