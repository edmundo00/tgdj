from tkinter import ttk
from src.utils.utils import *
from src.config.database import Database
from datetime import datetime
from mutagen.id3 import ID3, ID3NoHeaderError
from types import SimpleNamespace


class FILETOFINDQT:

    def __init__(self, ruta_archivo, lista_frames, frame_number, lista_checks, tags = None):
        # print(db)
        self.data_store = Database()
        self.db = self.data_store.get_db()
        self.dic_art = self.data_store.get_dic_art()
        self.show_date_checked, self.show_perfect_matches, self.show_artist_not_found, \
            self.show_title_not_found, self.show_remaining, self.direct_comparison = lista_checks
        self.ruta_archivo = ruta_archivo
        self.frame_number = frame_number
        self.artist_not_found = True
        self.title_not_found = True
        self.titulo_coincidencia = int(0)

        self.perfect_match = False


        if tags is None:
            self.tags = leer_tags(self.ruta_archivo)
        else:
            self.tags = self.listoid3(tags)

        self.artists1, self.artists2 = separar_artistas(self.tags.artist)


        self.buscar()


        self.nextframe = self.frame_number



    def listoid3(self,tags):
        # Creating a simulated ID3 object using SimpleNamespace
        custom_tags = SimpleNamespace(
            title=tags[0],
            artist=tags[1],
            year=tags[2],
            genre=tags[3],
            composer=tags[4],
            _filename=tags[5]
        )
        return custom_tags

    def reporte(self):
        """
        Genera un reporte de las variables más importantes y las imprime, además de retornarlas.

        Returns:
            pd.DataFrame: Un DataFrame con las variables clave del reporte.
        """
        reporte_data = {
            'title': self.tags.title,
            'artist': self.tags.artist,
            'year': self.tags.year,
            'genre': self.tags.genre,
            'composer': self.tags.composer,
            'file_path': self.ruta_archivo,
            "Artista encontrado": not self.artist_not_found,
            "Titulo encontrado": not self.title_not_found,
            "Numero de coincidencias": len(self.coincidencias) if self.coincidencias is not None else 0,
            "Hay coincidencia preferida": self.hay_coincidencia_preferida,
            "No hay coincidencia preferida": not self.hay_coincidencia_preferida,
            "Coincidencia perfecta": self.perfect_match
        }

        return reporte_data

    def get_coincidencia_favorita(self):
        if self.hay_coincidencia_preferida:
            reemplazo_tags_linea = crear_reemplazo_tags_linea(
                ruta_archivo=self.ruta_archivo,
                tags=self.tags,
                coincidencias=self.coincidencias,
                coincidencia_preferida=self.coincidencia_preferida,
                artists1=self.artists1,
                artists2=self.artists2,
                coincidencia_titulo=self.titulo_coincidencia
            )
            return reemplazo_tags_linea
        else:
            return None


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

        self.artist_not_found = False
        # Obtener las canciones del artista
        artist_songs = self.obtener_canciones_artista(artista_key)

        # Buscar el título
        self.titulo_coincidencia, database_titulo = buscar_titulo(artist_songs, self.tags)

        if self.titulo_coincidencia == 0:
            self.resultado = 'Titulo no encontrado'
            self.coincidencias = self.db.iloc[0:0]
            self.hay_coincidencia_preferida = False
            self.coincidencia_preferida = 0
            self.title_not_found = True
            return

        self.title_not_found = False
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

        leer_tags(self.ruta_archivo)

        self.buscar()

        for archivos in filetofind_list:
            archivos.destroy()


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



            

