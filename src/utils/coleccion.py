"""
Estado de la colección: recorre toda la música, lee las tags (con caché) y resume por carpeta.

La caché (data/cache_coleccion.csv) guarda tamaño y fecha de modificación de cada archivo: la
primera vez se lee todo (unos minutos), después solo lo que haya cambiado.
"""
import os
import re

import pandas as pd

from src.config.config import DATA_FOLDER
from src.utils.formato_tags import formatear_fecha

# Una caché por ordenador: las rutas cambian (D:\Dropbox / C:\Dropbox) y así no se pisan por Dropbox
CACHE = os.path.join(DATA_FOLDER, f"cache_coleccion_{os.environ.get('COMPUTERNAME', 'pc').lower()}.csv")
EXTENSIONES = (".mp3", ".flac", ".m4a", ".wav", ".aif", ".aiff", ".wma", ".ogg")
CAMPOS = ["title", "artist", "album", "year", "genre", "composer"]
CARPETA_DUPLICADOS = "_duplicados"


def listar(raiz):
    """(ruta, colección = primera subcarpeta, tamaño, mtime) de cada archivo de audio."""
    for actual, carpetas, ficheros in os.walk(raiz):
        carpetas[:] = [c for c in carpetas if c != CARPETA_DUPLICADOS]
        coleccion = os.path.relpath(actual, raiz).split(os.sep)[0]
        for f in ficheros:
            if f.lower().endswith(EXTENSIONES):
                ruta = os.path.join(actual, f)
                try:
                    st = os.stat(ruta)
                except OSError:
                    continue
                yield ruta, (coleccion if coleccion != "." else "(raíz)"), st.st_size, int(st.st_mtime)


def escanear(raiz, cache=None, progreso=None, cancelado=None):
    """
    Devuelve un DataFrame con una fila por archivo (ruta, coleccion, bytes, mtime + tags).
    progreso(hechos, total, leidos_de_disco); cancelado() -> True para parar (se guarda lo hecho).
    """
    from src.utils.utils import leer_tags
    cache = cache or CACHE
    previo = {}
    if os.path.exists(cache):
        c = pd.read_csv(cache, sep=";", na_filter=False, dtype=str, encoding="utf-8")
        previo = {r["ruta"]: r for r in c.to_dict("records")}
    archivos = list(listar(raiz))
    filas, leidos = [], 0
    for i, (ruta, coleccion, tamano, mtime) in enumerate(archivos, 1):
        if cancelado and cancelado():
            break
        p = previo.get(ruta)
        if p is not None and p["bytes"] == str(tamano) and p["mtime"] == str(mtime):
            fila = dict(p)
            fila["coleccion"] = coleccion
        else:
            fila = {"ruta": ruta, "coleccion": coleccion, "bytes": str(tamano), "mtime": str(mtime)}
            try:
                t = leer_tags(ruta)
                fila.update({c: str((getattr(t, "year" if c == "year" else c, "") or "")).strip() for c in CAMPOS})
            except Exception:
                fila.update({c: "" for c in CAMPOS})
            leidos += 1
        filas.append(fila)
        if progreso and (i % 200 == 0 or i == len(archivos)):
            progreso(i, len(archivos), leidos)
    df = pd.DataFrame(filas, columns=["ruta", "coleccion", "bytes", "mtime", *CAMPOS]).fillna("")
    # Guardar caché: lo leído ahora + lo que no se ha llegado a recorrer (si se canceló)
    vistos = set(df["ruta"])
    resto = [r for k, r in previo.items() if k not in vistos and os.path.exists(k)]
    pd.concat([df, pd.DataFrame(resto, columns=df.columns)], ignore_index=True).to_csv(
        cache, sep=";", index=False, encoding="utf-8")
    return df


def resumen(df, no_tocar_claves=None):
    """Una fila por colección con los indicadores de orden de la colección (en número de archivos)."""
    from src.utils import no_tocar
    if df.empty:
        return pd.DataFrame()
    fecha = df["year"].map(formatear_fecha)
    ano = pd.to_numeric(fecha.str[:4], errors="coerce")
    artista = df["artist"]
    d = pd.DataFrame({
        "coleccion": df["coleccion"],
        "archivos": 1,
        "gb": pd.to_numeric(df["bytes"], errors="coerce") / 1e9,
        "revisadas": df["composer"].str.match(r"^Musica: .+ - Letra: .+$"),
        "fecha_completa": fecha.str.len() == 10,
        "sin_fecha": fecha == "",
        "fecha_cd": ano >= 1990,
        "artista_raro": artista.str.contains(r";|,| - | feat", regex=True) & ~artista.str.contains(" / ", regex=False),
        "sin_genero": df["genre"].str.strip() == "",
        "no_tocar": [no_tocar.esta(r, no_tocar_claves) for r in df["ruta"]] if no_tocar_claves else False,
    })
    r = d.groupby("coleccion").sum(numeric_only=True)
    r.loc["TOTAL"] = r.sum()
    return r.sort_values("archivos", ascending=False)


class IndiceTengo:
    """
    ¿Tengo esta grabación? Busca en tu colección (la caché) por título + orquesta, sin acentos ni
    mayúsculas. 'si' = también coincide el año; 'otra' = tienes ese tema por esa orquesta pero con
    otra fecha (otra grabación, o la fecha del CD); '' = no lo tienes.
    """

    def __init__(self, df):
        from src.utils.buscador import normalizar
        from src.utils.buscar_artista import normalizar_nombre, separar_orquesta_cantor
        self._normalizar, self._nombre = normalizar, normalizar_nombre
        df = df[~df["ruta"].str.contains(r"[\/]_duplicados[\/]", regex=True)]
        self.archivos = {}
        for ruta, titulo, artista, year in zip(df["ruta"], df["title"], df["artist"], df["year"]):
            if not titulo:
                continue
            orquesta = separar_orquesta_cantor(artista)[0].split(",")[0]
            clave = normalizar(titulo) + "|" + normalizar_nombre(orquesta)
            self.archivos.setdefault(clave, []).append((ruta, formatear_fecha(year)[:4]))

    def buscar(self, titulo, orquesta, fecha):
        """Devuelve ('si' | 'otra' | '', [rutas, primero las del mismo año])."""
        lista = self.archivos.get(self._normalizar(titulo) + "|" + self._nombre(orquesta), [])
        if not lista:
            return "", []
        ano = formatear_fecha(fecha)[:4]
        mismas = [r for r, a in lista if ano and a == ano]
        otras = [r for r, a in lista if r not in mismas]
        return ("si" if mismas else "otra"), mismas + otras
