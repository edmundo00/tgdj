"""
Canciones para proponer cambios en la playlist: las de la biblioteca de MusicBee (con sus estrellas) que están
en la carpeta del portátil (MUSICA\\Edmundo). Nunca se propone nada de fuera de esa carpeta.

    cat = catalogo()                                   # DataFrame (se lee una vez; ~2,5 s)
    proponer_temas(cat, tandas, fila, k)               # para cambiar el tema k de la tanda
    proponer_tandas(cat, tandas, fila)                 # para cambiar la tanda entera
    proponer_cortinas(cat, tandas, fila, historial)    # para cambiar una cortina
"""
import os
import re
from dataclasses import dataclass
from statistics import median

import pandas as pd

from src.config.config import carpeta_portatil, dropbox_path, musicbee_start_folder
from src.diapos import caracter, historial as historial_mod
from src.diapos.generador import es_tanda
from src.utils.buscar_artista import normalizar_nombre, separar_orquesta_cantor
from src.utils.formato_tags import formatear_fecha

MAX_ANOS = 8                    # como en la revisión: misma época = menos de 8 años de diferencia
DISTANCIA_ORQUESTA = 4          # no proponer una orquesta que ya suena a menos de 4 tandas
TEMAS_POR_TANDA = 3

_cache = {"clave": None, "df": None}


def ruta_biblioteca():
    for sub in ("tango", "Portatil"):
        ruta = os.path.join(musicbee_start_folder, sub, "MusicBeeLibrary.mbl")
        if os.path.exists(ruta):
            return ruta
    return None


def _en_este_ordenador(ruta):
    """La ruta con el Dropbox de este ordenador (D:\\Dropbox en el fijo, C:\\Dropbox en el portátil)."""
    m = re.search(r"[\\/]Dropbox[\\/]", ruta)
    return os.path.join(dropbox_path, ruta[m.end():]) if m else ruta


def catalogo(ruta_mbl=None, carpeta=carpeta_portatil):
    """Canciones de la biblioteca de MusicBee dentro de `carpeta`: ruta, title, artist, artist1, artist2,
    year, ano, genre, composer, duration (s), estrellas (0-5)."""
    ruta_mbl = ruta_mbl or ruta_biblioteca()
    if not ruta_mbl:
        return pd.DataFrame()
    clave = (ruta_mbl, os.path.getmtime(ruta_mbl), carpeta)
    if _cache["clave"] == clave:
        return _cache["df"]
    from src.utils.MusicBeeLibraryTools import MusicBeeLibraryTools
    mb = MusicBeeLibraryTools(None, ruta_mbl).library_df
    # Filtrar por la ruta relativa a Dropbox antes de nada (sin tocar el disco: son 50.000 archivos)
    dentro = historial_mod.clave(carpeta).rstrip("\\") + "\\"
    mb = mb[mb["file_path"].map(historial_mod.clave).str.startswith(dentro)]
    filas = []
    for x in mb.itertuples():
        ruta = _en_este_ordenador(x.file_path)
        orquesta, cantor = separar_orquesta_cantor(x.artist or "")
        valoracion = x.unknown_1 if x.unknown_1 <= 100 else 0          # 255 = sin valorar
        filas.append({
            "ruta": ruta, "title": x.title or os.path.splitext(os.path.basename(ruta))[0], "artist": x.artist or "",
            "artist1": orquesta, "artist2": cantor, "year": x.year or "", "ano": formatear_fecha(x.year)[:4],
            "genre": (x.genre or "").strip().lower(), "composer": x.composer or "",
            "duration": (x.track_length or 0) / 1000, "estrellas": int(round(valoracion / 20)),
        })
    df = pd.DataFrame(filas)
    _cache.update(clave=clave, df=df)
    return df


def _ano(valor):
    return int(valor) if str(valor).isdigit() else None


def _tipo(genero):
    return "vals" if "vals" in genero else "milonga" if "milonga" in genero else "tango"


def _personas(cantor):
    return frozenset(normalizar_nombre(p) for p in re.split(r"\s+y\s+|,\s*|\s*/\s*", cantor or "") if p.strip())


def _titulo(t):
    return re.sub(r"[^a-z0-9]+", " ", normalizar_nombre(re.sub(r"\(.*?\)", "", str(t or "")))).strip()


def _usadas(tandas):
    """Claves de archivo y (orquesta, título) de todo lo que ya suena en la noche."""
    rutas, temas = set(), set()
    for t in tandas:
        for _, c in t.canciones.iterrows():
            rutas.add(historial_mod.clave(c["ruta"]))
            temas.add((normalizar_nombre(c["artist1"]), _titulo(c["title"])))
    return rutas, temas


def _libres(cat, tandas):
    rutas, temas = _usadas(tandas)
    if cat.empty:
        return cat
    claves = cat["ruta"].map(historial_mod.clave)
    tema = list(zip(cat["artist1"].map(normalizar_nombre), cat["title"].map(_titulo)))
    libre = ~claves.isin(rutas) & pd.Series([t not in temas for t in tema], index=cat.index)
    return cat[libre]


