"""
Copia de seguridad de las tags antes de cada "Aplicar tags", para poder deshacer.

Cada vez que se aplican tags se guarda output/backups/tags_AAAAMMDD_HHMMSS.csv con, por
archivo, el valor anterior y el nuevo de cada campo que cambió. Deshacer vuelve a escribir
los valores anteriores (borrando la tag si antes estaba vacía) y crea al lado un archivo
tags_….csv.deshecho para no deshacerlo dos veces. (No se renombra el CSV porque Dropbox
lo bloquea mientras lo sincroniza.)
"""
import glob
import os
from datetime import datetime

import pandas as pd

from src.config.config import OUTPUT_FOLDER

CARPETA_BACKUPS = os.path.join(OUTPUT_FOLDER, "backups")
CAMPOS = ("title", "artist", "year", "genre", "composer")


def guardar_backup(cambios, carpeta=None):
    """cambios: lista de (ruta, tags_antes: dict, tags_despues: dict). Devuelve la ruta del CSV."""
    carpeta = carpeta or CARPETA_BACKUPS
    os.makedirs(carpeta, exist_ok=True)
    filas = []
    for ruta, antes, despues in cambios:
        for campo in CAMPOS:
            if campo in despues:
                filas.append({"archivo": ruta, "campo": campo,
                              "antes": antes.get(campo, "") or "", "despues": despues[campo]})
    ruta_csv = os.path.join(carpeta, f"tags_{datetime.now():%Y%m%d_%H%M%S}.csv")
    pd.DataFrame(filas, columns=["archivo", "campo", "antes", "despues"]).to_csv(
        ruta_csv, sep=";", index=False, encoding="utf-8-sig")
    return ruta_csv


def esta_deshecho(ruta_csv):
    return os.path.exists(ruta_csv + ".deshecho")


def listar_backups(carpeta=None, incluir_deshechos=False):
    """Backups del más reciente al más antiguo."""
    rutas = sorted(glob.glob(os.path.join(carpeta or CARPETA_BACKUPS, "tags_*.csv")), reverse=True)
    return [r for r in rutas if incluir_deshechos or not esta_deshecho(r)]


def leer_backup(ruta_csv):
    return pd.read_csv(ruta_csv, sep=";", na_filter=False, encoding="utf-8-sig", dtype=str)


def resumen_backup(ruta_csv):
    df = leer_backup(ruta_csv)
    nombre = os.path.basename(ruta_csv)
    try:
        fecha = datetime.strptime(nombre[5:20], "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        fecha = nombre
    return f"{fecha} — {df['archivo'].nunique()} archivo(s)" + (" (deshecho)" if esta_deshecho(ruta_csv) else "")


def deshacer(ruta_csv, escribir_tags):
    """
    Restaura las tags anteriores. escribir_tags(ruta, valores, borrar_vacios=True) -> bool.
    Devuelve (restaurados, lista de archivos con error).
    """
    df = leer_backup(ruta_csv)
    restaurados, errores = 0, []
    for archivo, grupo in df.groupby("archivo", sort=False):
        valores = dict(zip(grupo["campo"], grupo["antes"]))
        if os.path.exists(archivo) and escribir_tags(archivo, valores, borrar_vacios=True):
            restaurados += 1
        else:
            errores.append(archivo)
    if not errores:
        with open(ruta_csv + ".deshecho", "w", encoding="utf-8") as marca:
            marca.write(f"Deshecho el {datetime.now():%d/%m/%Y %H:%M}\n")
    return restaurados, errores
