import os
from src.ui.owndatabase import owndatabase  # Asegúrate de que el módulo owndatabase está en el mismo directorio o en el PYTHONPATH
from src.config.config import *

def test_owndatabase():
    print("Iniciando prueba de la clase owndatabase...")

    # Crear una instancia de owndatabase sin update_status (para pruebas sin GUI)
    db = owndatabase()

    # Filtrar las filas donde 'Coincidencia perfecta' es False y 'Artista encontrado' es True
    filtered_df = db.owndf[
        (~db.owndf_rep['Coincidencia perfecta']) &
        (db.owndf_rep['Artista encontrado'])
    ]

    # Obtener la lista de artistas y el número de repeticiones
    artist_counts = filtered_df['artist'].value_counts()

    # Imprimir la lista de artistas y cuántas veces se repiten
    print(artist_counts)

    archivo_artistas_no_encontrados = os.path.join(OUTPUT_FOLDER, 'artistas_no_encontrados.csv')

    artist_counts.to_csv(archivo_artistas_no_encontrados, index=True)

if __name__ == '__main__':
    test_owndatabase()