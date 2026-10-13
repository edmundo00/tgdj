"""
Carácter de cada orquesta según la época (y a veces el cantor): data/caracter_orquestas.csv.

La tabla la puede corregir el usuario (se abre con Excel). Columnas:
    orquesta; desde; hasta; cantor; caracter; energia; dificultad; notas
    - desde/hasta vacíos = toda la carrera; cantor vacío = cualquiera
    - caracter: ritmico, melodico, lirico o dramatico
    - energia: 1 (muy tranquila) … 5 (mucha energía); dificultad: 1 fácil … 3 exige mucho a la pista
"""
import os
from dataclasses import dataclass
from statistics import median

import pandas as pd

from src.config.config import DATA_FOLDER
from src.utils.buscar_artista import normalizar_nombre

ARCHIVO = os.path.join(DATA_FOLDER, "caracter_orquestas.csv")
CARACTERES = {"ritmico": "rítmico", "melodico": "melódico", "lirico": "lírico", "dramatico": "dramático"}

_cache = {"clave": None, "filas": []}


@dataclass
class Caracter:
    orquesta: str
    caracter: str          # ritmico | melodico | lirico | dramatico
    energia: int
    dificultad: int
    notas: str = ""

    @property
    def texto(self):
        return f"{CARACTERES.get(self.caracter, self.caracter)} · energía {self.energia}"


def _entero(valor):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def leer(archivo=None):
    """Filas de la tabla (se vuelve a leer solo si el archivo cambió)."""
    archivo = archivo or ARCHIVO
    try:
        clave = (archivo, os.path.getmtime(archivo))
    except OSError:
        return []
    if _cache["clave"] != clave:
        df = pd.read_csv(archivo, sep=";", na_filter=False, dtype=str, encoding="utf-8-sig")
        filas = []
        for _, f in df.iterrows():
            if not f["orquesta"].strip():
                continue
            filas.append({
                "orquesta": f["orquesta"].strip(), "palabras": set(normalizar_nombre(f["orquesta"]).split()),
                "desde": _entero(f["desde"]), "hasta": _entero(f["hasta"]),
                "cantor": set(normalizar_nombre(f["cantor"]).split()),
                "caracter": f["caracter"].strip().lower(), "energia": _entero(f["energia"]) or 3,
                "dificultad": _entero(f["dificultad"]) or 1, "notas": f["notas"].strip(),
            })
        _cache.update(clave=clave, filas=filas)
    return _cache["filas"]


def buscar(orquesta, ano=None, cantor="", archivo=None):
    """Caracter de la orquesta en ese año (con ese cantor), o None si no está en la tabla."""
    palabras = set(normalizar_nombre(orquesta).split())
    if not palabras:
        return None
    candidatas = [f for f in leer(archivo) if f["palabras"] and f["palabras"] <= palabras]
    if not candidatas:
        return None
    cantor_palabras = set(normalizar_nombre(cantor).split())

    def encaja_ano(f):
        if ano is None or (f["desde"] is None and f["hasta"] is None):
            return True
        return (f["desde"] or 0) <= ano <= (f["hasta"] or 9999)

    def distancia(f):
        if ano is None or (f["desde"] is None and f["hasta"] is None):
            return 0
        return max((f["desde"] or 0) - ano, ano - (f["hasta"] or 9999), 0)

    # Primero la que encaja en años y cantor; luego en años; si no, la época más cercana
    def orden(f):
        con_cantor = bool(f["cantor"]) and f["cantor"] <= cantor_palabras
        cantor_no_encaja = bool(f["cantor"]) and not con_cantor
        return (cantor_no_encaja, not encaja_ano(f), distancia(f), not con_cantor)

    f = min(candidatas, key=orden)
    if f["cantor"] and not f["cantor"] <= cantor_palabras:
        return None
    return Caracter(f["orquesta"], f["caracter"], f["energia"], f["dificultad"], f["notas"])


def de_cancion(fila, archivo=None):
    ano = _entero(fila["ano"])
    return buscar(fila["artist1"], ano, fila["artist2"], archivo)


def de_tanda(tanda, archivo=None):
    """Carácter de la tanda: con la mediana de los años y el cantor más repetido."""
    if tanda.es_cortina or tanda.canciones.empty:
        return None
    df = tanda.canciones
    anos = [a for a in map(_entero, df["ano"]) if a]
    cantor = df["artist2"].mode().iloc[0] if not df["artist2"].mode().empty else ""
    orquesta = tanda.orquesta or df["artist1"].iloc[0]
    return buscar(orquesta, int(median(anos)) if anos else None, cantor, archivo)
