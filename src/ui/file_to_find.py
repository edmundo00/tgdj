from tinytag import TinyTag
from tkinter import ttk
from src.utils.utils import *
from src.config.database import Database
from datetime import datetime


class FILETOFIND:

    def __init__(self, lista_frames, ruta_archivo, frame_number, lista_checks):
        # print(db)
        self.data_store = Database()
        self.db = self.data_store.get_db()
        self.dic_art = self.data_store.get_dic_art()
        self.show_date_checked, self.show_perfect_matches, self.show_artist_not_found, \
            self.show_title_not_found, self.show_remaining, self.direct_comparison = lista_checks
        self.ruta_archivo = ruta_archivo
        self.frame_number = frame_number
        self.artist_not_found = False
        self.title_not_found = False


        if not self.direct_comparison:
            self.play_icon = tk.PhotoImage(file=icon_paths['play'])
            self.stop_icon = tk.PhotoImage(file=icon_paths['stop'])
            self.info_icon = tk.PhotoImage(file=icon_paths['info'])
            self.vars = []
            self.checkbuttons = []
            self.framefiles, self.framedatabase, self.frames_columnas_archivo, self.frames_columnas_resultado = lista_frames
            # In your class initialization or setup
            self.sizebuttons = [25, 25]  # Set button width and height in text units
            self.padx = 0
            self.pady = 0


        self.perfect_match = False
        # Initialize checkbutton states with default values
        # Estados de los checkbuttons

        self.leer_tags()
        self.buscar()

        if self.direct_comparison:
            self.nextframe = self.frame_number
        else:
            self.representa()

    def reporte(self):
        """
        Genera un reporte de las variables más importantes y las imprime, además de retornarlas.

        Returns:
            pd.DataFrame: Un DataFrame con las variables clave del reporte.
        """
        reporte_data = {
            "Artista encontrado": self.artist_not_found,
            "Titulo encontrado": self.title_not_found,
            "Numero de coincidencias": len(self.coincidencias) if self.coincidencias is not None else 0,
            "Hay coincidencia preferida": self.hay_coincidencia_preferida,
            "No hay coincidencia preferida": self.no_hay_coincidencia_preferida,
            "Coincidencia perfecta": self.perfect_match
        }

        return reporte_data

    def representa(self):
        # Determinar color de fondo basado en el número de frame
        self.color_de_fondo = 'whitesmoke' if es_par(self.frame_number) else 'lightgrey'
        # Configurar la altura del frame
        self.configurar_altura_frame()

        # Step 1: Check for coincidences and perfect matches
        is_perfect_match = self.perfect_match

        # Step 2: Adjust display logic based on checkbutton states
        if self.artist_not_found:
            if self.show_artist_not_found:
                # Show data when artist is not found and the respective checkbox is checked
                self.representar_datos_archivo()
                self.representar_datos_sin_resultado("NO ARTISTA", "red")
                self.nextframe = self.frame_number + 1
            else:
                self.nextframe = self.frame_number

        elif self.title_not_found:
            if self.show_title_not_found:
                # Show data when title is not found and the respective checkbox is checked
                self.representar_datos_archivo()
                self.representar_datos_sin_resultado("NO TITULO", "blue")
                self.nextframe = self.frame_number + 1
            else:
                self.nextframe = self.frame_number

        elif is_perfect_match:
            if self.show_perfect_matches:
                # Show perfect matches if the checkbox is checked
                self.representar_datos_archivo()
                self.representar_datos_resultado()
                self.nextframe = self.frame_number + 1
            else:
                self.nextframe = self.frame_number

        else:
            if self.show_remaining:
                # Representar todos los datos restantes
                self.representar_datos_archivo()
                self.representar_datos_resultado()
                self.nextframe = self.frame_number + 1
            else:
                self.nextframe = self.frame_number

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
        for counter, ((_, row_coincidencia), (_, row_color)) in enumerate(
                zip(self.coincidencias.iterrows(), self.colores_labels.iterrows())):
            if isinstance(row_coincidencia, pd.Series) and 'audio30' in row_coincidencia and 'audio10' in row_coincidencia:
                # Añadir checkbutton
                self._crear_checkbutton(self.frames_resultado['Checkbox'], counter)

                # Agregar elementos a los frames
                elementos = self.obtener_elementos_coincidencia(row_coincidencia, counter)
                self.agregar_elementos_a_frames(self.frames_resultado, elementos, color_de_fondo)

        if self.hay_coincidencia_preferida:
            self.activar_checkbox(self.coincidencia_preferida)

    def obtener_elementos_coincidencia(self, row, counter):
        """Obtiene los elementos a representar por cada coincidencia."""

        colores = self.colores_labels.iloc[counter]

        return [
            {'tipo': 'label', 'texto': row['titulo'], 'row': counter,'descripcion': 'Titulo', 'frame': self.frames_resultado['Titulo'],
             'anchor': "w", 'colour': colores['TITULO']},
            {'tipo': 'label', 'texto': row['artista'],'row': counter, 'descripcion': 'Orquesta',
             'frame': self.frames_resultado['Orquesta'], 'anchor': "w", 'colour': colores['ORQUESTA']},
            {'tipo': 'label', 'texto': row['cantor'], 'row': counter,'descripcion': 'Cantor', 'frame': self.frames_resultado['Cantor'],
             'anchor': "w", 'colour': colores['CANTOR']},
            {'tipo': 'label', 'texto': row['estilo'],'row': counter, 'descripcion': 'Estilo', 'frame': self.frames_resultado['Estilo'],
             'anchor': "w", 'colour': colores['ESTILO']},
            {'tipo': 'label', 'texto': row['fecha'],'row': counter, 'descripcion': 'Fecha', 'frame': self.frames_resultado['Fecha'],
             'anchor': "w", 'colour': colores['FECHA']},
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
             'frame': self.frames_archivo.get('Titulo'), 'anchor': "w", 'colour' : self.color_de_fondo},
            {'tipo': 'label', 'texto': self.artists1, 'row': 0, 'descripcion': 'Orquesta',
             'frame': self.frames_archivo.get('Orquesta'), 'anchor': "w", 'colour' : self.color_de_fondo},
            {'tipo': 'label', 'texto': self.artists2, 'row': 0, 'descripcion': 'Cantor',
             'frame': self.frames_archivo.get('Cantor'), 'anchor': "w", 'colour' : self.color_de_fondo},
            {'tipo': 'label', 'texto': self.tags.year, 'row': 0, 'descripcion': 'Fecha',
             'frame': self.frames_archivo.get('Fecha'), 'anchor': "w", 'colour' : self.color_de_fondo},
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
                    bg=elemento['colour'], anchor=elemento['anchor'], row=elemento['row'],
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
        # Inicialización de variables
        self.hay_coincidencia_preferida = False
        self.no_hay_coincidencia_preferida = False
        self.coincidencia_preferida = 0
        self.tipo_de_coincidencia = 0

        # Buscar al artista
        artista_original, cantor_original = separar_artistas(self.tags.artist)
        artista_key, self.artista_coincidencia = self.buscar_artista(artista_original)

        if not artista_key:
            self.resultado = 'Artista no encontrado'
            self.coincidencias = self.db.iloc[0:0]
            self.hay_coincidencia_preferida = False
            self.coincidencia_preferida = 0
            self.titulo_coincidencia = 0
            self.artist_not_found =True
            return

        # Obtener las canciones del artista
        artist_songs = self.obtener_canciones_artista(artista_key)

        # Buscar el título
        self.titulo_coincidencia, database_titulo = buscar_titulo(artist_songs, self.tags)

        if self.titulo_coincidencia == 0:
            self.resultado = 'Titulo no encontrado'
            self.coincidencias = self.db.iloc[0:0]
            self.hay_coincidencia_preferida = False
            self.coincidencia_preferida = 0
            self.title_not_found =True
            return

        # Comparar tags y generar coincidencias
        self.bool_coincidencias, self.perfect_match, perfect_match_index = compare_tags(
            self.artista_coincidencia, self.titulo_coincidencia, database_titulo, self.tags
        )

        if self.perfect_match:
            # Filtrar solo la coincidencia exacta utilizando el índice perfecto
            database_titulo = database_titulo.loc[[perfect_match_index]]
            self.hay_coincidencia_preferida = False  # No hay coincidencia preferida en caso de perfect match
            self.coincidencia_preferida = 0

        else:
            # Si no hay perfect match, proceder con la búsqueda de coincidencia preferida
            self.hay_coincidencia_preferida, self.coincidencia_preferida = buscar_preferencias(
                self.bool_coincidencias, self.show_date_checked
            )
            if not self.hay_coincidencia_preferida:
                self.no_hay_coincidencia_preferida = True

        self.coincidencias = database_titulo
        # Generar colores para los labels
        if not self.direct_comparison:
            self.colores_labels = coincidencias_a_colores(self.bool_coincidencias,self.perfect_match)



    def buscar_artista(self, artista_original):
        artista_buscar_min = unidecode(artista_original).lower()

        # Búsqueda exacta
        artista_key = next((key for key in self.dic_art if key == artista_original), None)
        if artista_key:
            return artista_key, 3

        # Búsqueda aproximada
        artista_key = next((key for key in self.dic_art if key == artista_buscar_min), None)
        if artista_key:
            return artista_key, 2

        # Búsqueda parcial
        artista_key = next((key for key in self.dic_art if artista_buscar_min in key), None)
        if artista_key:
            return artista_key, 1

        # Búsqueda por palabras
        artista_key = contain_most_words_in_dic(self.dic_art, artista_buscar_min)
        if artista_key is not None:
            return artista_key, 1

        return None, 0

    def obtener_canciones_artista(self, artista_key):
        if isinstance(artista_key, str):
            # Si es una cadena, toma el DataFrame único
            return self.dic_art[artista_key]
        elif isinstance(artista_key, list):
            # Si es una lista de cadenas, concatena los DataFrames
            return pd.concat([self.dic_art[key] for key in artista_key if key in self.dic_art])
        else:
            # Manejo de tipos inesperados
            raise ValueError("artista_key must be a string or a list of strings")


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
            ["tag.artist", tags.artist],  # Add the artist tag here
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
        bottom_frame.grid(row=len(etiquetas_datos) + 1, column=0, columnspan=2, padx=self.padx, pady=self.pady,
                          sticky="nsew")

        # Expandir el bottom_frame al cambiar el tamaño del popup
        popup.grid_rowconfigure(len(etiquetas_datos) + 1, weight=1)
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_columnconfigure(1, weight=1)

        # Encabezado dentro del bottom_frame
        header_label = tk.Label(bottom_frame, text="Base de Datos", font=("Helvetica", 14, "bold"), bg="#e0e0e0")
        header_label.grid(row=0, column=0, columnspan=4, padx=self.padx, pady=self.pady)

    # **********************************************
    # **********************************************
    # **********************************************
    # **********************************************
    # **********************************************

    def leer_entredas_y_tagear(self, popup):

        values = [entry.get() for entry in self.entry_dato_lista]

        artista_nuevo = unir_artistas(self.entry_dato_lista[2].get(),self.entry_dato_lista[3].get(), " / ")

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
            self.representa()

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
        # Verificar si self.frames_archivo está definido y destruir los frames en 'archivo'
        if hasattr(self, 'frames_archivo'):
            for column in columnas_config['archivo']:
                description = str(column['description'])
                if description in self.frames_archivo:
                    self.frames_archivo[description].destroy()

        # Verificar si self.frames_resultado está definido y destruir los frames en 'resultado'
        if hasattr(self, 'frames_resultado'):
            for column in columnas_config['resultado']:
                description = str(column['description'])
                if description in self.frames_resultado:
                    self.frames_resultado[description].destroy()



            

