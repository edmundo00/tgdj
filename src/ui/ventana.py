from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from datetime import datetime
from presentation_app import PresentationApp
from src.ui.file_to_find import FILETOFIND
from src.utils.utils import *
from src.config.database import Database
from src.config.config import columnas_config, musicbee_tags, df_reporte
import tkinter as tk
from src.ui.playlist_operations import PlaylistOperations
from src.utils.MusicBeeLibraryTools import MusicBeeLibraryTools
from src.ui.owndatabase import owndatabase
from src.ui.ReportManager import ReportManager
import threading

class Ventana:
    def __init__(self, root):
        self.data_store = Database()
        self.root = root
        self.colour = 'white'
        self.pad = 0
        self.df_reporte = pd.DataFrame()
        self.df_reporte_coincidencia_favorita = df_reporte_coincidencia_favorita
        self.origen_archivos = None

        self.owndb = None

        # Inicializar los diccionarios para almacenar los frames de columnas
        self.frames_columnas_archivo = {}
        self.frames_columnas_resultado = {}

        # Initialize PlaylistOperations
        self.playlist_operations = PlaylistOperations(self.root, m3u_start_path, path_map)

        self.owndb = owndatabase(self.update_progress_and_status)

        self.root.title("Tkinter Window with Menu, Icon, and Status Bar")
        self.root.geometry('1700x800')

        # Set Fullscreen Mode if the flag is enabled
        if full_screen:
            self.root.attributes('-fullscreen', True)  # Fullscreen enabled
            self.root.bind("<Escape>", self.exit_fullscreen)  # Press Escape to exit fullscreen mode

        # Set Maximized Mode if the flag is enabled
        if maximized:
            self.root.state('zoomed')  # Maximizes the window

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
        self.direct_tagging = tk.BooleanVar(value=DEFAULT_DIRECT_TAGGING)
        self.guardar_residuos = tk.BooleanVar(value=guardar_residuos)
        self.guardar_coincidencias = tk.BooleanVar(value=guardar_coincidencias)

        # Create UI components
        self.create_menu_bar()
        self.create_icon_bar()
        if not self.direct_tagging:
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
        """Create the icon bar with different frames for sections below the menu bar."""
        self.icon_bar = tk.Frame(self.root, relief=tk.RAISED, bd=2)
        self.icon_bar.grid(row=self.icon_bar_row, column=0, columnspan=self.icon_bar_colspan, sticky="ew")

        # Define icons and their commands
        icon_names = ['archivo', 'directorio', 'correr', 'transfer', 'trash', 'searchdb', 'presentacion', 'playlist',
                      'convert_playlist', 'merge', 'musicbee', 'createdb', 'comparedb', 'loaddb', 'filterdb']
        for icon_name in icon_names:
            setattr(self, f"{icon_name}_icon", tk.PhotoImage(file=icon_paths[icon_name]))

        # Define buttons
        buttons = [
            (self.archivo_icon, self.load_music_file, "Load a music file to compare"),
            (self.directorio_icon, self.load_music_folder, "Load a music folder to compare"),
            (self.playlist_icon, self.open_playlist, "Open a playlist to compare"),
            (self.musicbee_icon, self.open_musicbee_library, "Open MusicBee Library to compare"),
            (self.transfer_icon, self.aplicartags, "Apply tags"),
            (self.trash_icon, self.borrar_todo, "Delete all"),
            (self.convert_playlist_icon, self.playlist_operations.convert_playlist, "Convert playlist"),
            (self.merge_icon, self.playlist_operations.merge_playlist, "Merge playlist"),
            (self.createdb_icon, self.createdb, "Create database"),
            (self.loaddb_icon, self.loaddb, "Load database"),
            (self.comparedb_icon, self.comparedb, "Compare database"),
            (self.filterdb_icon, self.filterdb, "Filter database"),
            (self.presentacion_icon, self.open_presentation_popup, "Open presentation"),
            (self.correr_icon, None, "Run")
        ]

        sections = [
            ("Compare", buttons[:4]),
            ("Tools", buttons[4:6]),
            ("Playlist Tools", buttons[6:8]),
            ("Own DB", buttons[8:12]),
            ("Search DB", buttons[12:13]),
            ("Slides", buttons[12:13]),
            ("Others", buttons[13:14])
        ]

        # Configure the icon_bar to allow columns to resize based on content
        self.icon_bar.grid_columnconfigure(0, weight=0)
        self.icon_bar.grid_columnconfigure(1, weight=0)

        # Create a frame for each section and place them in columns
        for column_index, (section_title, section_buttons) in enumerate(sections):
            section_frame = tk.Frame(self.icon_bar, relief=tk.GROOVE, bd=2, padx=5, pady=5)
            section_frame.grid(row=0, column=column_index, sticky="nsew", padx=5, pady=5)

            # Add a label for the section
            label = tk.Label(section_frame, text=section_title, font=("Arial", 10, 'bold'))
            label.grid(row=0, column=0, columnspan=len(section_buttons), sticky="ew")

            # Create buttons within the section
            for i, (icon, command, tooltip) in enumerate(section_buttons):
                btn = tk.Button(section_frame, image=icon, relief=tk.FLAT, command=command)
                btn.grid(row=1, column=i, padx=5, pady=5)
                # Add tooltip functionality if defined
                # self.add_tooltip(btn, tooltip)

        # Checkbuttons section
        checkbutton_frame = tk.Frame(self.icon_bar)
        checkbutton_frame.grid(row=1, column=0, columnspan=len(sections), sticky="ew", pady=10)

        checkbuttons = [
            ("Date Checked", self.date_checked, None, None),
            ("Perfect Matches", self.perfect_matches, None, None),
            ("Artist Not Found", self.artist_not_found, None, None),
            ("Title Not Found", self.title_not_found, None, None),
            ("Visualizar Resto", self.view_remaining, None, None),
            ("Guardar coincidencias", self.guardar_coincidencias, None, None),
            ("Guardar residuos", self.guardar_residuos, None, None),
            ("No mostrar comparativa", self.direct_comparison, self.toggle_direct_tagging, None),
            ("Direct tagging", self.direct_tagging, None, 'red')
        ]

        for i, (text, variable, command, color) in enumerate(checkbuttons):
            chk = tk.Checkbutton(
                checkbutton_frame,
                text=text,
                variable=variable,
                bg=color if color else None,  # Use color if provided, otherwise default
                selectcolor=color if color else None,  # Apply color for when selected
                command=command
            )
            chk.grid(row=0, column=i, padx=5, pady=5)

        # Configure the main frame to not expand and adjust based on content
        for i in range(len(sections)):
            self.icon_bar.grid_columnconfigure(i, weight=0)

    def add_tooltip(self, widget, text):
        """Add a tooltip to a widget."""
        tooltip = tk.Label(self.root, text=text, background="yellow", relief=tk.SOLID, borderwidth=1, padx=2, pady=2, font=("Arial", 8))

        def show_tooltip(event):
            tooltip.place(x=event.x_root, y=event.y_root)

        def hide_tooltip(event):
            tooltip.place_forget()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

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

    def toggle_direct_tagging(self):
        """Toggle the direct tagging and reset or clear the layout based on the checkbutton state."""
        if self.direct_tagging.get():  # If it's checked, destroy frames and deactivate
            # Clear layout variables
            self.title_frame_row = 1
            self.title_frame_colspan = 3
            self.main_content_row = 2
            self.main_content_colspan = 3

            # Destroy the existing frames if they exist
            if hasattr(self, 'title_frame'):
                self.title_frame.destroy()
            if hasattr(self, 'main_content'):
                self.main_content.destroy()

            self.direct_tagging.set(False)  # Uncheck the button

        else:  # If it's unchecked, create the frames and activate
            # Create UI components
            self.create_title_frame()
            self.create_main_content_area()

            self.direct_tagging.set(True)  # Check the button


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

    def on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def load_music_file(self):
        self.borrar_todo()  # Clear the list of existing files
        numero_canciones = 0

        # Open a dialog to select a music file
        file_path = filedialog.askopenfilename(
            filetypes=[("MUSIC files", ".mp3 .wav .flac .ogg .m4a"), ("All files", "*.*")]
        )

        if file_path:
            # Create a list with a single file to reuse the same processing logic as for the folder
            music_files = [file_path]

            # Process the file using the same method as the folder, passing the file and folder path
            folder_path = os.path.dirname(file_path)  # Folder of the selected file

            self.origen_archivos = 'file'
            self.procesar_archivos(music_files, numero_canciones, show_progress=False, origen=folder_path)

    def open_musicbee_library(self):

        self.borrar_todo()  # Limpiar la lista de archivos existentes
        numero_canciones = 0
        """Open a file dialog to select the MusicBee library file."""
        file_path = filedialog.askopenfilename(
            title="Select MusicBee Library File",
            filetypes=[("MusicBee Library Files", "*.mbl"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                # Initialize the MusicBeeLibraryTools with the selected file
                self.musicbee_tool = MusicBeeLibraryTools(self.root, file_path)
                self.musicbee_tool.parse_library()
                # messagebox.showinfo("Success", "Library loaded successfully!")
                lines = self.musicbee_tool.library_df['file_path'].tolist()
                tagsml_df = self.musicbee_tool.library_df[['title', 'artist', 'year', 'genre', 'composer','file_path']]

                self.origen_archivos = 'musicbee'
                self.procesar_archivos(lines, numero_canciones, from_musicbee=True, show_progress=True,
                                       origen=file_path, tags=tagsml_df)

                # # After loading, show a popup to search for artist
                # self.musicbee_tool.musicbee_options_popup()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load library: {e}")

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

            # Load the M3U file and extract data
            with open(self.m3u_file_path, 'r', encoding='utf-8') as file:
                lines = [line.strip() for line in file if line.strip() and not line.startswith("#")]
                # Process lines from M3U file
                #lines es una lista con todos los paths de las canciones
                # numero_canciones es un contador que se define aqui mismo

                self.origen_archivos = 'playlist'
                self.procesar_archivos(lines, numero_canciones, from_playlist=True, show_progress=True,origen=self.m3u_file_path)

    def load_music_folder(self):
        self.borrar_todo()
        numero_canciones = 0
        folder_path = filedialog.askdirectory()

        if folder_path:
            # Get list of music files
            music_files = [os.path.join(folder_path, filename) for filename in os.listdir(folder_path)
                           if filename.endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a'))]

            # Process files from the directory
            self.origen_archivos = 'folder'
            self.procesar_archivos(music_files, numero_canciones, show_progress=True,origen=folder_path)

    def procesar_archivos(self, archivos, numero_canciones, from_playlist=False, from_musicbee= False, show_progress=False, origen=None, tags=None):
        """Procesa una lista de archivos y actualiza la interfaz."""

        total_archivos = len(archivos)
        self.archivos_comparado = ReportManager()

        # Configurar la barra de progreso si es necesario
        if show_progress:
            self.setup_progress_bar()

        for index, archivo in enumerate(archivos):
            tags_aplicar = None
            # Update progress if required
            if show_progress:
                self.update_progress_and_status(current= index + 1, total= total_archivos)


            # Process each file
            if from_playlist and not os.path.exists(archivo):
                # Handle special case for modified paths in playlists
                modified_path = dropbox_path + archivo.split("Dropbox", 1)[1]
                if os.path.exists(modified_path):
                    archivo = modified_path

            if from_musicbee and os.path.exists(archivo):
                # Handle special case for modified paths in playlists
                tags_aplicar = tags.iloc[index].tolist()


            if os.path.exists(archivo):
                numero_canciones, report_archivo, coinc_fav = self.crear_y_actualizar_filetofind(
                    ruta_archivo=archivo,
                    frame_number=numero_canciones,
                    tags = tags_aplicar
                )

                self.archivos_comparado.add_row(report_archivo)

                # # Comprobar si self.df_reporte está definido o no
                # if self.df_reporte is None:
                #     # Si no está definido, inicializar con el primer DataFrame
                #     self.df_reporte = pd.DataFrame([report_archivo])
                # else:
                #     # Si ya existe, concatenar el nuevo reporte
                #     self.df_reporte = pd.concat([self.df_reporte, pd.DataFrame([report_archivo])], ignore_index=True)



                if self.guardar_coincidencias.get():
                    self.df_reporte_coincidencia_favorita = pd.concat([self.df_reporte_coincidencia_favorita, coinc_fav], ignore_index=True)
            if show_progress:
                # Ensure UI updates properly
                self.root.after(10, self.update_progress_and_status(current=index + 1, total=total_archivos))

        # Establecer 'file_path' como índice pero mantenerlo como columna
        self.archivos_comparado.finalize_report()

        if showpopupinfo:
            self.mostrar_popup_reporte(self.archivos_comparado.report_df)

        if self.guardar_coincidencias.get():
            guardar_archivo_output(tipo='coincidencias', dataframe=self.df_reporte_coincidencia_favorita,
                                   encabezados=None)
        # Guardar residuos si se requiere
        if self.guardar_residuos.get():
            residuos_df = pd.DataFrame(residuos, columns=['Titulo Archivo', 'Titulo base de datos', 'Residuo',
                                                          'Ruta completa'])
            guardar_archivo_output(tipo='residuos', dataframe=residuos_df, encabezados=f"Origen: {origen}\n")

        # Limpiar la barra de progreso si fue utilizada
        if show_progress:
            self.cleanup_progress_bar()


    def mostrar_popup_reporte(self, df_reporte):
        # Calcular métricas del reporte
        total_canciones = len(df_reporte)
        sin_artista = df_reporte["Artista encontrado"].sum()
        sin_titulo = df_reporte["Titulo encontrado"].sum()
        coincidencia_perfecta = df_reporte["Coincidencia perfecta"].sum()
        coincidencia_preferida = df_reporte["Hay coincidencia preferida"].sum()
        no_coincidencia_preferida = df_reporte["No hay coincidencia preferida"].sum()

        # Crear la ventana de popup
        popup = tk.Toplevel()
        popup.title("Reporte de Análisis")

        # Crear el contenido del popup
        label_total = tk.Label(popup, text=f"Numero de canciones analizadas: {total_canciones}", font=("Helvetica", 12))
        label_total.grid(row=0, column=0, padx=10, pady=10)

        label_sin_artista = tk.Label(popup, text=f"Numero de canciones sin Artista encontrado: {sin_artista}",
                                     font=("Helvetica", 12, "bold"))
        label_sin_artista.grid(row=1, column=0, padx=10, pady=10)

        label_sin_titulo = tk.Label(popup, text=f"Numero de canciones sin Titulo encontrado: {sin_titulo}",
                                    font=("Helvetica", 12, "bold"))
        label_sin_titulo.grid(row=2, column=0, padx=10, pady=10)

        label_sin_titulo = tk.Label(popup, text=f"Numero de canciones con coincidencia perfecta: {coincidencia_perfecta}",
                                    font=("Helvetica", 12, "bold"))
        label_sin_titulo.grid(row=3, column=0, padx=10, pady=10)


        label_sin_titulo = tk.Label(popup, text=f"Numero de canciones con coincidencia preferida: {coincidencia_preferida}",
                                    font=("Helvetica", 12, "bold"))
        label_sin_titulo.grid(row=4, column=0, padx=10, pady=10)

        label_sin_titulo = tk.Label(popup, text=f"Numero de canciones sin coincidencia preferida: {no_coincidencia_preferida}",
                                    font=("Helvetica", 12, "bold"))
        label_sin_titulo.grid(row=5, column=0, padx=10, pady=10)


        # Botón para cerrar el popup
        close_button = tk.Button(popup, text="Cerrar", command=popup.destroy)
        close_button.grid(row=6, column=0, padx=10, pady=10)

    def setup_progress_bar(self):
        """Configura la barra de progreso y la etiqueta de estado."""
        self.status_label = tk.Label(self.status_bar, text="Progress: 0%", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT)

        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(self.status_bar, variable=self.progress_var, maximum=100, length=150)
        self.progress_bar.pack(side=tk.RIGHT, padx=self.pad)

    def cleanup_progress_bar(self):
        """Elimina la barra de progreso y la etiqueta de estado."""
        self.progress_bar.pack_forget()
        self.status_label.pack_forget()

    def crear_y_actualizar_filetofind(self, ruta_archivo, frame_number, tags):
        """
        Crea una instancia de FILETOFIND, la actualiza según los filtros seleccionados,
        y la añade a la lista global de filetofind_list.
        """
        # Crear instancia de FILETOFIND con los parámetros constantes
        if self.direct_tagging.get():
            lista_frames = [
                self.scrollable_frame[0],  # Corresponds to ff
                self.scrollable_frame[1],  # Corresponds to fd
                self.frames_columnas_archivo,
                self.frames_columnas_resultado
            ]
        else:
            lista_frames = [None, None, None, None]

        lista_checks = [
            self.date_checked.get(),  # Corresponds to show_date_checked
            self.perfect_matches.get(),  # Corresponds to show_perfect_matches
            self.artist_not_found.get(),  # Corresponds to show_artist_not_found
            self.title_not_found.get(),  # Corresponds to show_title_not_found
            self.view_remaining.get(),  # Corresponds to show_remaining
            self.direct_comparison.get()  # Corresponds to compare
        ]

        # Pass the list as a single argument along with other parameters
        new_filetofind = FILETOFIND(
            ruta_archivo=ruta_archivo,
            lista_frames=lista_frames,
            frame_number=frame_number,
            lista_checks=lista_checks,
            tags = tags
        )

        # Actualizar el número de canciones y añadir a la lista global
        frame_number = new_filetofind.nextframe
        reporte = new_filetofind.reporte()
        coinc_fav = new_filetofind.get_coincidencia_favorita()

        filetofind_list.append(new_filetofind)

        return frame_number, reporte, coinc_fav

    def aplicartags(self):
        reemplazo_tags = []
        self.reporte_tags = ReportManager()
        self.setup_progress_bar()

        total_archivos = len(filetofind_list)
        analizados = 0  # Contador de archivos analizados
        tageados = 0  # Contador de archivos efectivamente etiquetados

        def procesar_archivo_tags(archivo, coincidencia_preferida):
            """Helper function to process each file and update the reports."""
            nonlocal analizados, tageados, reemplazo_tags
            analizados += 1  # Incrementar el contador de analizados
            reemplazo_tags_linea, reporte, tageado = aplicartag_archivo(
                ruta_archivo=archivo.ruta_archivo,
                coincidencias=archivo.coincidencias,
                coincidencia_preferida=coincidencia_preferida,
                tags=archivo.tags,
                coincidencia_titulo=archivo.titulo_coincidencia
            )
            self.reporte_tags.add_row(reporte)
            if tageado:
                tageados += 1  # Incrementar el contador de tageados

            self.update_progress_and_status(current=analizados, total=total_archivos, tageados=tageados)

        if self.direct_comparison.get():
            # Procesar archivos con coincidencia preferida
            for archivo in filetofind_list:
                if archivo.hay_coincidencia_preferida:
                    procesar_archivo_tags(archivo, archivo.coincidencia_preferida)
        else:
            # Operar sobre las variables `vars` si no hay comparación directa
            for archivo in filetofind_list:
                for index, check in enumerate(archivo.vars):
                    if check.get():
                        procesar_archivo_tags(archivo, index)

        self.reporte_tags.finalize_report()

        if self.origen_archivos == 'owndb':
            self.owndb.owndf.update(self.reporte_tags.report_df)
            self.owndb.owndf.to_csv(os.path.join(DATA_FOLDER, 'owndatabase.csv'), index=False)


        # Crear DataFrame y guardar en un archivo CSV
        file_path = guardar_archivo_output("tags_aplicadas", self.df_reporte_coincidencia_favorita, encabezados=None)

        # Resetear la barra de estado al mensaje por defecto
        self.cleanup_progress_bar()

        # Mostrar mensaje de confirmación con un enlace para abrir el archivo y el resumen final
        self.mostrar_mensaje_confirmacion(file_path, analizados, tageados)



    def update_progress_and_status(self, value=None, current=None, total=None, tageados=None):
        """
        Update the progress bar and status message.

        Parameters:
        - value: Progress value in percentage (optional).
        - current: Current progress value (optional).
        - total: Total value to calculate the percentage (optional).
        - tageados: Number of tagged files (optional).

        If `current` and `total` are provided, `value` is ignored and progress is calculated.
        """
        if current is not None and total is not None:
            value = (current / total) * 100  # Calculate progress as a percentage

        # Check if progress bar exists and update it
        if hasattr(self, 'progress_var') and value is not None:
            self.progress_var.set(int(value))  # Update progress variable
            progress_text = f"Progress: {int(value)}% ({current} de {total} canciones)" if current and total else f"Progress: {int(value)}%"
            self.status_label.config(text=progress_text)

        # Refresh the interface to show updates
        self.root.update_idletasks()

    def mostrar_mensaje_confirmacion(self, file_path, analizados, tageados):
        # Crear una ventana emergente para mostrar el mensaje de confirmación
        popup = tk.Toplevel()
        popup.title("Archivo Guardado")
        popup.geometry("350x250")  # Ajustar el tamaño de la ventana

        # Etiqueta de confirmación de guardado
        label = tk.Label(popup, text="Archivo guardado correctamente.")
        label.pack(pady=10)

        # Mostrar el resumen de archivos analizados y etiquetados
        resumen = f"Archivos analizados: {analizados}\nArchivos tageados: {tageados}"
        resumen_label = tk.Label(popup, text=resumen)
        resumen_label.pack(pady=10)

        # Mostrar la ruta del archivo guardado
        path_label = tk.Label(popup, text=f"Ruta del archivo:\n{file_path}", wraplength=300, justify="center")
        path_label.pack(pady=10)

        # Botón para abrir el archivo
        abrir_button = tk.Button(popup, text="Abrir archivo", command=lambda: self.abrir_archivo(file_path))
        abrir_button.pack(pady=10)

        # Botón para cerrar la ventana emergente
        cerrar_button = tk.Button(popup, text="Cerrar", command=popup.destroy)
        cerrar_button.pack(pady=10)

    def abrir_archivo(self, file_path):
        # Abrir el archivo en el explorador de archivos predeterminado del sistema
        os.startfile(file_path)  # Para Windows

        # Para otros sistemas operativos:
        # macOS: os.system(f'open "{file_path}"')
        # Linux: os.system(f'xdg-open "{file_path}"')

    def borrar_todo(self):
        for archivos in filetofind_list:
            archivos.destroy()
        filetofind_list.clear()

    def createdb(self):
        """Create an instance of the `owndatabase` class and update UI with Treeview."""
        self.setup_progress_bar()

        db_name = simpledialog.askstring("Nombre de la Base de Datos", "Introduce un nombre para la base de datos:")

        if not db_name:  # Si no se introduce un nombre, mostrar un error y detener el proceso
            messagebox.showerror("Error", "Debe introducir un nombre para la base de datos.")

            return


        # Crear una instancia de `owndatabase` solo cuando se llama a este método
        self.owndb = owndatabase(self.update_progress_and_status)
        def tarea_pesada():
            # Llamar al método create_database de owndatabase para crear la base de datos con el nombre proporcionado
            self.owndb.create_database(db_name=db_name)

            # Clean up the progress bar
            self.cleanup_progress_bar()

            # Once the DB is created, show it in the UI
            self.show_db_in_treeview()

        hilo = threading.Thread(target=tarea_pesada)
        hilo.start()

    def comparedb(self):
        self.borrar_todo()  # Clear existing files
        numero_canciones = 0

        lines = self.owndb.owndf['file_path'].tolist()
        tags = self.owndb.owndf


        self.origen_archivos = 'owndb'

        def tarea_pesada():
            self.procesar_archivos(lines, numero_canciones, from_musicbee=True, show_progress=True, origen='OwnDB',
                                   tags=tags)

            # Perform the DataFrame update
            self.owndb.owndf.update(self.archivos_comparado.report_df)


            # Save to CSV
            self.owndb.guardar_base_de_datos()

            # Update the treeview
            self.update_treeview()

        hilo = threading.Thread(target=tarea_pesada)
        hilo.start()

    def update_treeview(self):
        """Destroy and recreate the Treeview with new data."""

        # Destroy the existing Treeview widget, if it exists
        if hasattr(self, 'tree'):
            self.tree.destroy()

        # Call the method to recreate the Treeview with the updated data
        self.show_db_in_treeview()

    def filterdb(self):
        """Open a popup window to filter the database and show filtered results in Treeview."""

        def apply_filters():
            """Apply filters based on user input and show the filtered database."""
            df = self.owndb.owndf.copy()  # Create a copy of the database to filter

            # Apply string filters
            for field, entry in string_filters.items():
                filter_value = entry.get().strip()
                filter_option = string_filter_vars[field].get()  # Get the selected option from the StringVar
                if filter_value:
                    if filter_option == 'contains':
                        df = df[df[field].str.contains(filter_value, case=False, na=False)]
                    elif filter_option == 'equals':
                        df = df[df[field] == filter_value]
                    elif filter_option == 'starts with':
                        df = df[df[field].str.startswith(filter_value, na=False)]
                    elif filter_option == 'ends with':
                        df = df[df[field].str.endswith(filter_value, na=False)]

            # Apply boolean filters
            for field, var in boolean_filters.items():
                selected_option = var.get()
                if selected_option == 'True':
                    df = df[df[field] == True]
                elif selected_option == 'False':
                    df = df[df[field] == False]

            # Show filtered data in Treeview
            self.show_db_in_treeview(df)

        # Popup window
        popup = tk.Toplevel(self.root)
        popup.title("Filter Database")
        popup.geometry("400x400")

        # Dictionary to store filter entries and options
        string_filters = {}
        string_filter_vars = {}  # Store StringVars for the OptionMenus
        boolean_filters = {}

        # Fields for string filters with options like "contains", "equals", etc.
        string_fields = ['title', 'artist', 'genre', 'composer']  # You can add more fields as needed
        for idx, field in enumerate(string_fields):
            tk.Label(popup, text=f"{field.capitalize()}:", font=('Helvetica', 12)).grid(row=idx, column=0, padx=10,
                                                                                        pady=5)
            string_filters[field] = tk.Entry(popup)
            string_filters[field].grid(row=idx, column=1, padx=10, pady=5)

            # Create a StringVar for the dropdown options
            filter_option_var = tk.StringVar(value="contains")
            string_filter_vars[field] = filter_option_var
            filter_option_menu = tk.OptionMenu(popup, filter_option_var, "contains", "equals", "starts with",
                                               "ends with")
            filter_option_menu.grid(row=idx, column=2, padx=10, pady=5)

        # Fields for boolean filters with options like "True", "False", "All"
        boolean_fields = ['Artista encontrado', 'Titulo encontrado', 'Coincidencia perfecta']
        for idx, field in enumerate(boolean_fields):
            tk.Label(popup, text=f"{field.replace('_', ' ').capitalize()}:", font=('Helvetica', 12)).grid(
                row=len(string_fields) + idx, column=0, padx=10, pady=5)

            var = tk.StringVar(value="All")
            boolean_filters[field] = var
            boolean_filter_menu = tk.OptionMenu(popup, var, "All", "True", "False")
            boolean_filter_menu.grid(row=len(string_fields) + idx, column=1, padx=10, pady=5)

        # Apply button
        apply_button = tk.Button(popup, text="Apply Filters", command=apply_filters)
        apply_button.grid(row=len(string_fields) + len(boolean_fields), column=0, columnspan=3, pady=20)

    def show_db_in_treeview(self, filtered_df=None):
        """Display the contents of the filtered or full database in a Treeview widget."""
        df_to_show = filtered_df if filtered_df is not None else self.owndb.owndf

        # The rest of the function remains the same as the original show_db_in_treeview()
        # but using df_to_show instead of self.owndb.owndf to display the filtered data.


        """Display the contents of owndb.owndf in a Treeview widget."""
        if hasattr(self, 'title_frame'):
            self.title_frame.destroy()
        if hasattr(self, 'main_content'):
            self.main_content.destroy()

        # Create a new frame for the Treeview (using title_frame's grid position)
        self.title_frame = tk.Frame(self.root, relief=tk.RAISED, bd=2)
        self.title_frame.grid(row=self.title_frame_row, column=0, rowspan=2, columnspan=self.title_frame_colspan, sticky="nsew")

        # Create the Treeview and hide the first column (tree column)
        self.tree = ttk.Treeview(self.title_frame, show="headings")  # "headings" hides the implicit tree column

        # Define columns from owndf
        columns = list(df_to_show.columns)
        self.tree["columns"] = columns

        self.column_widths = {
            'title': 150,
            'artist': 200,
            'year': 50,
            'genre': 50,
            'composer': 250,
            'file_path': 450,
            'Artista encontrado': 3,
            'Titulo encontrado': 3,
            'Numero de coincidencias': 3,
            'Hay coincidencia preferida': 3,
            'No hay coincidencia preferida': 3,
            'Coincidencia perfecta': 5
        }

        # Define column headings and widths
        for col in columns:
            width = self.column_widths.get(col, 150)  # Default to 150 if the column isn't in the dictionary
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_column(self.tree, _col, False))
            self.tree.column(col, width=width, anchor="w")

        # Insert the data into the Treeview
        for index, row in df_to_show.iterrows():
            self.tree.insert("", "end", values=list(row))

        # Add a vertical scrollbar for the Treeview
        scrollbar = ttk.Scrollbar(self.title_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Grid the Treeview and scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Make sure the title_frame expands as needed
        self.title_frame.grid_rowconfigure(0, weight=1)
        self.title_frame.grid_columnconfigure(0, weight=1)

    def sort_column(self, tree, col, reverse):
        """Sort the Treeview column when a header is clicked."""
        # Fetch the data in the treeview
        data = [(self.convert_type(tree.set(item, col)), item) for item in tree.get_children('')]

        # Sort data
        data.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (_, item) in enumerate(data):
            tree.move(item, '', index)

        # Reverse sort order for next click
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))

    def convert_type(self, value):
        """Convert value to appropriate data type for sorting."""
        try:
            # Try to convert to float (handles both integers and floats)
            return float(value)
        except ValueError:
            # If conversion fails, return the original string
            return value

    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode."""
        self.root.attributes("-fullscreen", False)

    def loaddb(self):
        """Load a CSV file into the owndatabase instance, ensuring it mirrors the characteristics of self.owndf."""
        # Open a file dialog to select the CSV file
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=DATABASE_FOLDER
        )

        if not file_path:
            messagebox.showerror("Error", "No file selected!")
            return

        try:
            # Load the CSV into a DataFrame
            df_loaded = pd.read_csv(file_path)

            # Ensure the loaded DataFrame has the same structure as self.owndf
            expected_columns = ['title', 'artist', 'year', 'genre', 'composer', 'file_path',
                                'Artista encontrado', 'Titulo encontrado', 'Numero de coincidencias',
                                'Hay coincidencia preferida', 'No hay coincidencia preferida',
                                'Coincidencia perfecta']

            # Verify if the CSV has the required columns
            if not all(col in df_loaded.columns for col in expected_columns):
                messagebox.showerror("Error", "The selected file does not have the required columns.")
                return

            # Restore the index and ensure column types are correct
            df_loaded.set_index('file_path', inplace=True, drop=False)
            df_loaded['Artista encontrado'] = df_loaded['Artista encontrado'].astype(bool)
            df_loaded['Titulo encontrado'] = df_loaded['Titulo encontrado'].astype(bool)
            df_loaded['Hay coincidencia preferida'] = df_loaded['Hay coincidencia preferida'].astype(bool)
            df_loaded['No hay coincidencia preferida'] = df_loaded['No hay coincidencia preferida'].astype(bool)
            df_loaded['Coincidencia perfecta'] = df_loaded['Coincidencia perfecta'].astype(bool)

            # Assign the loaded DataFrame to the owndatabase instance
            if self.owndb is None:
                self.owndb = owndatabase()

            self.owndb.owndf = df_loaded
            self.owndb.db_path = file_path

            # Display success message
            messagebox.showinfo("Success", f"Database loaded successfully from {os.path.basename(file_path)}.")

            # Optionally, update the UI to reflect the loaded data
            self.update_treeview()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load the database: {e}")
