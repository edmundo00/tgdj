"""
Correcciones hechas a mano sobre la base de datos (botón "Corregir datos…" del buscador).

Se guardan en data/correcciones.csv, identificadas por la grabación ORIGINAL (título, orquesta,
cantor y fecha normalizados), y se aplican cada vez que se carga la base de datos. Así no se
pierden al regenerar tangodb.csv ni al actualizar mergeddb.csv.
"""
import os
from datetime import datetime

import pandas as pd

from src.config.config import DATA_FOLDER
from src.utils.buscar_artista import normalizar_nombre
from src.utils.formato_tags import formatear_cantores, formatear_fecha, formatear_compositor

ARCHIVO = os.path.join(DATA_FOLDER, "correcciones.csv")
CAMPOS = ["titulo", "artista", "cantor", "fecha", "estilo", "musica", "letra"]


def clave_grabacion(titulo, artista, cantor, fecha):
    """Identifica una grabación aunque cambien mayúsculas, acentos, puntuación o el formato de fecha."""
    from src.utils.buscador import normalizar
    return "|".join([normalizar(titulo), normalizar_nombre(artista),
                     normalizar_nombre(formatear_cantores(cantor)), formatear_fecha(fecha)])


def claves(db):
    return [clave_grabacion(*v) for v in db[["titulo", "artista", "cantor", "fecha"]].astype(str).values]


def leer(archivo=None):
    archivo = archivo or ARCHIVO
    if not os.path.exists(archivo):
        return pd.DataFrame(columns=["clave", *CAMPOS, "corregido_el"])
    return pd.read_csv(archivo, sep=";", na_filter=False, dtype=str, encoding="utf-8-sig")


def guardar(clave, valores, archivo=None):
    """valores: dict con los CAMPOS (los que falten se dejan vacíos = no se tocan)."""
    archivo = archivo or ARCHIVO
    df = leer(archivo)
    df = df[df["clave"] != clave]
    nueva = {"clave": clave, **{c: str(valores.get(c, "") or "") for c in CAMPOS},
             "corregido_el": datetime.now().strftime("%Y-%m-%d %H:%M")}
    df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
    df.to_csv(archivo, sep=";", index=False, encoding="utf-8-sig")


def aplicar(db, archivo=None):
    """
    Devuelve una copia de db con las correcciones aplicadas, la columna '_clave_original'
    (para poder corregir otra vez) y 'corregida' (True/False).
    """
    db = db.copy()
    db["_clave_original"] = claves(db)
    db["corregida"] = False
    correcciones = leer(archivo)
    if correcciones.empty:
        return db
    for _, c in correcciones.iterrows():
        filas = db["_clave_original"] == c["clave"]
        if not filas.any():
            continue
        for campo in ("titulo", "artista", "cantor", "fecha", "estilo"):
            if c[campo]:
                db.loc[filas, campo] = c[campo]
        if c["musica"] or c["letra"]:
            db.loc[filas, "compositor_autor"] = formatear_compositor(c["musica"], c["letra"])
        db.loc[filas, "corregida"] = True
    if "artista_min" in db:
        db["artista_min"] = db["artista"]
    if "fecha_ano" in db:
        db["fecha_ano"] = db["fecha"].map(lambda f: formatear_fecha(f)[:4])
    if "titulo_min" in db:
        from src.utils.mejorar_bd import normalizar_titulo
        cambiadas = db["corregida"]
        db.loc[cambiadas, "titulo_min"] = db.loc[cambiadas, "titulo"].map(normalizar_titulo)
    return db
