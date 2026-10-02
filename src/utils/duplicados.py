"""
Copias idénticas dentro de cada colección (primera subcarpeta de la música).

Idénticas = mismo tamaño exacto y mismo contenido (se compara una huella de principio, medio y
final del archivo). No se borra nada: las copias se MUEVEN a <música>/_duplicados/<misma ruta>,
y cada movimiento queda apuntado en output/duplicados/movidos_FECHA.csv para poder deshacerlo.
"""
import hashlib
import os
import shutil
from collections import defaultdict
from datetime import datetime

import pandas as pd

from src.config.config import OUTPUT_FOLDER
from src.utils.coleccion import CARPETA_DUPLICADOS

CARPETA_REGISTROS = os.path.join(OUTPUT_FOLDER, "duplicados")
BLOQUE = 64 * 1024


def huella(ruta):
    """
    Hash de 3 trozos de 64 KB del INTERIOR del archivo (al 30, 50 y 70 %) + tamaño.
    El principio y el final no se miran porque ahí van las tags: dos copias del mismo audio con
    tags distintas tienen que salir como iguales.
    """
    tamano = os.path.getsize(ruta)
    h = hashlib.sha1(str(tamano).encode())
    with open(ruta, "rb") as f:
        for posicion in (int(tamano * 0.3), int(tamano * 0.5), max(int(tamano * 0.7) - BLOQUE, 0)):
            f.seek(posicion)
            h.update(f.read(BLOQUE))
    return h.hexdigest()


def buscar(archivos, progreso=None, cancelado=None):
    """
    archivos: iterable de (ruta, coleccion, tamaño). Solo se comparan archivos de la misma colección.
    Devuelve una lista de grupos (listas de rutas) de copias idénticas.
    """
    por_tamano = defaultdict(list)
    for ruta, coleccion, tamano in archivos:
        if int(tamano) > 100_000:
            por_tamano[(coleccion, int(tamano))].append(ruta)
    candidatos = [rs for rs in por_tamano.values() if len(rs) > 1]
    grupos = []
    for i, rutas in enumerate(candidatos, 1):
        if cancelado and cancelado():
            break
        por_huella = defaultdict(list)
        for r in rutas:
            try:
                por_huella[huella(r)].append(r)
            except OSError:
                pass
        grupos += [sorted(g) for g in por_huella.values() if len(g) > 1]
        if progreso:
            progreso(i, len(candidatos))
    return grupos


def sugerir_conservar(grupo, revisadas=frozenset()):
    """
    Cuál conservar: primero la ya revisada (compositor con formato nuevo), luego el nombre más
    "limpio" (sin '(1)', 'copia', '1_1'…) y, a igualdad, el más corto.
    """
    def puntos(r):
        nombre = os.path.basename(r).lower()
        sucio = any(x in nombre for x in ("(1)", "(2)", "copia", "copy", "1_1", "2_2", " - copia"))
        return (r not in revisadas, sucio, len(nombre), r)
    return min(grupo, key=puntos)


def mover(rutas, raiz, registro_dir=None):
    """Mueve las rutas a <raiz>/_duplicados/<ruta relativa>. Devuelve (movidos, errores, registro)."""
    registro_dir = registro_dir or CARPETA_REGISTROS
    os.makedirs(registro_dir, exist_ok=True)
    filas, errores = [], []
    for r in rutas:
        destino = os.path.join(raiz, CARPETA_DUPLICADOS, os.path.relpath(r, raiz))
        try:
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            if os.path.exists(destino):
                base, ext = os.path.splitext(destino)
                destino = f"{base} ({datetime.now():%H%M%S}){ext}"
            shutil.move(r, destino)
            filas.append({"origen": r, "destino": destino})
        except OSError as e:
            errores.append((r, str(e)))
    registro = os.path.join(registro_dir, f"movidos_{datetime.now():%Y%m%d_%H%M%S}.csv")
    pd.DataFrame(filas, columns=["origen", "destino"]).to_csv(registro, sep=";", index=False, encoding="utf-8-sig")
    return len(filas), errores, registro


def ultimo_registro(registro_dir=None):
    registro_dir = registro_dir or CARPETA_REGISTROS
    if not os.path.isdir(registro_dir):
        return None
    registros = sorted(f for f in os.listdir(registro_dir) if f.startswith("movidos_") and f.endswith(".csv"))
    return os.path.join(registro_dir, registros[-1]) if registros else None


def deshacer(registro):
    """Devuelve los archivos movidos a su sitio. Devuelve (restaurados, errores)."""
    df = pd.read_csv(registro, sep=";", na_filter=False, dtype=str, encoding="utf-8-sig")
    restaurados, errores = 0, []
    for origen, destino in zip(df["origen"], df["destino"]):
        try:
            if os.path.exists(origen):
                raise OSError("ya existe un archivo en el sitio original")
            os.makedirs(os.path.dirname(origen), exist_ok=True)
            shutil.move(destino, origen)
            restaurados += 1
        except OSError as e:
            errores.append((origen, str(e)))
    if not errores:
        os.replace(registro, registro[:-4] + "_deshecho.csv")
    return restaurados, errores
