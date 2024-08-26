# src/constants.py or src/enums.py
from enum import Enum

class TagLabels(Enum):
    TITULO = 'titulo'
    TITULO_EXACTO = 'titulo_exacto'
    TITULO_PALABRAS = 'titulo_palabras'
    ARTISTA = 'artista'
    ARTISTA_EXACTO = 'aritsta_exacto'
    CANTOR = 'cantor'
    CANTOR_EXACTO = 'cantor_exacto'
    FECHA = 'fecha'
    ANO = 'fecha_ano'
    GENERO = 'genero'
    COMPOSITOR_AUTOR = 'compositor_autor'
    TODO = 'todo'
