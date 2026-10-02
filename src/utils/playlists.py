"""
Reparar playlists (.m3u/.m3u8): encontrar en la colección las canciones que se movieron o
renombraron y reescribir su ruta.

Para cada entrada que no existe se buscan candidatos en la colección:
  1. mismo nombre de archivo,
  2. mismo artista y título (de las tags; VirtualDJ los apunta en la línea #EXTVDJ),
y se ordenan dando prioridad al mismo tamaño de archivo (VirtualDJ también lo apunta), que
identifica la misma grabación casi con seguridad. Antes de reescribir se guarda una copia.
"""
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from src.config.config import OUTPUT_FOLDER
from src.utils.buscar_artista import normalizar_nombre, separar_orquesta_cantor
from src.utils.utils import leer_lineas_m3u

CARPETA_COPIAS = os.path.join(OUTPUT_FOLDER, "playlists_copias")


@dataclass
class Entrada:
    linea: int                  # índice de la línea con la ruta
    ruta: str
    existe: bool
    artista: str = ""
    titulo: str = ""
    tamano: int = 0
    candidatos: list = field(default_factory=list)   # [(ruta, motivo, seguro)]


def _vdj(linea):
    """Datos de una línea '#EXTVDJ:<filesize>…</filesize><artist>…</artist><title>…</title>…'."""
    datos = dict(re.findall(r"<(\w+)>(.*?)</\1>", linea))
    try:
        tamano = int(datos.get("filesize", 0))
    except ValueError:
        tamano = 0
    return datos.get("artist", ""), datos.get("title", ""), tamano


def _resolver(ruta, dropbox):
    """Ruta tal cual, o rehecha con el Dropbox de este ordenador si viene de otro."""
    if os.path.exists(ruta) or "Dropbox" not in ruta or not dropbox:
        return ruta
    alternativa = os.path.join(dropbox, ruta.split("Dropbox", 1)[1].lstrip("\\/"))
    return alternativa if os.path.exists(alternativa) else ruta


def leer(ruta_m3u, dropbox=None):
    """Entradas de la playlist (las que existen y las que no), con los datos de VirtualDJ."""
    lineas, _ = leer_lineas_m3u(ruta_m3u)
    entradas, vdj = [], ("", "", 0)
    for i, l in enumerate(lineas):
        texto = l.strip()
        if texto.startswith("#EXTVDJ:"):
            vdj = _vdj(texto)
        elif texto and not texto.startswith("#"):
            ruta = _resolver(texto, dropbox)
            entradas.append(Entrada(i, texto, os.path.exists(ruta), *vdj))
            vdj = ("", "", 0)
    return entradas


def _clave_cancion(artista, titulo):
    orquesta = separar_orquesta_cantor(artista or "")[0].split(",")[0]
    return normalizar_nombre(orquesta) + "|" + re.sub(r"[^a-z0-9]+", " ", normalizar_nombre(titulo)).strip()


def _nombre_normalizado(ruta):
    """'Francisco Lomuto, Fernando Díaz - No hay tierra como la mía.flac' -> 'francisco lomuto fernando diaz no hay tierra como mia'."""
    return normalizar_nombre(os.path.splitext(os.path.basename(ruta.replace("\\", "/")))[0])


def _artista_titulo_de_nombre(ruta):
    """'Juan Maglio - Tango Argentino.flac' -> ('Juan Maglio', 'Tango Argentino')."""
    nombre = os.path.splitext(os.path.basename(ruta.replace("\\", "/")))[0]
    nombre = re.sub(r"^\d{1,3}[\s.\-_]+", "", nombre)          # número de pista delante
    if " - " in nombre:
        artista, titulo = nombre.split(" - ", 1)
        return artista.strip(), titulo.strip()
    return "", ""


