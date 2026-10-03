"""
Resúmenes de tu colección a partir de la biblioteca (src/biblioteca): el Estado de la colección
por carpeta y "¿la tengo?" para el buscador.
"""
import pandas as pd

from src.biblioteca.biblioteca import CARPETA_DUPLICADOS  # noqa: F401  (se importa desde aquí también)
from src.utils.formato_tags import formatear_fecha


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
