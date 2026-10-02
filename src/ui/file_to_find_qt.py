from src.utils.utils import *
from src.config.database import Database
from datetime import datetime
from mutagen.id3 import ID3, ID3NoHeaderError
from types import SimpleNamespace
from src.utils.buscar_artista import indice_para


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
        self.motivo_fecha = ""


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
            _filename=tags[5],
            album=tags[6] if len(tags) > 6 else ""
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
        # Sin artista en la tag no se puede buscar ("" in key coincidiría con cualquier artista)
        if artista_original.strip():
            artista_key, self.artista_coincidencia = self.buscar_artista(artista_original)
        else:
            artista_key, self.artista_coincidencia = None, 0

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
        # La misma grabación repetida (El Recodo y tango.info) se muestra una sola vez: la más completa
        if len(database_titulo) > 1:
            from src.utils.correcciones import claves
            completa = ((database_titulo["compositor_autor"].astype(str) != "").astype(int)
                        + (database_titulo["fecha"].astype(str).str.len() == 10).astype(int)
                        + (database_titulo.get("audio30", "").astype(str) != "").astype(int))
            database_titulo = (database_titulo.assign(_clave=claves(database_titulo), _completa=completa)
                               .sort_values("_completa", ascending=False, kind="stable")
                               .drop_duplicates("_clave").drop(columns=["_clave", "_completa"]))
        # Opciones en orden cronológico (las sin fecha al final)
        if not database_titulo.empty:
            orden = database_titulo["fecha"].astype(str).replace("", "9999")
            database_titulo = database_titulo.loc[orden.sort_values(kind="stable").index]
            # Fecha del archivo que en realidad es la del CD: no sirve para elegir
            self.motivo_fecha = fecha_es_de_cd(self.tags.year, list(database_titulo["artista"]),
                                               list(database_titulo["fecha"]))

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
            self.hay_coincidencia_preferida, self.coincidencia_preferida = elegir_preferida(
                self.bool_coincidencias, database_titulo, self.show_date_checked
            )
            if not self.hay_coincidencia_preferida:
                self.no_hay_coincidencia_preferida = True

        self.coincidencias = database_titulo
        # Generar colores para los labels

        self.colores_labels = coincidencias_a_colores(self.bool_coincidencias,self.perfect_match)


    def buscar_artista(self, artista_original):
        """Devuelve (claves de la BD, nivel 3=exacta 2=normalizada 1=parcial 0=no encontrado)."""
        claves, nivel = indice_para(self.dic_art).buscar(artista_original)
        return claves, nivel

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


            


# Puntos por campo según el tipo de coincidencia (verde 3, amarillo 2, naranja 1, rojo 0)
_GRUPOS_PUNTOS = {
    "orquesta": (TagLabels.ORQUESTA_EXACTA, TagLabels.ORQUESTA, TagLabels.ORQUESTA_PARCIAL),
    "titulo": (TagLabels.TITULO_EXACTO, TagLabels.TITULO, TagLabels.TITULO_PARCIAL),
    "cantor": (TagLabels.CANTOR_EXACTO, TagLabels.CANTOR, TagLabels.CANTOR_PARCIAL),
    "fecha": (TagLabels.FECHA_EXACTA, TagLabels.FECHA, TagLabels.FECHA_PARCIAL),
    "estilo": (TagLabels.ESTILO_EXACTO, TagLabels.ESTILO, TagLabels.ESTILO_PARCIAL),
    "compositor": (TagLabels.COMPOSITOR_AUTOR_EXACTO, TagLabels.COMPOSITOR_AUTOR, TagLabels.COMPOSITOR_AUTOR_PARCIAL),
}


def elegir_preferida(booleanos, candidatas, usar_fecha=True):
    """
    Elige la coincidencia a sugerir. Solo valen las filas con título y orquesta que coinciden,
    cantor no contradictorio y (si usar_fecha) año no contradictorio. Entre ellas gana la de más
    puntos; si varias empatan pero escribirían las mismas tags (duplicados de la BD), vale la primera.
    Devuelve (hay_preferida, posición).
    """
    from src.utils.formato_tags import tags_desde_coincidencia
    get = lambda etiqueta, i: bool(booleanos[etiqueta].iloc[i])
    validas = []
    for i in range(len(candidatas)):
        titulo_ok = get(TagLabels.TITULO_EXACTO, i) or get(TagLabels.TITULO, i)
        # Título parecido solo en parte: vale si cantor y año confirman que es esa grabación
        confirmada = ((get(TagLabels.CANTOR_EXACTO, i) or get(TagLabels.CANTOR, i))
                      and (get(TagLabels.FECHA_EXACTA, i) or get(TagLabels.FECHA, i)))
        if not (titulo_ok or (get(TagLabels.TITULO_PARCIAL, i) and confirmada)):
            continue
        if not (get(TagLabels.ORQUESTA_EXACTA, i) or get(TagLabels.ORQUESTA, i)):
            continue
        if get(TagLabels.CANTOR_NEGATIVO, i):
            continue
        if usar_fecha and get(TagLabels.FECHA_NEGATIVA, i):
            continue
        puntos = sum(3 * get(e, i) + 2 * get(n, i) + get(p, i) for e, n, p in _GRUPOS_PUNTOS.values())
        validas.append((puntos, i))
    if not validas:
        return False, 0
    maximo = max(p for p, _ in validas)
    mejores = [i for p, i in validas if p == maximo]
    tags = {tuple(sorted(tags_desde_coincidencia(candidatas.iloc[i]).items())) for i in mejores}
    if len(mejores) == 1 or len(tags) == 1:
        return True, mejores[0]
    return False, 0
