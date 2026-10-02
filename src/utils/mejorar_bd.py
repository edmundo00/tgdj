"""
Limpieza de la base de datos de grabaciones.

    python -m src.utils.mejorar_bd            (lee data/mergeddb.csv, escribe data/tangodb.csv)

1. Columnas de búsqueda normalizadas (sin acentos ni mayúsculas) para que
   'Humillacion' encuentre 'Humillación'.
2. Una sola grafía por orquesta y por cantor (la más frecuente):
   'Carlos di Sarli' -> 'Carlos Di Sarli', 'Agustin Irusta' -> 'Agustín Irusta'.
3. Compositor: si una fila no lo tiene y todas las demás filas con el mismo título
   que sí lo tienen coinciden en uno solo, se copia. Si hay dudas (dos tangos
   distintos con el mismo nombre) no se toca.
4. Fecha: si una fila no tiene fecha completa y otra fila de la misma grabación
   (mismo título, orquesta y cantor) sí la tiene, y es única, se copia.
5. Informe de las fechas que siguen siendo dudosas (vacías o rangos).
"""
import os
import re
import sys

import pandas as pd
from unidecode import unidecode

from src.utils.buscar_artista import normalizar_nombre
from src.utils.formato_tags import formatear_fecha, separar_compositor_autor, formatear_compositor

DESCONOCIDO = "Musica: ? - Letra: ?"


def normalizar_titulo(titulo):
    """'Humillación' -> 'humillacion' (los números se pasan a palabras, como en la búsqueda)."""
    from src.utils.utils import convert_numbers_to_words
    return unidecode(convert_numbers_to_words(str(titulo or ""))).lower().strip()


def grafia_canonica(serie):
    """Para cada nombre devuelve la grafía más frecuente entre los que se normalizan igual."""
    validos = serie[serie.map(normalizar_nombre) != ""]
    claves = validos.map(normalizar_nombre)
    mas_frecuente = validos.groupby(claves).agg(lambda s: s.value_counts().index[0])
    return serie.map(lambda x: mas_frecuente.get(normalizar_nombre(x), x) if normalizar_nombre(x) else x)


def _compositor_conocido(texto):
    musica, letra = separar_compositor_autor(texto)
    return formatear_compositor(musica, letra) if (musica or letra) else ""


def mejorar(db):
    """Devuelve (base de datos mejorada, dict con el número de cambios de cada tipo, informe de fechas)."""
    db = db.copy()
    cambios = {}

    # 2. Grafías únicas
    for col in ("artista", "cantor"):
        nueva = grafia_canonica(db[col].astype(str))
        cambios[f"{col} unificados"] = int((nueva != db[col]).sum())
        db[col] = nueva

    # 1. Columnas de búsqueda
    db["titulo_min"] = db["titulo"].map(normalizar_titulo)
    db["artista_min"] = db["artista"]          # se agrupa por la grafía canónica
    db["cantor_min"] = db["cantor"].map(lambda x: unidecode(str(x)).lower())

    # 3. Compositores
    conocido = db["compositor_autor"].map(_compositor_conocido)
    por_titulo = conocido[conocido != ""].groupby(db["titulo_min"]).agg(lambda s: set(s))
    unico = por_titulo[por_titulo.map(len) == 1].map(lambda s: next(iter(s)))
    rellenar = (conocido == "") & db["titulo_min"].isin(unico.index)
    db.loc[rellenar, "compositor_autor"] = db.loc[rellenar, "titulo_min"].map(unico)
    cambios["compositores rellenados"] = int(rellenar.sum())

    # 4. Fechas de la misma grabación
    fecha_f = db["fecha"].map(formatear_fecha)
    completa = fecha_f.str.fullmatch(r"\d{4}-\d{2}-\d{2}")
    grabacion = db["titulo_min"] + "|" + db["artista"].map(normalizar_nombre) + "|" + db["cantor"].map(normalizar_nombre)
    por_grabacion = fecha_f[completa].groupby(grabacion[completa]).agg(lambda s: set(s))
    unica = por_grabacion[por_grabacion.map(len) == 1].map(lambda s: next(iter(s)))

    def compatible(i):
        """Solo se rellena si la fecha que había (año o año-mes) no contradice la nueva."""
        nueva = unica.get(grabacion[i])
        return nueva is not None and nueva.startswith(fecha_f[i])

    candidatas = db.index[~completa & grabacion.isin(unica.index)]
    rellenar_fecha = [i for i in candidatas if compatible(i)]
    db.loc[rellenar_fecha, "fecha"] = [unica[grabacion[i]] for i in rellenar_fecha]
    cambios["fechas completadas"] = len(rellenar_fecha)
    db["fecha_ano"] = db["fecha"].map(lambda f: formatear_fecha(f)[:4])

    # 5. Informe de fechas dudosas
    fecha_f = db["fecha"].map(formatear_fecha)
    dudosa = fecha_f == ""
    informe = db.loc[dudosa, ["titulo", "artista", "cantor", "fecha", "origen"]].copy()
    informe["problema"] = informe["fecha"].map(lambda f: "vacía" if not str(f).strip() else "rango / formato raro")
    cambios["fechas dudosas (ver informe)"] = int(dudosa.sum())
    return db, cambios, informe


def main(origen=None, destino=None):
    from src.config.config import DATA_FOLDER, OUTPUT_FOLDER
    origen = origen or os.path.join(DATA_FOLDER, "mergeddb.csv")
    destino = destino or os.path.join(DATA_FOLDER, "tangodb.csv")
    db = pd.read_csv(origen, sep=";", na_filter=False, encoding="utf-8", dtype=str)
    nueva, cambios, informe = mejorar(db)
    nueva.to_csv(destino, sep=";", index=False, encoding="utf-8")
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    ruta_informe = os.path.join(OUTPUT_FOLDER, "informe_fechas_dudosas.csv")
    informe.sort_values(["artista", "titulo"]).to_csv(ruta_informe, sep=";", index=False, encoding="utf-8-sig")
    print(f"{len(nueva)} grabaciones -> {destino}")
    for k, v in cambios.items():
        print(f"  {k}: {v}")
    print(f"Informe: {ruta_informe}")
    return cambios


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:3])
