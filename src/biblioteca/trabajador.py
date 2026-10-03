"""
Lo que hace cada proceso aparte al emparejar la biblioteca (para no frenar la ventana y usar
varios núcleos). Cada proceso carga una vez la base de datos de tango y empareja lotes de canciones.
"""
_motor = None


def iniciar(usar_fecha):
    """Se ejecuta una vez en cada proceso: carga la base de datos de tango y prepara el motor."""
    global _motor
    import os
    import sys
    sys.stdout = sys.stderr = open(os.devnull, "w")      # sin mensajes de pygame / carga
    from src.config.config import DB_CSV_PATH
    from src.config.database import Database
    from src.motor.emparejar import Motor
    Database().load_data(DB_CSV_PATH)
    _motor = Motor(usar_fecha=usar_fecha)


def emparejar_lote(filas):
    """filas: [(id, ruta, [title, artist, year, genre, composer, ruta, album])] -> [(id, resumen o error)]."""
    from src.motor.emparejar import resumen
    salida = []
    for i, ruta, tags in filas:
        try:
            salida.append((i, resumen(_motor.emparejar(ruta, tags))))
        except Exception as e:
            salida.append((i, {"error": str(e)[:200]}))
    return salida
