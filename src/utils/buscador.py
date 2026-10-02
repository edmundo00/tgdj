"""
Motor de búsqueda de grabaciones en la base de datos (sin interfaz).

    indice = IndiceBusqueda(db)
    resultados = indice.buscar("pugliese chanel 1944", estilos={"tango"}, fuentes={"recodo"})

- Una sola caja: las palabras pueden ir en cualquier orden y estar en cualquier campo
  (título, orquesta, cantor, compositor). Sin acentos ni mayúsculas.
- Los años se reconocen solos: '1944' (ese año), '1940-1945' (rango), '1940s' (década).
- Las filas repetidas de la misma grabación (mismo título, orquesta, cantor y fecha,
  normalmente de El Recodo y de tango.info) se agrupan en una sola, con todas sus fuentes.
- Orden por relevancia: título exacto, título que empieza por lo buscado, palabras en el
  título, y después por orquesta y fecha.
"""
import re

import pandas as pd
from unidecode import unidecode

from src.utils.buscar_artista import normalizar_nombre
from src.utils.formato_tags import (
    formatear_fecha, formatear_estilo, formatear_cantores, separar_compositor_autor,
)

NOMBRES_FUENTE = {"recodo": "El Recodo", "tangoinfo": "tango.info"}

# Filtros de estilo: clave -> función sobre el estilo formateado
ESTILOS = {
    "tango": lambda e: e == "tango",
    "vals": lambda e: "vals" in e,
    "milonga": lambda e: "milonga" in e,
    "otros": lambda e: not any(x in e for x in ("tango", "vals", "milonga")),
}


def normalizar(texto):
    """'Adiós, Bardi' -> 'adios bardi' (sin acentos, mayúsculas ni puntuación)."""
    texto = unidecode(str(texto or "")).lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def interpretar_consulta(texto):
    """'firpo rosa 1920-1930' -> (['firpo', 'rosa'], 1920, 1930)."""
    palabras, desde, hasta = [], None, None
    for token in unidecode(str(texto or "")).lower().split():
        m = re.fullmatch(r"(\d{4})(?:-|\.\.)(\d{4})", token)
        if m:
            desde, hasta = sorted((int(m.group(1)), int(m.group(2))))
            continue
        m = re.fullmatch(r"(\d{3})0s", token)
        if m:
            desde, hasta = int(m.group(1) + "0"), int(m.group(1) + "9")
            continue
        if re.fullmatch(r"(18|19|20)\d{2}", token):
            desde = hasta = int(token)
            continue
        palabras.append(token)
    return palabras, desde, hasta


