"""
Fases 3 y 4 de PLAN_ORDENAR_MUSICA.md: la FICHA de cada grupo «suena igual» (qué grabación es) y su
COPIA MAESTRA (el archivo que se queda). No toca ningún archivo de música: solo escribe tablas e informes.

    python fichas.py

Ficha (fila de data/tangodb.csv = la base de TangoTags, con tus grafías), por orden de confianza:
  1. «sonido»: en el grupo hay un extracto de El Recodo → su fila (columna audio30), sin mirar tags.
  2. «tags»: votan los archivos del grupo con lo que dijo el emparejado de TangoTags en Mi biblioteca
     (perfecta = 3 votos a su fila, preferida = 2 a la sugerida, dudosa = 1 repartido entre sus opciones).
  3. «sin ficha»: ni sonido ni tags → a revisar.
Maestra: sin cortar (dura como la más larga del grupo, ±3 s) → sin pérdida (flac/wav/aif) → más datos por
segundo → colección preferida (COLECCIONES, abajo) → nombre más corto.

Escribe en huellas.sqlite la tabla `fichas` y aquí al lado _FICHAS.txt (resumen) y _FICHAS.csv (todo, para mirarlo).
"""
import csv
import os
import re
import sqlite3
import time
import unicodedata
from collections import Counter, defaultdict

import pandas as pd

from huellas_todas import AQUI, BD, MUSICA, PREFIJO_RECODO, TGDJ

TANGODB = os.path.join(TGDJ, "data", "tangodb.csv")
DBCSV = os.path.join(TGDJ, "data", "db.csv")
BIBLIOTECA = os.path.join(os.environ["LOCALAPPDATA"], "TangoTags", "biblioteca.sqlite")
# Desempate entre copias igual de buenas (decisión 4 del plan, provisional): primero la tuya
COLECCIONES = ["Edmundo", "HistoTango", "Osvaldo LA YUMBA", "Eduardo", "Dan", "Camilo Gatica", "Leandro",
               "Eva", "Angel", "Carlos Gardel"]
SIN_PERDIDA = {".flac", ".wav", ".aif", ".aiff", ".ape", ".wv"}


def _n(s):
    s = unicodedata.normalize("NFKD", str(s).lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)))


def clave_recodo(url):
    """…/mediatheque/304/40284409.mp3 → '@recodo\\304\\40284409.mp3'"""
    if not url or "/mediatheque/" not in url:
        return ""
    return PREFIJO_RECODO + url.split("/mediatheque/")[1].replace("/", os.sep)


FICHAS_TANGOTAGS = os.path.join(TGDJ, "data", "fichas_sonido.csv")
COLS_TANGOTAGS = ["rel", "fila_bd", "fuente", "grupo", "copias", "maestra", "nota"]


def guardar_para_tangotags(filas):
    """data/fichas_sonido.csv: por archivo (ruta dentro de MUSICA), su fila de tangodb y cómo se supo."""
    tmp = FICHAS_TANGOTAGS + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(COLS_TANGOTAGS)
        for x in filas:
            if x["fila_bd"] != "":
                w.writerow([x[c] for c in COLS_TANGOTAGS])
    os.replace(tmp, FICHAS_TANGOTAGS)