class IndiceColeccion:
    """Índice de la colección por nombre de archivo y por artista+título (a partir de la caché)."""

    def __init__(self, df):
        df = df[~df["ruta"].str.contains(r"[\\/]_duplicados[\\/]", regex=True)]
        self.tamano = dict(zip(df["ruta"], pd.to_numeric(df["bytes"], errors="coerce").fillna(0).astype(int)))
        self.por_nombre, self.por_cancion, self.por_nombre_normal = {}, {}, {}
        for ruta, artista, titulo in zip(df["ruta"], df["artist"], df["title"]):
            self.por_nombre.setdefault(os.path.basename(ruta).lower(), []).append(ruta)
            self.por_nombre_normal.setdefault(_nombre_normalizado(ruta), []).append(ruta)
            if titulo:
                self.por_cancion.setdefault(_clave_cancion(artista, titulo), []).append(ruta)

    def candidatos(self, entrada):
        vistos, salida = set(), []

        def anadir(rutas, motivo):
            for r in rutas:
                if r not in vistos and os.path.exists(r):
                    vistos.add(r)
                    mismo_tamano = bool(entrada.tamano) and self.tamano.get(r) == entrada.tamano
                    salida.append((r, motivo + (", mismo tamaño" if mismo_tamano else ""), mismo_tamano))

        anadir(self.por_nombre.get(os.path.basename(entrada.ruta.replace("\\", "/")).lower(), []), "mismo nombre de archivo")
        anadir(self.por_nombre_normal.get(_nombre_normalizado(entrada.ruta), []), "nombre de archivo parecido")
        artista, titulo = entrada.artista, entrada.titulo
        if not titulo:
            artista, titulo = _artista_titulo_de_nombre(entrada.ruta)
        if titulo:
            anadir(self.por_cancion.get(_clave_cancion(artista, titulo), []), "mismo artista y título")
        # Primero los de mismo tamaño (casi seguro la misma grabación), luego por motivo
        salida.sort(key=lambda c: (not c[2], "título" in c[1]))
        return salida


def analizar(ruta_m3u, indice, dropbox=None):
    entradas = leer(ruta_m3u, dropbox)
    for e in entradas:
        if not e.existe:
            e.candidatos = indice.candidatos(e)
    return entradas


def _coleccion(ruta):
    """Carpeta de la colección (la que va después de MUSICA), para preferir candidatos de la misma."""
    partes = re.split(r"[\\/]", ruta)
    return partes[partes.index("MUSICA") + 1].lower() if "MUSICA" in partes[:-1] else ""


def propuesta_segura(entrada):
    """
    Candidato con el mismo tamaño (misma grabación). Si hay varios (copias idénticas en varias
    colecciones) se prefiere el de la misma colección y luego el del mismo nombre de archivo.
    Sin tamaño conocido, solo si hay un único candidato.
    """
    seguros = [c for c in entrada.candidatos if c[2]]
    if seguros:
        nombre = os.path.basename(entrada.ruta.replace("\\", "/")).lower()
        seguros.sort(key=lambda c: (_coleccion(c[0]) != _coleccion(entrada.ruta),
                                    os.path.basename(c[0]).lower() != nombre))
        return seguros[0][0]
    if not entrada.tamano and len(entrada.candidatos) == 1:
        return entrada.candidatos[0][0]
    return None


def reparar(ruta_m3u, reemplazos, carpeta_copias=None):
    """
    reemplazos: {nº de línea: ruta nueva}. Guarda antes una copia de la playlist y conserva el
    resto del archivo tal cual (líneas #EXTVDJ, saltos de línea, codificación).
    Devuelve la ruta de la copia de seguridad.
    """
    carpeta_copias = carpeta_copias or CARPETA_COPIAS
    os.makedirs(carpeta_copias, exist_ok=True)
    base, ext = os.path.splitext(os.path.basename(ruta_m3u))
    copia = os.path.join(carpeta_copias, f"{base}_{datetime.now():%Y%m%d_%H%M%S}{ext}")
    shutil.copy2(ruta_m3u, copia)

    with open(ruta_m3u, "rb") as f:
        crudo = f.read()
    lineas, codificacion = leer_lineas_m3u(ruta_m3u)
    salto = "\r\n" if b"\r\n" in crudo else "\n"
    for i, nueva in reemplazos.items():
        lineas[i] = nueva
    texto = salto.join(lineas) + (salto if crudo.endswith((b"\n", b"\r")) else "")
    with open(ruta_m3u, "w", encoding=codificacion, newline="") as f:
        f.write(texto)
    return copia


def restaurar(copia, ruta_m3u):
    shutil.copy2(copia, ruta_m3u)
