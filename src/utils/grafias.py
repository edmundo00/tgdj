"""
Grafías preferidas de orquestas y cantores ("Carlos di Sarli" o "Carlos Di Sarli").

data/grafias.csv: nombre normalizado -> cómo quieres que se escriba. Tiene prioridad sobre la
grafía de la base de datos y se aplica al cargarla, así que las tags que se escriben y la
comparación "perfecta" usan tu forma de escribir los nombres.
"""
import os
import re

import pandas as pd

from src.config.config import DATA_FOLDER
from src.utils.buscar_artista import normalizar_nombre

ARCHIVO = os.path.join(DATA_FOLDER, "grafias.csv")


def leer(archivo=None):
    """{nombre normalizado: grafía preferida}"""
    archivo = archivo or ARCHIVO
    if not os.path.exists(archivo):
        return {}
    df = pd.read_csv(archivo, sep=";", na_filter=False, dtype=str, encoding="utf-8-sig")
    return {normalizar_nombre(g): g for g in df["grafia"] if g.strip()}


def guardar(preferidas, archivo=None):
    """preferidas: iterable de grafías elegidas (una por nombre)."""
    archivo = archivo or ARCHIVO
    unicas = {normalizar_nombre(g): g.strip() for g in preferidas if g.strip()}
    pd.DataFrame({"grafia": sorted(unicas.values(), key=str.lower)}).to_csv(
        archivo, sep=";", index=False, encoding="utf-8-sig")


def preferida(nombre, preferidas):
    return preferidas.get(normalizar_nombre(nombre), nombre)


def _cantores(valor, preferidas):
    """'A,B' / 'A y B' -> cada nombre con su grafía preferida, manteniendo el separador."""
    partes = re.split(r"(,\s*|\s+y\s+)", str(valor))
    return "".join(p if i % 2 else preferida(p.strip(), preferidas) if p.strip() else p
                   for i, p in enumerate(partes))


def aplicar(db, preferidas=None):
    preferidas = leer() if preferidas is None else preferidas
    if not preferidas:
        return db
    db = db.copy()
    if "_artista_bd" not in db:          # la grafía original, para el diálogo de grafías
        db["_artista_bd"], db["_cantor_bd"] = db["artista"], db["cantor"]
    db["artista"] = db["artista"].map(lambda v: preferida(v, preferidas))
    db["cantor"] = db["cantor"].map(lambda v: _cantores(v, preferidas))
    if "artista_min" in db:
        db["artista_min"] = db["artista"]
    return db


def diferencias(nombres_coleccion, nombres_bd, preferidas=None):
    """
    Nombres escritos distinto en tu colección y en la base de datos.
    nombres_coleccion: {grafía: nº de archivos}. Devuelve DataFrame con
    normalizado, grafia_bd, grafias_coleccion (dict), elegida.
    """
    preferidas = leer() if preferidas is None else preferidas
    bd = {}
    for n in nombres_bd:
        if normalizar_nombre(n):
            bd.setdefault(normalizar_nombre(n), n)
    por_nombre = {}
    for g, k in nombres_coleccion.items():
        n = normalizar_nombre(g)
        if n in bd:
            por_nombre.setdefault(n, {})
            por_nombre[n][g] = por_nombre[n].get(g, 0) + k
    filas = []
    for n, grafias in por_nombre.items():
        todas = set(grafias) | {bd[n]}
        if len(todas) < 2 and n not in preferidas:
            continue
        mayoritaria = max(grafias, key=grafias.get)
        filas.append({"normalizado": n, "grafia_bd": bd[n], "grafias_coleccion": grafias,
                      "archivos": sum(grafias.values()), "elegida": preferidas.get(n, mayoritaria)})
    return pd.DataFrame(filas).sort_values("archivos", ascending=False) if filas else pd.DataFrame(
        columns=["normalizado", "grafia_bd", "grafias_coleccion", "archivos", "elegida"])
