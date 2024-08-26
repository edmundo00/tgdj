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

class Ventana:
    def __init__(self, root):
        self.data_store = Database()
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

        # Define a list of icon names corresponding to the keys in icon_paths
        icon_names = ['archivo', 'directorio', 'correr', 'transfer', 'trash', 'searchdb', 'presentacion', 'playlist',
                      'convert_playlist']

        # Dynamically create and assign PhotoImage objects to instance variables
        for icon_name in icon_names:
            setattr(self, f"{icon_name}_icon", tk.PhotoImage(file=icon_paths[icon_name]))


        self.load_button_music_file = tk.Button(self.icon_bar, image=self.archivo_icon, relief=tk.FLAT,
                                                command=self.load_music_file)
        self.load_button_music_file.grid(row=0, column=0, padx=2, pady=2)
        self.load_button_music_folder = tk.Button(self.icon_bar, image=self.directorio_icon, relief=tk.FLAT,
                                                  command=self.load_music_folder)
        self.load_button_music_folder.grid(row=0, column=1, padx=2, pady=2)
        self.save_button = tk.Button(self.icon_bar, image=self.correr_icon, relief=tk.FLAT)
        self.save_button.grid(row=0, column=2, padx=2, pady=2)
        self.transfer_button = tk.Button(self.icon_bar, image=self.transfer_icon, relief=tk.FLAT,
                                         command=self.aplicartags)
        self.transfer_button.grid(row=0, column=3, padx=2, pady=2)
        self.trash_button = tk.Button(self.icon_bar, image=self.trash_icon, relief=tk.FLAT, command=self.borrar_todo)
        self.trash_button.grid(row=0, column=4, padx=2, pady=2)
        self.trash_button = tk.Button(self.icon_bar, image=self.searchdb_icon, relief=tk.FLAT, command=self.searchdb)
        self.trash_button.grid(row=0, column=5, padx=2, pady=2)
        self.presentation_button = tk.Button(self.icon_bar, image=self.presentacion_icon, relief=tk.FLAT,
                                             command=self.open_presentation_popup)
        self.presentation_button.grid(row=0, column=6, padx=2, pady=2)
        self.playlist_button = tk.Button(self.icon_bar, image=self.playlist_icon, relief=tk.FLAT,
                                         command=self.open_playlist)
        self.playlist_button.grid(row=0, column=7, padx=2, pady=2)
        self.convert_playlist_button = tk.Button(self.icon_bar, image=self.convert_playlist_icon, relief=tk.FLAT,
                                                 command=self.convert_playlist)
        self.convert_playlist_button.grid(row=0, column=8, padx=2, pady=2)


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
            new_filetofind = FILETOFIND(self.subframe1, self.subframe2, file_path, numero_canciones, self.root)
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
                                                        numero_canciones, self.root)
                            numero_canciones += 1
                            filetofind_list.append(new_filetofind)
                        else:
                            modified_path = dropbox_path + line.split("Dropbox", 1)[1]
                            if os.path.exists(modified_path):
                                new_filetofind = FILETOFIND(self.subframe1, self.subframe2, modified_path,
                                                            numero_canciones, self.root)
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
                    new_filetofind = FILETOFIND(self.subframe1, self.subframe2, file_path, numero_canciones, self.root)
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
