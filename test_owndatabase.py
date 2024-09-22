import os
from src.ui.owndatabase import owndatabase  # Asegúrate de que el módulo owndatabase está en el mismo directorio o en el PYTHONPATH
from src.config.config import *
import re
from src.utils.utils import *

def test_owndatabase():
    print("Iniciando prueba de la clase owndatabase...")

    # Crear una instancia de owndatabase
    db = owndatabase()

    # Llamar a las funciones definidas en la clase
    output_folder = OUTPUT_FOLDER

    # Obtener la lista de artistas no encontrados y sus recuentos
    db.get_artist_counts(output_folder)

    # Procesar fechas en los nombres de archivo
    db.process_file_dates(output_folder)



if __name__ == '__main__':
    test_owndatabase()