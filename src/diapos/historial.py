"""
Milongas anteriores en el mismo sitio, para no repetir cortinas ni tandas.

Las playlists de las milongas se llaman AAMMDD_Lugar (p. ej. 261013_Milonga_Mia.mbp, 240920_Milonga_Mia.m3u):
se buscan en la misma carpeta que la playlist que se revisa, del mismo lugar y anteriores a su fecha.
Las canciones se comparan por ruta relativa a Dropbox (vale en el fijo y en el portátil), sin leer tags.
"""
import os
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from unidecode import unidecode

from src.utils.musicbee_playlist import leer_mbp
from src.utils.utils import load_m3u_file_helper

MESES_ATRAS = 12
_NOMBRE = re.compile(r"^(\d{2})(\d{2})(\d{2})[ _\-]*(.+?)\.(mbp|m3u8?)$", re.IGNORECASE)


@dataclass
class Milonga:
    fecha: date
    nombre: str
    claves: set = field(default_factory=set)

    @property
    def fecha_texto(self):
        return f"{self.fecha:%d/%m/%Y}"


def clave(ruta):
    """Ruta relativa a Dropbox, en minúsculas."""
    m = re.search(r"[\\/]Dropbox[\\/]", ruta)
    return (ruta[m.end():] if m else ruta).replace("/", "\\").lower()


def fecha_y_lugar(nombre_archivo):
    """'261013_Milonga_Mia.mbp' -> (date(2026, 10, 13), 'milonga mia'); (None, None) si no sigue el formato."""
    m = _NOMBRE.match(os.path.basename(nombre_archivo))
    if not m:
        return None, None
    try:
        fecha = date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None, None
    lugar = re.sub(r"[^a-z0-9]+", " ", unidecode(m.group(4)).lower()).strip()
    return fecha, lugar


def _rutas(ruta):
    try:
        return leer_mbp(ruta) if ruta.lower().endswith(".mbp") else load_m3u_file_helper(ruta)
    except OSError:
        return []


def anteriores(ruta_playlist, meses=MESES_ATRAS):
    """Milongas del mismo lugar en los `meses` anteriores (la más reciente primero)."""
    fecha, lugar = fecha_y_lugar(ruta_playlist)
    if not lugar:
        return []
    carpeta = os.path.dirname(ruta_playlist)
    desde = fecha - timedelta(days=31 * meses)
    milongas = {}
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return []
    for nombre in nombres:
        f, l = fecha_y_lugar(nombre)
        if l != lugar or not (desde <= f < fecha):
            continue
        # si hay .mbp y .m3u de la misma milonga, vale con una
        if f in milongas and not nombre.lower().endswith(".mbp"):
            continue
        claves = {clave(r) for r in _rutas(os.path.join(carpeta, nombre))}
        if claves:
            milongas[f] = Milonga(f, os.path.splitext(nombre)[0], claves)
    return sorted(milongas.values(), key=lambda m: m.fecha, reverse=True)