class IndiceBusqueda:
    def __init__(self, db):
        self.grabaciones = self._agrupar(db)

    @staticmethod
    def _agrupar(db):
        d = pd.DataFrame({
            "titulo": db["titulo"].astype(str).str.strip(),
            "orquesta": db["artista"].astype(str).str.strip(),
            "cantor": db["cantor"].map(formatear_cantores),
            "fecha": db["fecha"].map(formatear_fecha),
            "estilo": db["estilo"].map(formatear_estilo),
            "compositor_autor": db["compositor_autor"].astype(str),
            "audio30": db.get("audio30", pd.Series("", index=db.index)).astype(str).str.strip(),
            "audio10": db.get("audio10", pd.Series("", index=db.index)).astype(str).str.strip(),
            "origen": db.get("origen", pd.Series("", index=db.index)).astype(str),
            "corregida": db.get("corregida", pd.Series(False, index=db.index)).astype(bool),
            "indice_bd": db.index,
        })
        musica_letra = d["compositor_autor"].map(separar_compositor_autor)
        d["musica"] = musica_letra.map(lambda x: x[0])
        d["letra"] = musica_letra.map(lambda x: x[1])
        d["clave"] = (d["titulo"].map(normalizar) + "|" + d["orquesta"].map(normalizar_nombre) + "|"
                      + d["cantor"].map(normalizar_nombre) + "|" + d["fecha"])
        # Dentro de cada grabación, primero la fila con más datos
        d["_datos"] = (d["musica"] != "").astype(int) + (d["letra"] != "").astype(int) \
            + (d["audio30"] != "").astype(int) + (d["fecha"].str.len() == 10).astype(int)
        d = d.sort_values("_datos", ascending=False, kind="stable")

        # "first" de pandas salta los vacíos si son NaN: así se toma el primer dato no vacío
        rellenables = ["estilo", "musica", "letra", "audio30", "audio10"]
        d[rellenables] = d[rellenables].replace("", pd.NA)
        grupos = d.groupby("clave", sort=False)
        g = grupos.agg(titulo=("titulo", "first"), orquesta=("orquesta", "first"), cantor=("cantor", "first"),
                       fecha=("fecha", "first"), compositor_autor=("compositor_autor", "first"),
                       indice_bd=("indice_bd", "first"), repeticiones=("titulo", "size"),
                       corregida=("corregida", "any"))
        g = g.join(grupos[rellenables].first()).fillna({c: "" for c in rellenables})
        en = {f: (d["origen"] == f).groupby(d["clave"], sort=False).any() for f in ("recodo", "tangoinfo")}
        g["fuentes"] = [tuple(f for f in ("recodo", "tangoinfo") if en[f][c]) for c in g.index]
        g = g.reset_index(drop=True)
        g["ano"] = pd.to_numeric(g["fecha"].str[:4], errors="coerce")
        g["_titulo_n"] = g["titulo"].map(normalizar)
        g["_todo_n"] = (g["_titulo_n"] + " | " + g["orquesta"].map(normalizar) + " | " + g["cantor"].map(normalizar)
                        + " | " + g["musica"].map(normalizar) + " | " + g["letra"].map(normalizar))
        return g

    def buscar(self, texto, estilos=None, fuentes=None, desde=None, hasta=None):
        """
        estilos: conjunto de claves de ESTILOS (None = todos). fuentes: {'recodo', 'tangoinfo'} (None = todas).
        desde/hasta: años; los que vengan en el texto tienen prioridad.
        Devuelve un DataFrame ordenado por relevancia.
        """
        palabras, d_texto, h_texto = interpretar_consulta(texto)
        palabras = [normalizar(p) for p in palabras if normalizar(p)]
        desde = d_texto if d_texto is not None else desde
        hasta = h_texto if h_texto is not None else hasta
        g = self.grabaciones
        mascara = pd.Series(True, index=g.index)
        for p in palabras:   # cada palabra tiene que estar al comienzo de alguna palabra
            mascara &= g["_todo_n"].str.contains(rf"\b{re.escape(p)}", regex=True)
        if desde is not None:
            mascara &= g["ano"] >= desde
        if hasta is not None:
            mascara &= g["ano"] <= hasta
        if estilos:
            mascara &= g["estilo"].map(lambda e: any(ESTILOS[k](e) for k in estilos))
        if fuentes:
            mascara &= g["fuentes"].map(lambda fs: bool(set(fs) & set(fuentes)))
        r = g[mascara].copy()
        if r.empty or not palabras:
            return r.sort_values(["_titulo_n", "ano"], kind="stable") if not r.empty else r

        titulo = r["_titulo_n"]
        orquesta = r["orquesta"].map(normalizar)
        persona = orquesta + " " + r["cantor"].map(normalizar)
        relevancia = pd.Series(0, index=r.index)
        en_titulo = []
        for p in palabras:
            # Una palabra que es la orquesta o el cantor de esa fila no cuenta para el título ("di" de Di Sarli)
            es_persona = persona.str.contains(rf"\b{re.escape(p)}\b", regex=True)
            palabra_entera = titulo.str.contains(rf"\b{re.escape(p)}\b", regex=True) & ~es_persona
            empieza = titulo.str.contains(rf"\b{re.escape(p)}", regex=True) & ~es_persona
            relevancia += palabra_entera * 15 + empieza * 8
            relevancia += orquesta.str.contains(rf"\b{re.escape(p)}", regex=True) * 3
            en_titulo.append(empieza)
        # Las palabras buscadas que están en el título, juntas: ¿es el título entero o su comienzo?
        for i in r.index:
            frase = " ".join(p for p, m in zip(palabras, en_titulo) if m[i])
            if frase and titulo[i] == frase:
                relevancia[i] += 100
            elif frase and titulo[i].startswith(frase):
                relevancia[i] += 40
        r["_relevancia"] = relevancia
        r["_ano_orden"] = r["ano"].fillna(9999)
        r["_orquesta_n"] = orquesta
        return r.sort_values(["_relevancia", "_titulo_n", "_orquesta_n", "_ano_orden"],
                             ascending=[False, True, True, True], kind="stable")

    def orquestas(self):
        """Orquestas de la base de datos, las más frecuentes primero (para autocompletar)."""
        return list(self.grabaciones["orquesta"].value_counts().index)