def main():
    t0 = time.time()
    con = sqlite3.connect(BD, timeout=120)
    grupo = dict(con.execute("SELECT rel, grupo FROM grupos"))
    info = {r: (b, d) for r, b, d in con.execute("SELECT rel, bytes, duracion FROM huellas")}
    votos_par = defaultdict(int)
    for a, b, v in con.execute("SELECT a, b, votos FROM parejas"):
        votos_par[(a, b)] = v

    tdb = pd.read_csv(TANGODB, sep=";", dtype=str, na_filter=False)
    fila_de_extracto = {clave_recodo(u): i for i, u in enumerate(tdb["audio30"]) if u}
    raw = pd.read_csv(DBCSV, sep=";", dtype=str, na_filter=False)
    # extractos de El Recodo cuya grabación quedó en tangodb con la ficha de tango.info: por título + fecha
    por_titulo_fecha = {}
    for i, (t, f) in enumerate(zip(tdb["titulo_min"], tdb["fecha"])):
        por_titulo_fecha.setdefault((_n(t), f), i)
    for u, t, f in zip(raw["audio30"], raw["titulo_min"], raw["fecha"]):
        k = clave_recodo(u)
        if k and k not in fila_de_extracto and (_n(t), f) in por_titulo_fecha:
            fila_de_extracto[k] = por_titulo_fecha[(_n(t), f)]
    raw_de_extracto = {clave_recodo(u): i for i, u in enumerate(raw["audio30"]) if u}

    # lo que dijo el emparejado de TangoTags de cada archivo
    tags = {}
    if os.path.exists(BIBLIOTECA):
        b = sqlite3.connect(BIBLIOTECA)
        for ruta, estado, sug, ops, ti, ar, ye in b.execute(
                "SELECT ruta, estado, sugerida, opciones, title, artist, year FROM archivos"):
            rel = os.path.relpath(ruta, MUSICA) if ruta.lower().startswith(MUSICA.lower()) else None
            if rel:
                try:
                    ops = [int(x) for x in ops.strip("[]").split(",") if x.strip()]
                except ValueError:
                    ops = []
                tags[rel] = (estado, sug, ops, ti, ar, ye)

    miembros = defaultdict(list)
    for r, g in grupo.items():
        miembros[g].append(r)

    filas, cuenta = [], Counter()
    for g, m in miembros.items():
        extractos = [r for r in m if r.startswith(PREFIJO_RECODO)]
        archivos = [r for r in m if not r.startswith(PREFIJO_RECODO)]
        if not archivos:
            continue        # extracto de El Recodo que no está en tu música
        ficha, fuente, nota = None, "sin ficha", ""
        # 1. por el sonido
        if extractos:
            idx = [fila_de_extracto[e] for e in extractos if e in fila_de_extracto]
            if idx:
                ficha, fuente = Counter(idx).most_common(1)[0][0], "sonido"
                if len(set(idx)) > 1:
                    nota = f"El Recodo tiene {len(set(idx))} fichas para este sonido"
            else:
                crudas = [raw_de_extracto[e] for e in extractos if e in raw_de_extracto]
                if crudas:
                    fuente, nota = "sonido (solo El Recodo)", f"db.csv fila {crudas[0]}"
        # 2. por los tags
        voto = Counter()
        for r in archivos:
            t = tags.get(r)
            if not t:
                continue
            estado, sug, ops, *_ = t
            if estado == "perfecta" and ops:
                for o in ops:
                    voto[o] += 3 / len(ops)
            elif estado == "preferida" and sug is not None:
                voto[sug] += 2
            elif estado == "dudosa" and ops:
                for o in ops:
                    voto[o] += 1 / len(ops)
        if ficha is None and voto and fuente == "sin ficha":
            (mejor, v), *resto = voto.most_common(2) + [(None, 0)]
            segundo = resto[0][1] if resto else 0
            if v >= 2 and v >= 2 * segundo:
                ficha, fuente = mejor, "tags"
            else:
                fuente, nota = "dudosa", "tags: " + ", ".join(f"{tdb.at[i, 'artista']} {tdb.at[i, 'fecha']}"
                                                             for i, _ in voto.most_common(3))
        elif ficha is not None and voto:
            mejor = voto.most_common(1)[0][0]
            if mejor != ficha and not nota:
                nota = f"los tags decían otra: {tdb.at[mejor, 'artista']} · {tdb.at[mejor, 'titulo']} · {tdb.at[mejor, 'fecha']}"
        cuenta[fuente] += 1

        # 4. copia maestra
        dur_max = max(info[r][1] for r in archivos)

        def puntos(r):
            tam, dur = info[r]
            ext = os.path.splitext(r)[1].lower()
            col = r.split(os.sep)[0]
            return (dur >= dur_max - 3, ext in SIN_PERDIDA, round(tam / max(dur, 1) / 20000),
                    -(COLECCIONES.index(col) if col in COLECCIONES else 99), -len(r))
        maestra = max(archivos, key=puntos)
        f = tdb.loc[ficha] if ficha is not None else None
        for r in archivos:
            filas.append(dict(
                grupo=g, maestra=int(r == maestra), rel=r, copias=len(archivos), fuente=fuente,
                fila_bd=ficha if ficha is not None else "",
                orquesta=f["artista"] if f is not None else "", cantor=f["cantor"] if f is not None else "",
                titulo=f["titulo"] if f is not None else "", fecha=f["fecha"] if f is not None else "",
                estilo=f["estilo"] if f is not None else "", nota=nota,
                tags_ahora=" · ".join(str(x) for x in tags.get(r, ("", "", "", "", "", ""))[3:]),
                mb=round(info[r][0] / 1e6, 1), segundos=round(info[r][1])))

    con.execute("DROP TABLE IF EXISTS fichas")
    cols = list(filas[0].keys())
    con.execute(f"CREATE TABLE fichas ({', '.join(cols)})")
    con.executemany(f"INSERT INTO fichas VALUES ({', '.join('?' * len(cols))})", [tuple(x.values()) for x in filas])
    con.commit()
    # Copia pequeña para TangoTags (en Dropbox: vale en los dos PC): la usa src/motor/por_sonido.py
    guardar_para_tangotags(filas)
    with open(os.path.join(AQUI, "_FICHAS.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, cols, delimiter=";")
        w.writeheader()
        w.writerows(sorted(filas, key=lambda x: (x["orquesta"], x["fecha"], x["titulo"], x["grupo"], -x["maestra"])))

    grupos_n = len({x["grupo"] for x in filas})
    sobran = [x for x in filas if not x["maestra"]]
    ed = [x for x in filas if x["rel"].lower().startswith("edmundo" + os.sep)]
    ed_sobran = [x for x in ed if not x["maestra"]]
    txt = [f"Fichas y copias maestras · {time.strftime('%d-%m-%Y %H:%M')} · {time.time() - t0:.0f} s",
           f"Archivos: {len(filas)} → grabaciones distintas: {grupos_n}",
           "Cómo se sabe qué grabación es (grupos):"]
    txt += [f"  {k}: {v}" for k, v in cuenta.most_common()]
    txt += [f"Archivos que sobran (no son la maestra): {len(sobran)} · {sum(x['mb'] for x in sobran) / 1000:.1f} GB",
            f"Carpeta Edmundo: {len(ed)} archivos; {len(ed_sobran)} no son la maestra de su grupo "
            f"({sum(x['mb'] for x in ed_sobran) / 1000:.1f} GB)",
            f"Todo en _FICHAS.csv (abrir con Excel; una fila por archivo, maestra=1 la que se queda)."]
    with open(os.path.join(AQUI, "_FICHAS.txt"), "w", encoding="utf8") as fh:
        fh.write("\n".join(txt) + "\n")
    print("\n".join(txt))


if __name__ == "__main__":
    main()
