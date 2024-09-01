import pandas as pd
from tinytag import TinyTag
import tkinter as tk
from tkinter import ttk
import pygame
from src.utils.utils import *
from src.config.database import Database


class FILETOFIND:

    def __init__(self, framefiles, framedatabase, frames_columnas_archivo, frames_columnas_resultado, ruta_archivo, frame_number, root):
        # print(db)
        self.data_store = Database()
        self.db = self.data_store.get_db()
        self.dic_art = self.data_store.get_dic_art()
        self.root = root
        self.play_icon = tk.PhotoImage(file=icon_paths['play'])
        self.stop_icon = tk.PhotoImage(file=icon_paths['stop'])
        self.info_icon = tk.PhotoImage(file=icon_paths['info'])
        self.ruta_archivo = ruta_archivo
        self.vars = []
        self.checkbuttons = []
        self.frame_number = frame_number
        self.framefiles = framefiles
        self.framedatabase = framedatabase
        self.frames_columnas_archivo = frames_columnas_archivo
        self.frames_columnas_resultado = frames_columnas_resultado  # Asegúrate

        self.leer_tags()

        self.buscar()

        self.representar_datos()

    def representar_datos(self):
        """
        Representa los datos en la interfaz creando frames para cada columna
        con la altura especificada y colocando los widgets dentro.
        """
        # Determinar color de fondo basado en el número de frame
        color_de_fondo = 'whitesmoke' if es_par(self.frame_number) else 'lightgrey'

        # Definir colores para diferentes tipos de coincidencias
        colores_por_coincidencia = {
            0: 'palegreen',
            1: 'lime',
            2: 'darkgray',
            3: 'gold',
            4: 'aquamarine',
            5: 'red'
        }

        # Configura la altura del frame basado en el tipo de coincidencia
        self.altura_frame = 27 * (
            1 if self.tipo_de_coincidencia == 2 or len(self.coincidencias) == 0 else len(self.coincidencias)
        )

        # Estilos de fuente
        fuente_10_bold = ('Consolas', 11, "bold")
        fuente_10 = ('Consolas', 11)

        # Determinar la fila actual usando numero_canciones
        current_row = self.frame_number

        # Crear frames una sola vez antes del bucle
        frames = {}
        for column in columnas_config['resultado']:
            description = column['description']
            frames[description] = self._crear_frame_columna(
                self.frames_columnas_resultado.get(description, self.framedatabase), current_row, col=0, width=column['minsize'], colour=color_de_fondo)
        frames_archivo = {}
        for column in columnas_config['archivo']:
            description = column['description']
            frames_archivo[description] = self._crear_frame_columna(
                self.frames_columnas_archivo.get(description, self.framefiles), current_row, col=0, width=column['minsize'], colour=color_de_fondo)



        # Manejar la visualización de coincidencias o "NADA ENCONTRADO"
        if self.coincidencias.empty:
            columnas_resultado = ['Checkbox', 'Titulo', 'Orquesta', 'Cantor', 'Estilo', 'Fecha', 'Info', 'Play_30']
            for i, descripcion in enumerate(columnas_resultado):
                text = "NADA ENCONTRADO" if descripcion == 'Titulo' else ""
                self._crear_label_en_frame(frames_archivo['Titulo'], text=text, font=fuente_10, anchor='w', bg=color_de_fondo, row=0, column=0)


        else:
            # Iterar sobre las coincidencias
            for counter, (_, row) in enumerate(self.coincidencias.iterrows()):
                if isinstance(row, pd.Series) and 'audio30' in row and 'audio10' in row:
                    # Añadir checkbutton al frame correspondiente
                    self._crear_checkbutton(frames['Checkbox'], counter)

                    # Datos de las labels para la fila de coincidencias
                    labels_data = [
                        (row['titulo'], 'Titulo', frames['Titulo'], "w"),
                        (row['artista'], 'Orquesta', frames['Orquesta'], "w"),
                        (row['cantor'], 'Cantor', frames['Cantor'], "w"),
                        (row['estilo'], 'Estilo', frames['Estilo'], "w"),
                        (row['fecha'], 'Fecha', frames['Fecha'], "w"),
                    ]

                    # Añadir labels a los frames correspondientes
                    for text, description, frame_columna, anchor in labels_data:
                        self._crear_label_en_frame(
                            frame_columna, text=text,
                            font=fuente_10_bold if description == 'Titulo' else fuente_10,
                            bg=color_de_fondo, anchor=anchor, row=counter, column=0
                        )

                    # Añadir botones de información, reproducción y parada
                    self._crear_button_en_frame(
                        frames['Info'], row=counter, image=self.info_icon,
                        command=lambda r=row: self.show_popup_db(r), bg=color_de_fondo
                    )
                    self._crear_play_button_on_frame(
                        frames['Play_30'], link_to_music(row['audio30']),
                        row=counter, column=0, bg=color_de_fondo
                    )
                    self._crear_play_button_on_frame(
                        frames['Play_10'], link_to_music(row['audio10']),
                        row=counter, column=0, bg=color_de_fondo
                    )
                    self._crear_stop_button_on_frame(frames['Pausa'], row=counter, column=0, bg=color_de_fondo)

                else:
                    print(f"Unexpected row format or missing columns: {row}")

            if self.hay_coincidencia_preferida:
                self.activar_checkbox(self.coincidencia_preferida)

        # Add the button to the 'Info' frame
        if 'Info' in frames_archivo:
            self._crear_button_en_frame(
                frames_archivo['Info'],
                image=self.info_icon,
                command=self.show_popup_file,
                bg=color_de_fondo
            )

        # Define data for the labels to be added to the file information frames
        file_labels_data = [
            (self.tags.title, 'Titulo', None),
            (self.artists1, 'Orquesta', None),
            (self.artists2, 'Cantor', None),
            (self.tags.year, 'Fecha', 11),
        ]

        # Add labels to the corresponding frames
        for text, description, char_width in file_labels_data:
            if description in frames_archivo:
                self._crear_label_en_frame(
                    frames_archivo[description],
                    text=text,
                    font=fuente_10_bold if description == 'Titulo' else fuente_10,
                    bg=color_de_fondo,
                    anchor="w",
                    row=0,
                    column=0
                )

    # Helper Methods

    def _crear_frame_columna(self, parent, row, col, width, colour):
        """Crea un frame con la altura fija especificada para la columna y un ancho fijo."""
        frame = tk.Frame(parent, height=self.altura_frame, width=width, bg=colour)  # Set fixed width and height
        frame.grid(row=row, column=col, sticky="nsew")
        frame.grid_propagate(False)  # Prevent the frame from resizing to fit its contents
        frame.pack_propagate(False)  # Additional protection to prevent resizing
        return frame

    def _crear_label_en_frame(self, frame, text, font, bg, anchor, row=0, column=0):
        """Crea un label dentro del frame dado, utilizando grid."""
        label = tk.Label(frame, text=text, font=font, bg=bg, anchor=anchor)
        label.grid(row=row, column=column, sticky="w", padx=5, pady=5)

    def _crear_button_en_frame(self, frame, text=None, image=None, command=None, bg=None, row=0, column=0):
        """Crea un botón dentro del frame dado, utilizando grid."""
        button = tk.Button(frame, text=text, image=image, command=command, bg=bg)
        button.grid(row=row, column=column, sticky="ew", padx=5, pady=5)

    def _crear_checkbutton(self, parent, counter):
        var = tk.BooleanVar()
        self.vars.append(var)
        checkbutton = tk.Checkbutton(parent, variable=var, command=lambda i=counter: self.on_checkbox_toggle(i))
        checkbutton.grid(row=counter, column=0, sticky="nw", padx=1, pady=1)
        self.checkbuttons.append(checkbutton)

    def _crear_play_button_on_frame(self, frame, music_link, row, column, bg):
        """Crea un botón de reproducción dentro del frame dado, utilizando grid."""
        play_button = tk.Button(frame, image=self.play_icon, relief=tk.FLAT,
                                command=lambda: self.play_music(music_link), bg=bg)
        play_button.grid(row=row, column=column, sticky="e", padx=1, pady=1)

    def _crear_stop_button_on_frame(self, frame, row, column, bg):
        """Crea un botón de parada dentro del frame dado, utilizando grid."""
        stop_button = tk.Button(frame, image=self.stop_icon, relief=tk.FLAT,
                                command=stop_music, bg=bg)
        stop_button.grid(row=row, column=column, sticky="e", padx=1, pady=1)

    def _crear_play_button_file(self, parent, archivo, counter, bg):
        """Crea botones de reproducción y parada para un archivo."""
        playmusic_button = tk.Button(parent, image=self.play_icon, relief=tk.FLAT,
                                     command=lambda fp=archivo: self.play_music(fp), bg=bg)
        playmusic_button.grid(row=0, column=counter, sticky="nw", padx=2, pady=2)
        stopmusic_button = tk.Button(parent, image=self.stop_icon, relief=tk.FLAT, command=stop_music, bg=bg)
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
        artista_buscar  = unidecode(artista_original).lower()
        
        # First, try to find an exact match
        artista_key = next((key for key in self.dic_art if key == artista_buscar), None)

        # If no exact match is found, try to find a partial match
        if not artista_key:
            artista_key = next((key for key in self.dic_art if artista_buscar in key), None)
        
        if not artista_key:
            self.resultado = 'Artista no encontrado'
            self.coincidencias = self.db.iloc[0:0]
            return

        artist_songs = self.dic_art[artista_key]
        
        # Get a dictionary of boolean matches for all tags
        coincidencias = compare_tags(artist_songs, tag)

        # Check for title match
        if coincidencias[TagLabels.TITULO].any() == True:
            self.resultado = 'Titulo encontrado'
            self.tipo_de_coincidencia = 0
            dbet = artist_songs[coincidencias[TagLabels.TITULO]]

            # Check for year match
            if coincidencias[TagLabels.ANO].any() == True:
                self.resultado = 'Año encontrado'
                self.tipo_de_coincidencia = 1
                self.coincidencia_preferida = dbet.index[coincidencias[TagLabels.ANO]].min()
                self.hay_coincidencia_preferida = True
            else:
                self.resultado = 'Año no encontrado'

        # Check for partial title word matches (is a list with the index of rows with common words)
        elif coincidencias[TagLabels.TITULO_PALABRAS]:
            self.resultado = 'Palabras del titulo encontrado'
            self.tipo_de_coincidencia = 3
            dbet = artist_songs.loc[coincidencias[TagLabels.TITULO_PALABRAS]]

            # Check for year match in the filtered data
            if coincidencias[TagLabels.ANO].any():
                self.resultado = 'Año encontrado'
                self.tipo_de_coincidencia = 4
                self.coincidencia_preferida = dbet.index[coincidencias[TagLabels.ANO]].min()
                self.hay_coincidencia_preferida = True
            else:
                self.resultado = 'Año no encontrado'
        else:
            self.resultado = 'Titulo o palabras del titulo no encontrado'
            self.coincidencias = self.db.iloc[0:0]
            return

        # If we found a year match and the whole tag matches exactly, update the coincidence type
        if self.tipo_de_coincidencia == 1 and coincidencias[TagLabels.TODO].any() == True:
            dbet = dbet[coincidencias[TagLabels.TODO]]
            if len(dbet) == 1:
                self.tipo_de_coincidencia = 2
                self.hay_coincidencia_preferida = False

        # If the title is the only match and there's exactly one match, set the preferred match
        if self.tipo_de_coincidencia == 0 and len(dbet) == 1:
            self.hay_coincidencia_preferida = True
            self.coincidencia_preferida = dbet.index[0]

        # Set the filtered matches as the final coincidences
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
