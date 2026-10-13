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
ANO_EPOCA_DE_ORO = 1965         # para las reservas, primero lo grabado hasta entonces

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
    caracter: str = ""

    @property
    def anos(self):
        a = sorted(x for x in map(_ano, self.canciones["ano"]) if x)
        return "" if not a else (str(a[0]) if a[0] == a[-1] else f"{a[0]}–{a[-1]}")


def _tandas_posibles(cat, tandas, genero, excluir_orquestas=(), solo_5=True, archivo_caracter=None):
    """Todas las tandas de 3 temas (misma orquesta, cantor, género y época) que se pueden formar con lo que no
    suena esa noche. Devuelve (propuestas, {orquesta normalizada: cuántos temas tiene})."""
    libres = _libres(cat, tandas)
    if libres.empty:
        return [], {}
    c = libres[libres["genre"].map(_tipo) == genero]
    c = c[c["genre"].map(es_tanda)]
    if solo_5:
        c = c[c["estrellas"] >= 5]
    c = c.copy()
    c["_ano"] = c["ano"].map(_ano)
    c = c[c["_ano"].notna()]
    c["_orq"] = c["artist1"].map(normalizar_nombre)
    c["_cantor"] = c["artist2"].map(_personas)
    c = c[~c["_orq"].isin(set(excluir_orquestas)) & (c["_orq"] != "")]
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
            car.energia if car else None, car.texto if car else "", car.dificultad if car else 1,
            car.caracter if car else ""))
    return propuestas, c.groupby("_orq").size().to_dict()      # cuántos temas tiene de cada orquesta


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
    propuestas, favoritas = _tandas_posibles(cat, tandas, genero, cerca, solo_5, archivo_caracter)
    ref = car_actual.energia if car_actual else 3
    primer_tercio = pos < len(reales) / 3
    en_la_noche = {normalizar_nombre(tandas[i].orquesta) for i in reales}

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
    c = c[c["ruta"].map(os.path.exists)].copy()
    # al final las dudosas: sin artista o con "tango", "vals" o "milonga" en el título (pueden confundir a la pista)
    c["_dudosa"] = (c["artist"].str.strip() == "") | c["title"].str.lower().str.contains(r"tango|vals|milonga")
    return c.sort_values(["_dudosa", "artist", "title"]).drop(columns="_dudosa").reset_index(drop=True)


SIN_PERDIDA = (".flac", ".wav", ".aiff", ".aif", ".ape", ".wv")
CON_PERDIDA = (".mp3", ".m4a", ".wma", ".aac", ".ogg", ".opus", ".mp4")


def con_perdida(ruta):
    return os.path.splitext(ruta)[1].lower() in CON_PERDIDA


def versiones_sin_perdida(cat, tandas):
    """{ruta en MP3 (u otro formato con pérdida) de la noche: ruta en FLAC (o sin pérdida) de la misma grabación
    en la carpeta del portátil}. Misma grabación = misma orquesta, título, cantor y año; sin año no se propone
    nada (una orquesta pudo grabar el mismo tema varias veces)."""
    buscadas = [c for t in tandas for _, c in t.canciones.iterrows() if con_perdida(c["ruta"])]
    if not buscadas or cat.empty:
        return {}
    sin = cat[cat["ruta"].map(lambda r: os.path.splitext(r)[1].lower() in SIN_PERDIDA)]
    indice = {}
    for _, c in sin.iterrows():
        indice.setdefault((normalizar_nombre(c["artist1"]), _titulo(c["title"])), []).append(c)
    salida = {}
    for c in buscadas:
        for otra in indice.get((normalizar_nombre(c["artist1"]), _titulo(c["title"])), []):
            ano = _ano(c["ano"])
            misma = ano and ano == _ano(otra["ano"]) and _personas(c["artist2"]) == _personas(otra["artist2"])
            if misma and os.path.exists(otra["ruta"]):
                salida[c["ruta"]] = otra["ruta"]
                break
    return salida


# Tandas de reserva: (clave, para qué, género). Se eligen sin repetir orquesta entre ellas.
RESERVAS = [
    ("cumple", "Vals de cumpleaños", "vals"),
    ("ritmica", "Tango rítmico extra (si sobra tiempo o hay que despertar la pista)", "tango"),
    ("final", "Tango tranquilo para el final", "tango"),
]


