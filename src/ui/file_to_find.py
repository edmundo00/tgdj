from tinytag import TinyTag
from tkinter import ttk
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
        # In your class initialization or setup
        self.sizebuttons = [25, 25]  # Set button width and height in text units
        self.padx = 0
        self.pady = 0

        self.leer_tags()

        self.buscar()
        self.representa()

    def representa(self):
        # Determinar color de fondo basado en el número de frame
        self.color_de_fondo = 'whitesmoke' if es_par(self.frame_number) else 'lightgrey'
        # Configurar la altura del frame
        self.configurar_altura_frame()

        if self.artista_coincidencia==0:
            self.representar_datos_archivo()
            self.representar_datos_sin_resultado("NO ARTISTA", "red")
            self.nextframe = self.frame_number + 1
        elif self.titulo_coincidencia==0:
            self.representar_datos_archivo()
            self.representar_datos_sin_resultado("NO TITULO", "blue")
            self.nextframe = self.frame_number + 1
        elif self.perfect_match:
            self.representar_datos_archivo()
            self.representar_datos_perfect_match()
            self.nextframe = self.frame_number + 1
        else:
            self.representar_datos_archivo()
            self.representar_datos_resultado()
            self.nextframe = self.frame_number + 1

    def representar_datos_archivo(self):
        """
        Representa los datos del archivo en la interfaz creando frames para cada columna
        con la altura especificada y colocando los widgets dentro.
        """
        # Crear frames para archivo
        self.frames_archivo = self.crear_frames_columnas(
            self.frames_columnas_archivo, columnas_config['archivo'], self.color_de_fondo, self.framefiles
        )

        # Agregar elementos a los frames de archivo
        elementos_archivo = self.obtener_elementos_archivo()
        self.agregar_elementos_a_frames(self.frames_archivo, elementos_archivo, self.color_de_fondo)

    def representar_datos_resultado(self):
        """
        Representa los datos de los resultados en la interfaz creando frames para cada columna
        con la altura especificada y colocando los widgets dentro.
        """
        # Crear frames para resultados
        self.frames_resultado = self.crear_frames_columnas(
            self.frames_columnas_resultado, columnas_config['resultado'], self.color_de_fondo, self.framedatabase
        )

        # Agregar elementos a los frames de resultados
        self.representar_coincidencias(self.color_de_fondo)

    def representar_datos_perfect_match(self):
        """
        Representa los datos de los resultados en la interfaz creando frames para cada columna
        con la altura especificada y colocando los widgets dentro.
        """
        # Crear frames para resultados
        self.frames_resultado = self.crear_frames_columnas(
            self.frames_columnas_resultado, columnas_config['resultado'], self.color_de_fondo, self.framedatabase
        )

        # Agregar elementos a los frames de resultados
        self.representar_coincidencias(self.color_de_fondo)

    def representar_datos_sin_resultado(self, texto, color_de_fondo):
        """
        Representa los datos de los resultados en la interfaz creando frames para cada columna
        con la altura especificada y colocando los widgets dentro.
        """
        # Crear frames para resultados
        self.frames_resultado = self.crear_frames_columnas(
            self.frames_columnas_resultado, columnas_config['resultado'], self.color_de_fondo, self.framedatabase
        )

        self.mostrar_nada_encontrado(texto, color_de_fondo)


    def configurar_altura_frame(self):
        """Configura la altura del frame según el tipo de coincidencia."""
        self.altura_frame = 25 * (
            1 if self.tipo_de_coincidencia == 2 or len(self.coincidencias) == 0 else len(self.coincidencias)
        )

    def crear_frames_columnas(self, frames_columnas, columnas_config, color_de_fondo, default_frame):
        """Crea los frames para cada columna basado en la configuración dada."""
        frames = {}
        for column in columnas_config:
            description = column['description']
            frames[description] = self._crear_frame_columna(
                frames_columnas.get(description, default_frame), self.frame_number, col=0, width=column['minsize'],
                colour=color_de_fondo)
        return frames

    def mostrar_nada_encontrado(self, texto, color_de_fondo):
        """Muestra 'NADA ENCONTRADO' en las columnas correspondientes."""
        columnas_resultado = ['Titulo', 'Orquesta', 'Cantor', 'Fecha', 'Estilo']
        textos = [texto, '', '', '', '']
        fuente_10 = ('Consolas', 12)

        # Corrected the syntax for the zip and loop
        for descripcion, text in zip(columnas_resultado, textos):
            self._crear_label_en_frame(
                self.frames_resultado[descripcion],
                text=text,
                font=fuente_10,
                anchor='w',
                bg=color_de_fondo,
                row=0,
                column=0
            )

    def representar_coincidencias(self, color_de_fondo):
        """Representa las coincidencias en los frames correspondientes."""
        fuente_10_bold = ('Consolas', 12, "bold")
        fuente_10 = ('Consolas', 12)
        for counter, (_, row) in enumerate(self.coincidencias.iterrows()):
            if isinstance(row, pd.Series) and 'audio30' in row and 'audio10' in row:
                # Añadir checkbutton
                self._crear_checkbutton(self.frames_resultado['Checkbox'], counter)

                # Agregar elementos a los frames
                elementos = self.obtener_elementos_coincidencia(row, counter)
                self.agregar_elementos_a_frames(self.frames_resultado, elementos, color_de_fondo)

        if self.hay_coincidencia_preferida:
            self.activar_checkbox(self.coincidencia_preferida)

    def obtener_elementos_coincidencia(self, row, counter):
        """Obtiene los elementos a representar por cada coincidencia."""
        return [
            {'tipo': 'label', 'texto': row['titulo'], 'row': counter,'descripcion': 'Titulo', 'frame': self.frames_resultado['Titulo'],
             'anchor': "w"},
            {'tipo': 'label', 'texto': row['artista'],'row': counter, 'descripcion': 'Orquesta',
             'frame': self.frames_resultado['Orquesta'], 'anchor': "w"},
            {'tipo': 'label', 'texto': row['cantor'], 'row': counter,'descripcion': 'Cantor', 'frame': self.frames_resultado['Cantor'],
             'anchor': "w"},
            {'tipo': 'label', 'texto': row['estilo'],'row': counter, 'descripcion': 'Estilo', 'frame': self.frames_resultado['Estilo'],
             'anchor': "w"},
            {'tipo': 'label', 'texto': row['fecha'],'row': counter, 'descripcion': 'Fecha', 'frame': self.frames_resultado['Fecha'],
             'anchor': "w"},
            {'tipo': 'button', 'frame': self.frames_resultado['Info'], 'row': counter, 'image': self.info_icon,
             'command': lambda r=row: self.show_popup_db(r)},
            {'tipo': 'play_button', 'frame': self.frames_resultado['Play_30'], 'link': link_to_music(row['audio30']),
             'row': counter, 'column': 0},
            {'tipo': 'play_button', 'frame': self.frames_resultado['Play_10'], 'link': link_to_music(row['audio10']),
             'row': counter, 'column': 0},
            {'tipo': 'stop_button', 'frame': self.frames_resultado['Pausa'], 'row': counter, 'column': 0},
        ]

    def obtener_elementos_archivo(self):
        """Obtiene los elementos a representar para los frames de archivo."""
        return [
            {'tipo': 'button', 'frame': self.frames_archivo.get('Info'), 'row': 0, 'image': self.info_icon,
             'command': self.show_popup_file},
            {'tipo': 'label', 'texto': self.tags.title, 'row': 0, 'descripcion': 'Titulo',
             'frame': self.frames_archivo.get('Titulo'), 'anchor': "w"},
            {'tipo': 'label', 'texto': self.artists1, 'row': 0, 'descripcion': 'Orquesta',
             'frame': self.frames_archivo.get('Orquesta'), 'anchor': "w"},
            {'tipo': 'label', 'texto': self.artists2, 'row': 0, 'descripcion': 'Cantor',
             'frame': self.frames_archivo.get('Cantor'), 'anchor': "w"},
            {'tipo': 'label', 'texto': self.tags.year, 'row': 0, 'descripcion': 'Fecha',
             'frame': self.frames_archivo.get('Fecha'), 'anchor': "w"},
            {'tipo': 'play_button', 'frame': self.frames_archivo.get('Play'), 'link': self.ruta_archivo, 'row': 0,
             'column': 0},
            {'tipo': 'stop_button', 'frame': self.frames_archivo.get('Pausa'), 'row': 0, 'column': 0},
        ]

    def agregar_elementos_a_frames(self, frames, elementos, color_de_fondo):
        """Agrega los elementos a los frames correspondientes."""
        for elemento in elementos:
            if elemento['tipo'] == 'label':
                self._crear_label_en_frame(
                    elemento['frame'], text=elemento['texto'],
                    font=('Consolas', 12, "bold") if elemento['descripcion'] == 'Titulo' else ('Consolas', 12),
                    bg=color_de_fondo, anchor=elemento['anchor'], row=elemento['row'],
                    column=elemento.get('column', 0)
                )
            elif elemento['tipo'] == 'button':
                self._crear_button_en_frame(
                    elemento['frame'], row=elemento['row'], image=elemento['image'],
                    command=elemento['command'], bg=elemento.get('bg', color_de_fondo)
                )
            elif elemento['tipo'] == 'play_button':
                self._crear_play_button_on_frame(
                    elemento['frame'], elemento['link'],
                    row=elemento['row'], column=elemento['column'], bg=color_de_fondo
                )
            elif elemento['tipo'] == 'stop_button':
                self._crear_stop_button_on_frame(
                    elemento['frame'], row=elemento['row'], column=elemento['column'], bg=color_de_fondo
                )
    def _crear_frame_columna(self, parent, row, col, width, colour):
        """Create a frame with fixed height but flexible width that can expand with the window."""
        frame = tk.Frame(parent, height=self.altura_frame, width=width, bg=colour)
        frame.grid(row=row, column=col, sticky="nsew")  # Use sticky 'nsew' to expand in all directions

        # Allow horizontal expansion by configuring column weight and setting propagate False if needed
        frame.grid_propagate(False)  # Prevent resizing due to internal content
        parent.grid_columnconfigure(col, weight=1)  # Set weight to allow expansion horizontally
        parent.grid_rowconfigure(row, weight=1)  # Optional: allow vertical expansion

        return frame

    def _crear_label_en_frame(self, frame, text, font, bg, anchor, row=0, column=0):
        """Crea un label dentro del frame dado, utilizando grid."""
        label = tk.Label(frame, text=text, font=font, bg=bg, anchor=anchor)
        label.grid(row=row, column=column, sticky="ew", padx=self.padx, pady=self.pady)
        texto_debug = f'creando label en fila {row} columna {column} con el texto {text}'
        # Configure the frame's grid to expand the column
        frame.grid_columnconfigure(column, weight=1)

    def _crear_button_en_frame(self, frame, text=None, image=None, command=None, bg=None, row=0, column=0):
        """Crea un botón dentro del frame dado, utilizando grid."""
        # Use self.sizebuttons to set the width and height
        button = tk.Button(
            frame,
            text=text,
            image=image,
            borderwidth=0,  # Eliminar borde
            highlightthickness=0,  # Eliminar borde de resaltado
            relief="flat",  # Sin relieve
            command=command,
            bg=bg,
            width=self.sizebuttons[0],  # Width from self.sizebuttons
            height=self.sizebuttons[1]  # Height from self.sizebuttons
        )

        # Place the button in the grid
        button.grid(row=row, column=column, sticky="ne", padx=self.padx, pady=self.pady)

        return button

    def _crear_checkbutton(self, parent, counter):
        var = tk.BooleanVar()
        self.vars.append(var)
        checkbutton = tk.Checkbutton(
            parent,
            variable=var,
            command=lambda i=counter: self.on_checkbox_toggle(i),
        )
        checkbutton.grid(row=counter, column=0, sticky="ew", padx=self.padx,
                         pady=self.pady)  # Adjust padding for visual height control
        self.checkbuttons.append(checkbutton)
        # Ensure the GUI is updated to get the correct size

    def _crear_play_button_on_frame(self, frame, music_link, row, column, bg):
        """Crea un botón de reproducción dentro del frame dado, utilizando grid."""
        play_button = tk.Button(
            frame,
            image=self.play_icon,
            borderwidth=0,  # Eliminar borde
            highlightthickness=0,  # Eliminar borde de resaltado
            relief="flat",  # Sin relieve
            command=lambda: self.play_music(music_link),
            bg=bg,
            width=self.sizebuttons[0],  # Width from self.sizebuttons
            height=self.sizebuttons[1]  # Height from self.sizebuttons
        )
        play_button.grid(row=row, column=column, sticky="ne", padx=self.padx, pady=self.pady)

    def _crear_stop_button_on_frame(self, frame, row, column, bg):
        """Crea un botón de parada dentro del frame dado, utilizando grid."""
        stop_button = tk.Button(
            frame,
            image=self.stop_icon,
            borderwidth=0,  # Eliminar borde
            highlightthickness=0,  # Eliminar borde de resaltado
            relief="flat",  # Sin relieve
            command=stop_music,  # Assuming stop_music is a method of the class
            bg=bg,
            width=self.sizebuttons[0],  # Width from self.sizebuttons
            height=self.sizebuttons[1]  # Height from self.sizebuttons
        )
        stop_button.grid(row=row, column=column, sticky="ne", padx=self.padx, pady=self.pady)

    def leer_tags(self):
        self.tags = TinyTag.get(self.ruta_archivo)
        self.artists1, self.artists2 = separar_artistas(self.tags.artist)


    def buscar(self):
        tag = self.tags
        self.hay_coincidencia_preferida = False
        self.coincidencia_preferida = 0
        self.tipo_de_coincidencia = 0
        artista_original, cantor_original = separar_artistas(tag.artist)
        artista_buscar_min = unidecode(artista_original).lower()

        # First, try to find an exact match
        artista_key = next((key for key in self.dic_art if key == artista_original), None)
        self.artista_coincidencia = 3

        if not artista_key:
            # First, try to find an good match
            artista_key = next((key for key in self.dic_art if key == artista_buscar_min), None)
            self.artista_coincidencia = 2

        # If no exact match is found, try to find a partial match
        if not artista_key:
            artista_key = next((key for key in self.dic_art if artista_buscar_min in key), None)
            self.artista_coincidencia = 1

        if not artista_key:
            artista_key = contain_most_words_in_dic(self.dic_art, artista_buscar_min)
            if artista_key is not None:
                artista_coincidencia = 1
            else:
                self.artista_coincidencia = 0
                self.resultado = 'Artista no encontrado'
                self.coincidencias = self.db.iloc[0:0]
                return

        # DEVULEVE LA BASE DE DATOS CON TODAS LAS COMLUMNAS QUE CORRENSPONDEN A LA ORQUESTA

        if isinstance(artista_key, str):
            # If it's a string, take the single DataFrame
            artist_songs = self.dic_art[artista_key]
        elif isinstance(artista_key, list):
            # If it's a list of strings, concatenate the DataFrames
            artist_songs = pd.concat([self.dic_art[key] for key in artista_key if key in self.dic_art])
        else:
            # Handle unexpected types (optional)
            raise ValueError("artista_key must be a string or a list of strings")


        self.titulo_coincidencia, database_titulo = buscar_titulo(artist_songs, tag)

        if self.titulo_coincidencia==0:
            self.resultado = 'Titulo no encontrado'
            self.coincidencias = self.db.iloc[0:0]
            return



        # Get a dictionary of boolean matches for all tags
        self.bool_coincidencias , self.perfect_match = compare_tags(self.artista_coincidencia, self.titulo_coincidencia, database_titulo, tag)

        self.coincidencias = database_titulo


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
            label_etiqueta.grid(row=i, column=0, padx=self.padx, pady=self.pady, sticky="w")

            # Create label for the tag data
            label_dato = tk.Label(popup, text=dato, anchor="w", justify="left", font=("Helvetica", 12))
            label_dato.grid(row=i, column=1, padx=self.padx, pady=self.pady, sticky="w")

        # Add a button to close the popup
        close_button = tk.Button(popup, text="Close", command=popup.destroy)
        close_button.grid(row=len(etiquetas_datos), column=0, padx=self.padx, pady=self.pady, sticky="w")

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
            label_etiqueta.grid(row=i, column=0, padx=self.padx, pady=self.pady, sticky="w")

            # Ensure dato is a string, or convert it if necessary
            if dato is None:
                dato = ""  # Convert None to an empty string
            elif not isinstance(dato, str):
                dato = str(dato)  # Convert other types to string

            # Create entry for the tag data
            entry_dato = tk.Entry(popup, justify="left", font=("Helvetica", 12), width=100)
            entry_dato.insert(0, dato)  # Insert text into the entry
            entry_dato.grid(row=i, column=1, padx=self.padx, pady=self.pady, sticky="w")
            self.entry_dato_lista.append(entry_dato)

        # Add a button to close the popup
        close_button = tk.Button(popup, text="Close", command=popup.destroy)
        close_button.grid(row=len(etiquetas_datos), column=0, padx=self.padx, pady=self.pady, sticky="w")

        update_tags_button = tk.Button(popup, text="Update tags", command=lambda: self.leer_entredas_y_tagear(popup))
        update_tags_button.grid(row=len(etiquetas_datos), column=1, padx=self.padx, pady=self.pady, sticky="w")

        # Crear un marco inferior con un color de fondo diferente y borde grueso usando grid
        bottom_frame = tk.Frame(popup, bg="#e0e0e0", bd=5, relief="ridge")
        bottom_frame.grid(row=len(etiquetas_datos) + 1, column=0, columnspan=2, padx=self.padx, pady=self.pady, sticky="nsew")

        # Expandir el bottom_frame al cambiar el tamaño del popup
        popup.grid_rowconfigure(len(etiquetas_datos) + 1, weight=1)
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_columnconfigure(1, weight=1)

        # Encabezado dentro del bottom_frame
        header_label = tk.Label(bottom_frame, text="Base de Datos", font=("Helvetica", 14, "bold"), bg="#e0e0e0")
        header_label.grid(row=0, column=0, columnspan=4, padx = self.padx, pady=self.pady)

        def searchdb():
            def update_table():
                # Obtener filtros
                title_filter = title_entry.get().lower()
                artist_filter = artist_var.get()
                cantor_filter = cantor_var.get()
                start_date = start_date_entry.get()
                end_date = end_date_entry.get()

                # Filtrar datos
                filtered_db = self.db[
                    self.db['titulo'].str.lower().str.contains(title_filter, na=False) &
                    (self.db['artista'] == artist_filter if artist_filter != 'Todos' else True) &
                    (self.db['cantor'] == cantor_filter if cantor_filter != 'Todos' else True) &
                    (self.db['fecha'] >= start_date if start_date else True) &
                    (self.db['fecha'] <= end_date if end_date else True)
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
                    filtered_cantors = self.db['cantor'].dropna().unique().tolist()
                else:
                    filtered_cantors = self.db[self.db['artista'] == selected_artist]['cantor'].dropna().unique().tolist()

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
            tk.Label(bottom_frame, text="Titulo:", font=font_style, bg="#e0e0e0").grid(row=1, column=0, padx=self.padx,
                                                                                       pady=self.pady, sticky="w")
            title_entry = tk.Entry(bottom_frame, font=font_style)
            title_entry.grid(row=1, column=1, padx=self.padx, pady=self.pady, sticky="ew")
            title_entry.bind("<KeyRelease>", lambda event: update_table())

            # Filtro de Artista
            tk.Label(bottom_frame, text="Artista:", font=font_style, bg="#e0e0e0").grid(row=2, column=0, padx=self.padx,
                                                                                        pady=self.pady, sticky="w")
            artist_var = tk.StringVar(bottom_frame)
            artist_var.set("Todos")
            artist_dropdown = ttk.Combobox(bottom_frame, textvariable=artist_var, font=font_style)
            artist_dropdown['values'] = ['Todos'] + sorted(self.db['artista'].dropna().unique().tolist())
            artist_dropdown.grid(row=2, column=1, padx=self.padx, pady=self.pady, sticky="ew")
            artist_var.trace("w", update_cantor_dropdown)

            # Filtro de Cantor
            tk.Label(bottom_frame, text="Cantor:", font=font_style, bg="#e0e0e0").grid(row=3, column=0, padx=self.padx,
                                                                                       pady=self.pady, sticky="w")
            cantor_var = tk.StringVar(bottom_frame)
            cantor_var.set("Todos")
            cantor_dropdown = ttk.Combobox(bottom_frame, textvariable=cantor_var, font=font_style)
            cantor_dropdown['values'] = ['Todos'] + sorted(self.db['cantor'].dropna().unique().tolist())
            cantor_dropdown.grid(row=3, column=1, padx=self.padx, pady=self.pady, sticky="ew")
            cantor_var.trace("w", on_filter_change)

            # Filtro de Fecha
            tk.Label(bottom_frame, text="Fecha desde:", font=font_style, bg="#e0e0e0").grid(row=4, column=0, padx=self.padx,
                                                                                            pady=self.pady, sticky="w")
            start_date_entry = tk.Entry(bottom_frame, font=font_style)
            start_date_entry.grid(row=4, column=1, padx=self.padx, pady=self.pady, sticky="ew")
            start_date_entry.bind("<KeyRelease>", lambda event: update_table())

            tk.Label(bottom_frame, text="Fecha hasta:", font=font_style, bg="#e0e0e0").grid(row=4, column=2, padx=self.padx,
                                                                                            pady=self.pady, sticky="w")
            end_date_entry = tk.Entry(bottom_frame, font=font_style)
            end_date_entry.grid(row=4, column=3, padx=self.padx, pady=self.pady, sticky="ew")
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

        # Destruir frames en 'archivo'
        for column in columnas_config['archivo']:
            description = str(column['description'])
            self.frames_archivo[description].destroy()

        # Destruir frames en 'resultado'
        for column in columnas_config['resultado']:
            description = str(column['description'])
            self.frames_resultado[description].destroy()



            