def proponer_temas(cat, tandas, fila, k, solo_5=True, maximo=20):
    """Temas para sustituir el k-ésimo de la tanda: misma orquesta, género y época; mismo cantor primero.
    Columna 'motivo' dice por qué encaja."""
    tanda = tandas[fila]
    actual = tanda.canciones.iloc[k]
    otros = tanda.canciones.drop(tanda.canciones.index[k])
    anos = [a for a in map(_ano, otros["ano"] if len(otros) else tanda.canciones["ano"]) if a]
    centro = median(anos) if anos else _ano(actual["ano"])
    orquesta = normalizar_nombre(actual["artist1"])
    cantores = {_personas(c) for c in (otros["artist2"] if len(otros) else [actual["artist2"]])}
    libres = _libres(cat, tandas)
    if libres.empty:
        return libres
    c = libres[(libres["artist1"].map(normalizar_nombre) == orquesta)
               & (libres["genre"].map(_tipo) == _tipo(actual["genre"]))]
    if solo_5:
        c = c[c["estrellas"] >= 5]
    c = c.copy()
    c["_ano"] = c["ano"].map(_ano)
    if centro:
        c = c[c["_ano"].notna() & ((c["_ano"] - centro).abs() <= MAX_ANOS)]
    c["mismo_cantor"] = c["artist2"].map(lambda x: _personas(x) in cantores)
    c["distancia"] = (c["_ano"] - centro).abs() if centro else 0
    c["motivo"] = c["mismo_cantor"].map(lambda m: "mismo cantor" if m else "otro cantor")
    c = c[c["ruta"].map(os.path.exists)]
    c = c.sort_values(["mismo_cantor", "estrellas", "distancia"], ascending=[False, False, True])
    return c.drop(columns=["_ano"]).head(maximo).reset_index(drop=True)


@dataclass
class TandaPropuesta:
    orquesta: str
    cantor: str
    genero: str
    canciones: pd.DataFrame
    energia: float = None
    motivo: str = ""
    dificultad: int = 1

    @property
    def anos(self):
        a = sorted(x for x in map(_ano, self.canciones["ano"]) if x)
        return "" if not a else (str(a[0]) if a[0] == a[-1] else f"{a[0]}–{a[-1]}")


def proponer_tandas(cat, tandas, fila, solo_5=True, maximo=25, archivo_caracter=None):
    """Tandas de 3 temas (misma orquesta, cantor, género y época) para sustituir la tanda `fila`.
    No propone orquestas que ya suenan a menos de DISTANCIA_ORQUESTA tandas."""
    tanda = tandas[fila]
    genero = _tipo(tanda.genero)
    reales = [i for i, t in enumerate(tandas) if not t.es_cortina and not t.es_cumparsita]
    pos = reales.index(fila) if fila in reales else 0
    cerca = {normalizar_nombre(tandas[i].orquesta) for i in reales[max(0, pos - DISTANCIA_ORQUESTA + 1):
                                                                   pos + DISTANCIA_ORQUESTA] if i != fila}
    car_actual = caracter.de_tanda(tanda, archivo_caracter)
    libres = _libres(cat, tandas)
    if libres.empty:
        return []
    c = libres[libres["genre"].map(_tipo) == genero]
    c = c[c["genre"].map(es_tanda)]
    if solo_5:
        c = c[c["estrellas"] >= 5]
    c = c.copy()
    c["_ano"] = c["ano"].map(_ano)
    c = c[c["_ano"].notna()]
    c["_orq"] = c["artist1"].map(normalizar_nombre)
    c["_cantor"] = c["artist2"].map(_personas)
    c = c[~c["_orq"].isin(cerca) & (c["_orq"] != "")]
    propuestas = []
    for (_, _), g in c.groupby(["_orq", "_cantor"]):
        g = g.sort_values("_ano").drop_duplicates(subset=["title"])
        if len(g) < TEMAS_POR_TANDA:
            continue
        # la ventana de 3 temas con menos años de diferencia
        mejor = min(range(len(g) - TEMAS_POR_TANDA + 1),
                    key=lambda n: g["_ano"].iloc[n + TEMAS_POR_TANDA - 1] - g["_ano"].iloc[n])
        trio = g.iloc[mejor:mejor + TEMAS_POR_TANDA]
        if trio["_ano"].iloc[-1] - trio["_ano"].iloc[0] > MAX_ANOS:
            continue
        trio = trio[trio["ruta"].map(os.path.exists)]
        if len(trio) < TEMAS_POR_TANDA:
            continue
        primera = trio.iloc[0]
        car = caracter.buscar(primera["artist1"], int(median(trio["_ano"])), primera["artist2"], archivo_caracter)
        propuestas.append(TandaPropuesta(
            primera["artist1"], primera["artist2"] or "instrumental", genero,
            trio.drop(columns=["_ano", "_orq", "_cantor"]).reset_index(drop=True),
            car.energia if car else None, car.texto if car else "", car.dificultad if car else 1))
    ref = car_actual.energia if car_actual else 3
    primer_tercio = pos < len(reales) / 3

    en_la_noche = {normalizar_nombre(tandas[i].orquesta) for i in reales}
    favoritas = c.groupby("_orq").size().to_dict()          # cuántos temas tiene de esa orquesta

    def orden(p):
        dificil_pronto = primer_tercio and p.dificultad >= 3
        orq = normalizar_nombre(p.orquesta)
        return (dificil_pronto, abs((p.energia if p.energia is not None else 3) - ref), orq in en_la_noche,
                -favoritas.get(orq, 0), p.orquesta)
    return sorted(propuestas, key=orden)[:maximo]


def proponer_cortinas(cat, tandas, fila, historial=(), solo_5=True):
    """Cortinas que no suenan esta noche ni sonaron en este sitio (historial)."""
    libres = _libres(cat, tandas)
    if libres.empty:
        return libres
    c = libres[libres["genre"].str.startswith("cortina")]
    if solo_5:
        c = c[c["estrellas"] >= 5]
    ya = set().union(*(m.claves for m in historial)) if historial else set()
    c = c[~c["ruta"].map(historial_mod.clave).isin(ya)]
    c = c[c["ruta"].map(os.path.exists)]
    return c.sort_values(["artist", "title"]).reset_index(drop=True)