def opciones_reserva(cat, tandas, clave, solo_5=True, archivo_caracter=None, maximo=15):
    """Opciones para una reserva (la mejor primero). No repiten nada de la noche; el vals no es de una orquesta
    que ya tiene vals esa noche; los tangos no son de las orquestas de las últimas tandas."""
    genero = next(g for c, _, g in RESERVAS if c == clave)
    reales = [t for t in tandas if not t.es_cortina and not t.es_cumparsita]
    if clave == "cumple":
        excluir = {normalizar_nombre(t.orquesta) for t in reales if _tipo(t.genero) == "vals"}
    else:
        excluir = {normalizar_nombre(t.orquesta) for t in reales[-DISTANCIA_ORQUESTA:]}
    propuestas, favoritas = _tandas_posibles(cat, tandas, genero, excluir, solo_5, archivo_caracter)
    en_la_noche = {normalizar_nombre(t.orquesta) for t in reales}

    def orden(p):
        e = p.energia if p.energia is not None else 3
        orq = normalizar_nombre(p.orquesta)
        anos = [a for a in map(_ano, p.canciones["ano"]) if a]
        moderna = bool(anos) and min(anos) > ANO_EPOCA_DE_ORO      # grabaciones actuales, al final
        if clave == "cumple":                       # festivo: mucha energía y fácil
            meta = (-e, p.dificultad)
        elif clave == "ritmica":
            meta = (p.caracter != "ritmico", -e, p.dificultad)
        else:                                       # final: melódico o lírico, tranquilo
            meta = (p.caracter not in ("melodico", "lirico"), abs(e - 2.5))
        return (moderna,) + meta + (orq in en_la_noche, -favoritas.get(orq, 0), p.orquesta)
    return sorted(propuestas, key=orden)[:maximo]


def reserva(cat, tandas, historial=(), solo_5=True, archivo_caracter=None, actividad=None):
    """
    Para cada reserva, (opciones, índice de la elegida) sin repetir orquesta entre ellas; las cortinas posibles
    (de artistas distintos) y cuál va delante de cada reserva: animada antes del vals de cumpleaños y del tango
    rítmico, tranquila antes del tango del final (según la actividad ya medida; las no medidas, en su orden).
    actividad(ruta) -> valor o None (por defecto, la caché de bpm sin calcular nada nuevo).
    """
    elegidas, usadas = {}, set()
    for clave, _, _ in RESERVAS:
        opciones = opciones_reserva(cat, tandas, clave, solo_5, archivo_caracter)
        indice = next((n for n, p in enumerate(opciones) if normalizar_nombre(p.orquesta) not in usadas), None)
        if indice is not None:
            usadas.add(normalizar_nombre(opciones[indice].orquesta))
        elegidas[clave] = (opciones, indice)
    cortinas = proponer_cortinas(cat, tandas, None, historial, solo_5)
    cortinas = cortinas.drop_duplicates(subset=["artist"]).reset_index(drop=True)
    if actividad is None:
        from src.diapos import bpm
        cache = bpm.CacheBpm()
        actividad = lambda ruta: cache.guardado(ruta, bpm.ACTIVIDAD)[1]       # noqa: E731
    from src.diapos.bpm import CORTINA_TRANQUILA, CORTINA_ANIMADA
    medida = [actividad(r) for r in cortinas["ruta"]]
    cortina_de, ocupadas = {}, set()
    for clave, _, _ in RESERVAS:
        libres = [n for n in range(len(cortinas)) if n not in ocupadas]
        if not libres:
            break
        animada = clave != "final"
        # la que mejor encaja de las medidas (nunca una tranquila antes de algo animado, ni al revés);
        # si no hay, una sin medir; y si tampoco, cualquiera
        encajan = [n for n in libres if medida[n] is not None
                   and (medida[n] >= CORTINA_TRANQUILA if animada else medida[n] <= CORTINA_ANIMADA)]
        sin_medir = [n for n in libres if medida[n] is None]
        if encajan:
            n = max(encajan, key=lambda k: medida[k] if animada else -medida[k])
        else:
            n = (sin_medir or libres)[0]
        cortina_de[clave] = n
        ocupadas.add(n)
    return elegidas, cortinas, cortina_de
