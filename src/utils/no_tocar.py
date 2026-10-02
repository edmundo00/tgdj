"""
Canciones marcadas a mano como "No tocar": ya revisadas y se dejan como están.
Se guardan en data/no_tocar.csv con la ruta relativa a Dropbox (vale en todos los ordenadores)
y no vuelven a aparecer al cargar (se puede desactivar en Opciones).
"""
import os
from datetime import datetime

import pandas as pd

from src.config.config import DATA_FOLDER, dropbox_path

ARCHIVO = os.path.join(DATA_FOLDER, "no_tocar.csv")


def _clave(ruta):
    """Ruta relativa a Dropbox, en minúsculas y con '/' (igual en D:\\Dropbox y C:\\Dropbox)."""
    ruta = os.path.normpath(ruta)
    try:
        rel = os.path.relpath(ruta, os.path.normpath(dropbox_path))
        if not rel.startswith(".."):
            ruta = rel
    except ValueError:      # otra unidad
        pass
    return ruta.replace("\\", "/").lower()


def leer(archivo=None):
    archivo = archivo or ARCHIVO
    if not os.path.exists(archivo):
        return pd.DataFrame(columns=["clave", "ruta", "titulo", "marcado_el"])
    return pd.read_csv(archivo, sep=";", na_filter=False, dtype=str, encoding="utf-8-sig")


def claves(archivo=None):
    return set(leer(archivo)["clave"])


def esta(ruta, conjunto):
    return _clave(ruta) in conjunto


def marcar(rutas_titulos, archivo=None):
    """rutas_titulos: lista de (ruta, título)."""
    archivo = archivo or ARCHIVO
    df = leer(archivo)
    nuevas = pd.DataFrame([{"clave": _clave(r), "ruta": r, "titulo": t or "",
                            "marcado_el": datetime.now().strftime("%Y-%m-%d %H:%M")} for r, t in rutas_titulos])
    df = pd.concat([df[~df["clave"].isin(nuevas["clave"])], nuevas], ignore_index=True)
    df.to_csv(archivo, sep=";", index=False, encoding="utf-8-sig")


def desmarcar(rutas, archivo=None):
    archivo = archivo or ARCHIVO
    df = leer(archivo)
    quitar = {_clave(r) for r in rutas}
    df[~df["clave"].isin(quitar)].to_csv(archivo, sep=";", index=False, encoding="utf-8-sig")
