from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime
from presentation_app import PresentationApp
from src.ui.file_to_find import FILETOFIND
from src.utils.utils import *
from src.config.database import Database
from src.config.config import columnas_config, musicbee_tags
import tkinter as tk
from src.ui.playlist_operations import PlaylistOperations
from src.utils.MusicBeeLibraryTools import MusicBeeLibraryTools

class Ventana:
    def __init__(self, root):
        self.data_store = Database()
        self.root = root
        self.colour = 'white'
        self.pad = 0

        # Inicializar los diccionarios para almacenar los frames de columnas
        self.frames_columnas_archivo = {}
        self.frames_columnas_resultado = {}

        # Initialize PlaylistOperations
        self.playlist_operations = PlaylistOperations(self.root, m3u_start_path, path_map)

        self.musicbee = MusicBeeLibraryTools(self.root)


        self.root.title("Tkinter Window with Menu, Icon, and Status Bar")
        self.root.geometry('1700x800')

        # Setup layout configurations
        self.layout_configurations()

        # Inicialización previa
        self.presentation_window = None  # Inicializar a None
        # El resto de la inicialización

        # Initialize the checkbutton states with default values from config.py
        self.date_checked = tk.BooleanVar(value=DEFAULT_DATE_CHECKED)
        self.perfect_matches = tk.BooleanVar(value=DEFAULT_PERFECT_MATCHES)
        self.artist_not_found = tk.BooleanVar(value=DEFAULT_ARTIST_NOT_FOUND)
        self.title_not_found = tk.BooleanVar(value=DEFAULT_TITLE_NOT_FOUND)
        self.view_remaining = tk.BooleanVar(value=DEFAULT_REMAINING)
        self.direct_comparison = tk.BooleanVar(value=DEFAULT_DIRECT_COMPARISON)

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
                      'convert_playlist', 'merge', 'musicbee']
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
            (self.convert_playlist_icon, self.playlist_operations.convert_playlist),
            (self.merge_icon, self.playlist_operations.merge_playlist),
            (self.musicbee_icon, self.musicbee.open_musicbee_library)
        ]

        for i, (icon, command) in enumerate(buttons):
            btn = tk.Button(self.icon_bar, image=icon, relief=tk.FLAT, command=command)
            btn.grid(row=0, column=i, padx=self.pad, pady=self.pad)

        checkbuttons = [
            ("Date Checked", self.date_checked),
            ("Perfect Matches", self.perfect_matches),
            ("Artist Not Found", self.artist_not_found),
            ("Title Not Found", self.title_not_found),
            ("Visualizar Resto", self.view_remaining),
            ("Comparacion directa", self.direct_comparison)
        ]

        for i, (text, variable) in enumerate(checkbuttons, start=len(buttons)):
            # Asigna 'red' a los colores solo si el texto es "Comparacion directa", de lo contrario None
            color = 'red' if text == "Comparacion directa" else None
            # Crea el Checkbutton con los colores correspondientes
            chk = tk.Checkbutton(self.icon_bar, text=text, variable=variable,
                                 bg=color, selectcolor=color)
            chk.grid(row=0, column=i, padx=self.pad, pady=self.pad)

    def configure_scrollable_frames(self):
        """Configure all scrollable frames in self.scrollable_frame to expand and fill their canvases."""
        for canvas, scrollable_frame in zip(self.canvas, self.scrollable_frame):
            # Force update to ensure all pending tasks are completed
            scrollable_frame.update_idletasks()

            # Bind the <Configure> event to adjust the size dynamically when the window is resized
            canvas.bind("<Configure>", lambda event, c=canvas, sf=scrollable_frame: self.adjust_canvas_width(c, sf))

            # Initial adjustment to set the correct size
            self.adjust_canvas_width(canvas, scrollable_frame)

    def adjust_canvas_width(self, canvas, scrollable_frame):
        """Adjust the canvas window width to match the canvas size."""
        # Get the current width of the canvas
        canvas_width = canvas.winfo_width()
        if canvas_width > 0:
            # Adjust the canvas window width to match the canvas width
            canvas.itemconfig(self.canvas_window[self.canvas.index(canvas)], width=canvas_width)

        # Ensure the grid inside the scrollable frame allows content to expand
        scrollable_frame.grid_rowconfigure(0, weight=1)  # Ensuring the row expands
        scrollable_frame.grid_columnconfigure(0, weight=1)  # Ensuring the column expands

    def open_musicbee_library(self):
        """Open a file dialog to select the MusicBee library file."""
        file_path = filedialog.askopenfilename(
            title="Select MusicBee Library File",
            filetypes=[("MusicBee Library Files", "*.mbl"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                # Initialize the MusicBeeLibraryTools with the selected file
                self.musicbee_tool = MusicBeeLibraryTools(file_path)
                self.musicbee_tool.parse_library()
                messagebox.showinfo("Success", "Library loaded successfully!")

                # After loading, show a popup to search for artist
                self.show_artist_search_popup()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load library: {e}")

    def create_title_frame(self):
        """Create the title frame with 'File Tags' and 'Database Tags' labels."""
        self.title_frame = tk.Frame(self.root, relief=tk.RAISED, bd=2)
        self.title_frame.grid(row=self.title_frame_row, column=0, columnspan=self.title_frame_colspan, sticky="ew")
        self.title_frame.grid_propagate(True)  # Allow resizing to content

        # Set weights and minsize explicitly for the title columns
        self.title_frame.grid_columnconfigure(0, weight=435, minsize=200)  # Control size for "File Tags"
        self.title_frame.grid_columnconfigure(1, weight=565, minsize=200)  # Control size for "Database Tags"

        # Create the labels
        file_tags_label = tk.Label(
            self.title_frame,
            text="File Tags",
            font=('Consolas', 12, 'bold'),
            bg=self.colour,
            relief=tk.SOLID,
            bd=1
        )
        file_tags_label.grid(row=0, column=0, padx=self.pad, pady=self.pad, sticky="nsew")

        database_tags_label = tk.Label(
            self.title_frame,
            text="Database Tags",
            font=('Consolas', 12, 'bold'),
            bg=self.colour,
            relief=tk.SOLID,
            bd=1
        )
        database_tags_label.grid(row=0, column=1, padx=self.pad, pady=self.pad, sticky="nsew")

    def create_main_content_area(self):
        """Create the main content area with two subframes occupying all available space."""
        # Crear el contenedor principal para los subframes
        self.main_content = tk.Frame(self.root, bg=self.colour)  # Color de fondo del main_content
        self.main_content.grid(row=self.main_content_row, column=0, columnspan=self.main_content_colspan, sticky="nsew")

        # Configuración para expandir el main_content
        self.main_content.grid_rowconfigure(0, weight=1)  # Permitir que la fila se expanda
        self.main_content.grid_columnconfigure(0, weight=1)  # Ajuste proporcional para el primer subframe
        self.main_content.grid_columnconfigure(1, weight=1)  # Ajuste proporcional para el segundo subframe

        # Crear los subframes
        self.create_subframes()

    def create_subframes(self):
        """Create subframes inside the main content area, ensuring they resize with the window."""
        # Initialize the list to hold scrollable frames
        self.scrollable_frame = []
        self.canvas = []
        self.canvas_window = []

        # Create and configure subframe1
        self.create_and_configure_subframe(
            subframe_bg=self.colour,
            subframe_row=0,
            subframe_column=0,
            title_config=columnas_config['archivo'],
            scrollable_bg=self.colour,
            frames_columnas=self.frames_columnas_archivo,
            canvas_attr_name='canvas1'
        )
        self.configure_scrollable_frames()

        # Create and configure subframe2
        self.create_and_configure_subframe(
            subframe_bg=self.colour,
            subframe_row=0,
            subframe_column=1,
            title_config=columnas_config['resultado'],
            scrollable_bg=self.colour,
            frames_columnas=self.frames_columnas_resultado,
            canvas_attr_name='canvas2'
        )
        self.configure_scrollable_frames()


    def create_and_configure_subframe(self, subframe_bg, subframe_row, subframe_column, title_config, scrollable_bg,
                                      frames_columnas, canvas_attr_name):
        """Helper function to create and configure a subframe and its components."""
        # Create the subframe
        subframe = tk.Frame(self.main_content, relief=tk.RAISED, bd=2, bg=subframe_bg)
        subframe.grid(row=subframe_row, column=subframe_column, sticky="nsew")

        # Ensure the subframe expands correctly
        self.main_content.grid_rowconfigure(subframe_row, weight=1)
        self.main_content.grid_columnconfigure(subframe_column, weight=1)

        # Create fixed title row for the subframe
        self.crear_titulos(subframe, title_config)

        # Create the scrollable area within the subframe
        canvas_window, canvas, scrollable_frame = self.create_scrollable_area(subframe, canvas_attr_name, bg=scrollable_bg)
        self.scrollable_frame.append(scrollable_frame)
        self.canvas.append(canvas)
        self.canvas_window.append(canvas_window)



        # Create frames inside the scrollable area according to the provided configuration
        self.crear_frames_en_columnas(title_config, scrollable_frame, frames_columnas)

    def on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling only when the window is on top and focused."""
        # Check if the root window is focused
        if self.root.focus_get() is not None:
            # Scroll both canvases
            if hasattr(self, 'canvas1') and hasattr(self, 'canvas2'):
                self.canvas1.yview_scroll(int(-1 * (event.delta / 120)), "units")
                self.canvas2.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def crear_titulos(self, subframe, config):
        """
        Crea una fila de títulos fija en la parte superior del subframe,
        ajustando el ancho de cada columna según la configuración proporcionada.
        """
        titulo_frame = tk.Frame(subframe, relief=tk.RAISED, bd=1, bg=self.colour)
        titulo_frame.grid(row=0, column=0, sticky="ew", columnspan=len(config))  # Abarcar todas las columnas

        # Configura las columnas del titulo_frame según la configuración proporcionada
        for col_config in config:
            titulo_frame.grid_columnconfigure(col_config['col'], weight=col_config['weight'],
                                              minsize=col_config['minsize'])

        # Crea los labels para los títulos
        for col_config in config:
            label = tk.Label(titulo_frame,
                             text=col_config['description'] if col_config['tipo'] == 'label' else '',
                             anchor="center",
                             font=('Consolas', 15, 'bold'),
                             bg=self.colour)
            label.grid(row=0, column=col_config['col'], sticky="ew", padx=self.pad, pady=self.pad)

    def crear_frames_en_columnas(self, config, scrollable_frame, frame_store):
        """Creates frames inside the scrollable frame according to the provided configuration."""
        # Configure columns of the scrollable_frame to allow expansion
        for col_config in config:
            scrollable_frame.grid_columnconfigure(col_config['col'], weight=col_config['weight'],
                                                  minsize=col_config['minsize'])

        # Configure the row to expand as well (important for vertical alignment)
        scrollable_frame.grid_rowconfigure(0, weight=1)  # Ensure vertical expansion for the content

        # Create the frames based on the configuration
        for col_config in config:
            # Create a frame for each column
            frame = tk.Frame(scrollable_frame, relief=tk.RAISED, bg=self.colour, highlightbackground=self.colour,
                             highlightthickness=2)
            frame.grid(row=0, column=col_config['col'], sticky="nsew", padx=self.pad, pady=self.pad)

            # Assign a name to the frame based on the column description
            frame_name = col_config['description']
            frame_store[frame_name] = frame  # Store the frame in the dictionary

    def create_scrollable_area(self, subframe, canvas_attr_name, **kwargs):
        """Creates a scrollable area inside the subframe for data, below the fixed titles."""
        # Filter out conflicting arguments from kwargs
        self.root.bind_all("<MouseWheel>", self.on_mouse_wheel)

        canvas_kwargs = {k: v for k, v in kwargs.items() if
                         k not in ['bg', 'highlightbackground', 'highlightthickness']}

        # Create a canvas to contain the scrollable area with distinct colors for debugging
        canvas = tk.Canvas(subframe, bg=self.colour, highlightbackground=self.colour, highlightthickness=2, **canvas_kwargs)
        scrollbar = ttk.Scrollbar(subframe, orient="vertical", command=canvas.yview)

        # Create an internal frame to add scrollable widgets
        scrollable_frame = tk.Frame(canvas, bg=self.colour, highlightbackground=self.colour, highlightthickness=2)

        # Adjust the scroll region to encompass the entire frame
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))


        # Bind the configuration change event to the scrollable frame
        scrollable_frame.bind("<Configure>", on_frame_configure)


        # Create a window in the canvas to display the scrollable frame
        canvas_window =  canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Configure the canvas to work with the scrollbar
        canvas.configure(yscrollcommand=scrollbar.set)

        # Layout configuration within the subframe
        canvas.grid(row=1, column=0, sticky="nsew")  # Ensure the canvas occupies all space
        scrollbar.grid(row=1, column=1, sticky="ns")

        # Ensure the subframe allows the canvas and scrollbar to expand
        subframe.grid_rowconfigure(1, weight=1)  # Ensure vertical expansion
        subframe.grid_columnconfigure(0, weight=1)  # Ensure horizontal expansion

        # Save the canvas in the corresponding class attribute
        setattr(self, canvas_attr_name, canvas)

        # Bind mouse wheel events to scroll both canvases
        canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

        # Assuming self.scrollable_frame is a list of frames you want to configure
        # Configure all scrollable frames

        # scrollable_frame.update_idletasks()
        # canvas.itemconfig(canvas_window, width=canvas.winfo_width())
        # scrollable_frame.grid_rowconfigure(0, weight=1)  # Ensuring the row expands
        # scrollable_frame.grid_columnconfigure(0, weight=1)


        return canvas_window, canvas, scrollable_frame

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


    def open_presentation_popup(self):
        # Inicializa la ventana si no existe o si ha sido destruida
        if self.presentation_window is None or not tk.Toplevel.winfo_exists(self.presentation_window):
            self.presentation_window = tk.Toplevel(self.root)
            self.presentation_window.title("Presentation Window")
            # Añade más configuración para la ventana si es necesario
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
        tk.Label(popup, text="Titulo:", font=font_style).grid(row=0, column=0, padx=self.pad, pady=self.pad, sticky="w")
        title_entry = tk.Entry(popup, font=font_style)
        title_entry.grid(row=0, column=1, padx=self.pad, pady=self.pad, sticky="ew")
        title_entry.bind("<KeyRelease>", lambda event: update_table())

        # Filtro de Artista
        tk.Label(popup, text="Artista:", font=font_style).grid(row=1, column=0, padx=self.pad, pady=self.pad, sticky="w")
        artist_var = tk.StringVar(popup)
        artist_var.set("Todos")
        artist_dropdown = ttk.Combobox(popup, textvariable=artist_var, font=font_style)
        artist_dropdown['values'] = ['Todos'] + sorted(self.data_store.get_db()['artista'].dropna().unique().tolist())
        artist_dropdown.grid(row=1, column=1, padx=self.pad, pady=self.pad, sticky="ew")
        artist_var.trace("w", update_cantor_dropdown)

        # Filtro de Cantor
        tk.Label(popup, text="Cantor:", font=font_style).grid(row=2, column=0, padx=self.pad, pady=self.pad, sticky="w")
        cantor_var = tk.StringVar(popup)
        cantor_var.set("Todos")
        cantor_dropdown = ttk.Combobox(popup, textvariable=cantor_var, font=font_style)
        cantor_dropdown['values'] = ['Todos'] + sorted(self.data_store.get_db()['cantor'].dropna().unique().tolist())
        cantor_dropdown.grid(row=2, column=1, padx=self.pad, pady=self.pad, sticky="ew")
        cantor_var.trace("w", on_filter_change)

        # Filtro de Fecha
        tk.Label(popup, text="Fecha desde:", font=font_style).grid(row=3, column=0, padx=self.pad, pady=self.pad, sticky="w")
        start_date_entry = tk.Entry(popup, font=font_style)
        start_date_entry.grid(row=3, column=1, padx=self.pad, pady=self.pad, sticky="ew")
        start_date_entry.bind("<KeyRelease>", lambda event: update_table())

        tk.Label(popup, text="Fecha hasta:", font=font_style).grid(row=3, column=2, padx=self.pad, pady=self.pad, sticky="w")
        end_date_entry = tk.Entry(popup, font=font_style)
        end_date_entry.grid(row=3, column=3, padx=self.pad, pady=self.pad, sticky="ew")
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
        self.borrar_todo()
        numero_canciones = 0
        file_path = filedialog.askopenfilename(
            filetypes=[("MUSIC files", ".mp3 .wav .flac .ogg .m4a"), ("All files", "*.*")]
        )
        if file_path:
            # try:
            new_filetofind = FILETOFIND(
                framefiles=self.scrollable_frame[0],
                framedatabase=self.scrollable_frame[1],
                frames_columnas_archivo=self.frames_columnas_archivo,  # Pasar diccionario de frames de archivo
                frames_columnas_resultado=self.frames_columnas_resultado,  # Pasar diccionario de frames de resultado
                ruta_archivo=file_path,
                frame_number=numero_canciones,
                root=self.root,
                show_date_checked=self.date_checked.get(),
                show_perfect_matches=self.perfect_matches.get(),
                show_artist_not_found=self.artist_not_found.get(),
                show_title_not_found=self.title_not_found.get(),
                show_remaining=self.view_remaining.get(),  # Pasar el estado del nuevo checkbox
                compare=self.direct_comparison.get()
            )

            numero_canciones = new_filetofind.nextframe
            filetofind_list.append(new_filetofind)
            # except Exception as error:
            #     messagebox.showerror("Error", f"Error al leer el archivo musica:\n{error}")

    def open_playlist(self):
        self.borrar_todo()
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
                            numero_canciones = self.crear_y_actualizar_filetofind(
                                ruta_archivo=line,
                                frame_number=numero_canciones
                            )
                        else:
                            modified_path = dropbox_path + line.split("Dropbox", 1)[1]
                            if os.path.exists(modified_path):
                                numero_canciones = self.crear_y_actualizar_filetofind(
                                    ruta_archivo=modified_path,
                                    frame_number=numero_canciones
                                )

    def load_music_folder(self):
        self.borrar_todo()
        numero_canciones = 0
        folder_path = filedialog.askdirectory()
        # Loop through all files in the folder
        # Create a Label for the status text
        self.status_label = tk.Label(self.status_bar, text="Progress: 0%", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT)

        # Create a Progressbar widget
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(self.status_bar, variable=self.progress_var, maximum=100, length=150)
        self.progress_bar.pack(side=tk.RIGHT, padx=self.pad)
        contador_canciones = 0

        for filename in os.listdir(folder_path):
            self.update_progress(100 * contador_canciones / len(os.listdir(folder_path)))
            contador_canciones += 1
            if contador_canciones % 10 == 0:
                self.root.update()
            if filename.endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):  # Add more extensions as needed
                file_path = os.path.join(folder_path, filename)
                if file_path:
                    numero_canciones = self.crear_y_actualizar_filetofind(
                        ruta_archivo=file_path,
                        frame_number=numero_canciones
                    )


                    # except Exception as error:
                    #     messagebox.showerror("Error", f"Error al leer el archivo musica:\n{error}")
        self.progress_bar.pack_forget()
        self.status_label.pack_forget()

    def crear_y_actualizar_filetofind(self, ruta_archivo, frame_number):
        """
        Crea una instancia de FILETOFIND, la actualiza según los filtros seleccionados,
        y la añade a la lista global de filetofind_list.
        """
        # Crear instancia de FILETOFIND con los parámetros constantes
        new_filetofind = FILETOFIND(
            framefiles=self.scrollable_frame[0],
            framedatabase=self.scrollable_frame[1],
            frames_columnas_archivo=self.frames_columnas_archivo,
            frames_columnas_resultado=self.frames_columnas_resultado,
            ruta_archivo=ruta_archivo,
            frame_number=frame_number,
            root=self.root,
            show_date_checked = self.date_checked.get(),
            show_perfect_matches = self.perfect_matches.get(),
            show_artist_not_found = self.artist_not_found.get(),
            show_title_not_found = self.title_not_found.get(),
            show_remaining = self.view_remaining.get(),  # Pasar el estado del nuevo checkbox
            compare = self.direct_comparison.get()
            )

        # Actualizar el número de canciones y añadir a la lista global
        frame_number = new_filetofind.nextframe
        filetofind_list.append(new_filetofind)

        return frame_number




    def aplicartags(self):
        reemplazo_tags = []
        for archivos in filetofind_list:
            for index, check in enumerate(archivos.vars):
                if check.get():
                    artist=unir_artistas(archivos.coincidencias.artista.iloc[index],archivos.coincidencias.cantor.iloc[index], " / " )


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
