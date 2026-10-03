"""
Biblioteca: toda tu música en una base de datos local (SQLite), al día de forma incremental.

    bib = Biblioteca()                       # abre (o crea) %LOCALAPPDATA%\\TangoTags\\biblioteca.sqlite
    informe = bib.actualizar(progreso=..., cancelado=...)
    df = bib.dataframe()                     # una fila por archivo (ruta, colección, tags, llegada…)

Qué carpetas entran: data/biblioteca.json (en Dropbox, compartido entre ordenadores), con rutas
relativas a Dropbox. Por defecto: TDJ/MUSICA (cada subcarpeta es una colección; sin
musica_variada_edmundo) y TDJ/TIDAL Download (la bandeja de entrada: una sola colección).

Actualizar en dos niveles, para que sea rápido:
  1. Recorrer las carpetas mirando solo tamaño y fecha de modificación (sin abrir archivos):
     nuevas, cambiadas, desaparecidas. Una desaparecida + una nueva con el mismo audio (huella)
     es una canción MOVIDA: se conserva su fila (y su fecha de llegada) con la ruta nueva.
  2. Leer las tags solo de lo nuevo o cambiado. Se guarda cada 200, así que si se corta,
     la siguiente vez sigue donde iba.
Los archivos "solo en la nube" de Dropbox no se abren (se marcan en_nube) para no forzar descargas.

La base de datos es una caché: si se borra, se reconstruye sola.
"""
import json
import os
import sqlite3
import threading
import time

import pandas as pd

from src.config.config import DATA_FOLDER, dropbox_path

EXTENSIONES = (".mp3", ".flac", ".m4a", ".wav", ".aif", ".aiff", ".wma", ".ogg")
CARPETA_DUPLICADOS = "_duplicados"
CONFIG = os.path.join(DATA_FOLDER, "biblioteca.json")
CONFIG_POR_DEFECTO = {
    "raices": [
        {"ruta": "TDJ/MUSICA", "subcarpetas_son_colecciones": True, "excluir": ["musica_variada_edmundo"]},
        {"ruta": "TDJ/TIDAL Download", "subcarpetas_son_colecciones": False, "excluir": []},
    ]
}
CAMPOS_TAGS = ("title", "artist", "album", "year", "genre", "composer")
LOTE = 200
_ACTUALIZANDO = threading.Lock()     # una sola actualización a la vez (la de arrancar y la del botón)
# Atributos de Windows de los archivos "solo en la nube" (Dropbox / OneDrive)
_EN_NUBE = 0x400000 | 0x1000     # FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS | FILE_ATTRIBUTE_OFFLINE

ESQUEMA = """
CREATE TABLE IF NOT EXISTS archivos (
    id            INTEGER PRIMARY KEY,
    ruta          TEXT UNIQUE NOT NULL,
    raiz          TEXT NOT NULL,
    coleccion     TEXT NOT NULL,
    carpeta       TEXT NOT NULL,
    ext           TEXT,
    bytes         INTEGER,
    mtime         INTEGER,
    creado        REAL,              -- llegada al disco (fecha de creación del archivo)
    visto_primera REAL,              -- primera vez que lo vio la biblioteca
    visto_ultima  REAL,
    en_nube       INTEGER DEFAULT 0,
    tags_leidas   INTEGER DEFAULT 0,
    error         TEXT DEFAULT '',
    title TEXT DEFAULT '', artist TEXT DEFAULT '', album TEXT DEFAULT '',
    year TEXT DEFAULT '', genre TEXT DEFAULT '', composer TEXT DEFAULT '',
    huella        TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS i_coleccion ON archivos(coleccion);
CREATE INDEX IF NOT EXISTS i_creado ON archivos(creado);
CREATE INDEX IF NOT EXISTS i_visto ON archivos(visto_primera);
CREATE INDEX IF NOT EXISTS i_bytes ON archivos(bytes);
CREATE TABLE IF NOT EXISTS meta (clave TEXT PRIMARY KEY, valor TEXT);
"""


def ruta_bd_por_defecto():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "TangoTags", "biblioteca.sqlite")


def leer_config(archivo=None):
    archivo = archivo or CONFIG
    if os.path.exists(archivo):
        with open(archivo, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(json.dumps(CONFIG_POR_DEFECTO))


def guardar_config(config, archivo=None):
    archivo = archivo or CONFIG
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def raices_absolutas(config, base=None):
    """[(ruta absoluta, subcarpetas_son_colecciones, excluir)] (rutas relativas a Dropbox)."""
    base = base or dropbox_path
    salida = []
    for r in config["raices"]:
        ruta = r["ruta"] if os.path.isabs(r["ruta"]) else os.path.join(base, *r["ruta"].replace("\\", "/").split("/"))
        salida.append((os.path.normpath(ruta), r.get("subcarpetas_son_colecciones", False), set(r.get("excluir", []))))
    return salida


def en_nube(st):
    return bool(getattr(st, "st_file_attributes", 0) & _EN_NUBE)


def recorrer(raices):
    """Archivos de audio de todas las raíces: dict ruta -> (raiz, coleccion, carpeta, ext, st)."""
    encontrados = {}
    for raiz, por_subcarpeta, excluir in raices:
        if not os.path.isdir(raiz):
            continue
        nombre_raiz = os.path.basename(raiz)
        for actual, carpetas, ficheros in os.walk(raiz):
            rel = os.path.relpath(actual, raiz)
            if rel == ".":
                carpetas[:] = [c for c in carpetas if c != CARPETA_DUPLICADOS and c not in excluir]
            else:
                carpetas[:] = [c for c in carpetas if c != CARPETA_DUPLICADOS]
            primera = rel.split(os.sep)[0] if rel != "." else ""
            coleccion = (primera or "(raíz)") if por_subcarpeta else nombre_raiz
            for f in ficheros:
                ext = os.path.splitext(f)[1].lower()
                if ext not in EXTENSIONES:
                    continue
                ruta = os.path.join(actual, f)
                try:
                    st = os.stat(ruta)
                except OSError:
                    continue
                encontrados[ruta] = (raiz, coleccion, actual, ext, st)
    return encontrados


class Biblioteca:
    def __init__(self, ruta_bd=None, config=None, base=None):
        self.ruta_bd = ruta_bd or ruta_bd_por_defecto()
        os.makedirs(os.path.dirname(self.ruta_bd), exist_ok=True)
        self.config = config if config is not None else leer_config()
        self.base = base
        with self.conexion() as con:
            con.executescript(ESQUEMA)

    def conexion(self):
        """Una conexión nueva (cada hilo usa la suya). WAL: se puede leer mientras otro escribe."""
        con = sqlite3.connect(self.ruta_bd, timeout=30)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        return con

    # ------------------------------------------------------------------ meta
    def meta(self, clave, defecto=None):
        with self.conexion() as con:
            fila = con.execute("SELECT valor FROM meta WHERE clave=?", (clave,)).fetchone()
        return fila[0] if fila else defecto

    def poner_meta(self, clave, valor):
        with self.conexion() as con:
            con.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (clave, str(valor)))

    def empezar_sesion(self):
        """Apunta el inicio de esta sesión; 'nuevas desde la última vez' = vistas después de la anterior."""
        anterior = self.meta("sesion_actual")
        if anterior is not None:
            self.poner_meta("sesion_anterior", anterior)
        self.poner_meta("sesion_actual", time.time())

    def inicio_sesion_anterior(self):
        valor = self.meta("sesion_anterior")
        return float(valor) if valor else None

    # ------------------------------------------------------------------ actualizar
    def actualizar(self, progreso=None, cancelado=None, leer=None, huella=None):
        """
        progreso(fase, hechos, total). Devuelve un informe con nuevas, cambiadas, movidas, borradas,
        leidas, en_nube, errores y segundos. leer/huella se pueden inyectar en los tests.
        """
        from src.utils.utils import leer_tags
        from src.utils.duplicados import huella as huella_audio
        leer = leer or leer_tags
        huella = huella or huella_audio
        cancelado = cancelado or (lambda: False)
        with _ACTUALIZANDO:
            return self._actualizar(progreso, cancelado, leer, huella)

    @staticmethod
    def actualizando():
        return _ACTUALIZANDO.locked()

    def _actualizar(self, progreso, cancelado, leer, huella):
        informe = dict(nuevas=0, cambiadas=0, movidas=0, borradas=0, leidas=0, en_nube=0, errores=0)
        t0 = time.time()
        ahora = time.time()

        # ---- Nivel 1: mirar (tamaño y fecha) --------------------------------------------
        if progreso:
            progreso("mirar", 0, 0)
        disco = recorrer(raices_absolutas(self.config, self.base))
        if cancelado():
            return informe
        con = self.conexion()
        try:
            guardado = {r: (i, b, m) for i, r, b, m in con.execute("SELECT id, ruta, bytes, mtime FROM archivos")}
            nuevas = [r for r in disco if r not in guardado]
            desaparecidas = [r for r in guardado if r not in disco]

            # Movidas: una desaparecida y una nueva que son el mismo archivo. Pruebas, de más a menos segura:
            #   misma huella de audio (si estaba guardada) · mismo tamaño exacto y mismo nombre ·
            #   mismo tamaño exacto y es el único par posible con ese tamaño
            por_tamano = {}
            for r in desaparecidas:
                por_tamano.setdefault(guardado[r][1], []).append(r)
            nuevas_por_tamano = {}
            for r in nuevas:
                nuevas_por_tamano.setdefault(disco[r][4].st_size, []).append(r)
            movidas = {}
            for r in nuevas:
                tamano = disco[r][4].st_size
                candidatas = por_tamano.get(tamano, [])
                if not candidatas:
                    continue
                elegida = None
                guardadas = dict(con.execute(
                    f"SELECT ruta, huella FROM archivos WHERE ruta IN ({','.join('?' * len(candidatas))})",
                    candidatas))
                if any(guardadas.values()) and not en_nube(disco[r][4]):
                    try:
                        h_nueva = huella(r)
                        elegida = next((v for v in candidatas if guardadas.get(v) == h_nueva), None)
                    except OSError:
                        pass
                if elegida is None:
                    elegida = next((v for v in candidatas
                                    if os.path.basename(v).lower() == os.path.basename(r).lower()), None)
                if elegida is None and len(candidatas) == 1 and len(nuevas_por_tamano[tamano]) == 1:
                    elegida = candidatas[0]
                if elegida is not None:
                    movidas[r] = elegida
                    candidatas.remove(elegida)

            for nueva, vieja in movidas.items():
                raiz, coleccion, carpeta, ext, st = disco[nueva]
                con.execute("""UPDATE archivos SET ruta=?, raiz=?, coleccion=?, carpeta=?, ext=?, mtime=?,
                               visto_ultima=? WHERE ruta=?""",
                            (nueva, raiz, coleccion, carpeta, ext, int(st.st_mtime), ahora, vieja))
            informe["movidas"] = len(movidas)
            borrar = [r for r in desaparecidas if r not in movidas.values()]
            con.executemany("DELETE FROM archivos WHERE ruta=?", [(r,) for r in borrar])
            informe["borradas"] = len(borrar)

            for r in nuevas:
                if r in movidas:
                    continue
                raiz, coleccion, carpeta, ext, st = disco[r]
                nube = en_nube(st)
                con.execute("""INSERT INTO archivos (ruta, raiz, coleccion, carpeta, ext, bytes, mtime, creado,
                               visto_primera, visto_ultima, en_nube, tags_leidas) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)""",
                            (r, raiz, coleccion, carpeta, ext, st.st_size, int(st.st_mtime), st.st_ctime,
                             ahora, ahora, int(nube)))
            informe["nuevas"] = len(nuevas) - len(movidas)

            for r, (i, b, m) in guardado.items():
                if r not in disco:
                    continue
                raiz, coleccion, carpeta, ext, st = disco[r]
                cambiada = b != st.st_size or m != int(st.st_mtime)
                if cambiada:
                    con.execute("""UPDATE archivos SET bytes=?, mtime=?, tags_leidas=0, huella='', en_nube=?,
                                   raiz=?, coleccion=?, carpeta=?, visto_ultima=? WHERE id=?""",
                                (st.st_size, int(st.st_mtime), int(en_nube(st)), raiz, coleccion, carpeta, ahora, i))
                    informe["cambiadas"] += 1
                else:
                    con.execute("UPDATE archivos SET raiz=?, coleccion=?, carpeta=?, en_nube=?, visto_ultima=? "
                                "WHERE id=?", (raiz, coleccion, carpeta, int(en_nube(st)), ahora, i))
            con.commit()

            # ---- Nivel 2: leer tags de lo nuevo o cambiado --------------------------------
            pendientes = con.execute("SELECT id, ruta FROM archivos WHERE tags_leidas=0 AND en_nube=0").fetchall()
            informe["en_nube"] = con.execute("SELECT COUNT(*) FROM archivos WHERE en_nube=1").fetchone()[0]
            for n, (i, ruta) in enumerate(pendientes, 1):
                if cancelado():
                    break
                try:
                    t = leer(ruta)
                    valores = [str(getattr(t, c, "") or "").strip() for c in CAMPOS_TAGS]
                    con.execute(f"UPDATE archivos SET {', '.join(c + '=?' for c in CAMPOS_TAGS)}, "
                                "tags_leidas=1, error='' WHERE id=?", (*valores, i))
                    informe["leidas"] += 1
                except Exception as e:
                    con.execute("UPDATE archivos SET tags_leidas=1, error=? WHERE id=?", (str(e)[:200], i))
                    informe["errores"] += 1
                if n % LOTE == 0:
                    con.commit()
                    if progreso:
                        progreso("leer", n, len(pendientes))
            con.commit()
            if progreso:
                progreso("leer", len(pendientes), len(pendientes))
        finally:
            con.close()
        informe["segundos"] = round(time.time() - t0, 1)
        self.poner_meta("ultima_actualizacion", time.time())
        return informe

    # ------------------------------------------------------------------ importar caché antigua
    def importar_cache_csv(self, ruta_csv):
        """
        Aprovecha la caché CSV del Estado de la colección (ya tiene las tags leídas) para que la
        primera construcción no tenga que leer 50.000 archivos. Solo importa filas cuyo archivo
        sigue igual (mismo tamaño y fecha). Devuelve cuántas importó.
        """
        if not os.path.exists(ruta_csv):
            return 0
        df = pd.read_csv(ruta_csv, sep=";", na_filter=False, dtype=str, encoding="utf-8")
        disco = recorrer(raices_absolutas(self.config, self.base))
        filas = []
        for f in df.to_dict("records"):
            d = disco.get(f["ruta"])
            if d is None:
                continue
            raiz, coleccion, carpeta, ext, st = d
            if str(st.st_size) != f["bytes"] or str(int(st.st_mtime)) != f["mtime"]:
                continue
            # La llegada es la fecha de creación: así 'últimos 7 días' funciona desde el primer día
            filas.append((f["ruta"], raiz, coleccion, carpeta, ext, st.st_size, int(st.st_mtime), st.st_ctime,
                          st.st_ctime, time.time(), int(en_nube(st)),
                          *(f.get(c, "") for c in CAMPOS_TAGS)))
        with self.conexion() as con:
            con.executemany(f"""INSERT OR IGNORE INTO archivos (ruta, raiz, coleccion, carpeta, ext, bytes, mtime,
                               creado, visto_primera, visto_ultima, en_nube, {', '.join(CAMPOS_TAGS)}, tags_leidas)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,{','.join('?' * len(CAMPOS_TAGS))},1)""", filas)
        return len(filas)

    # ------------------------------------------------------------------ consultar
    def dataframe(self, donde="", parametros=()):
        """Archivos como DataFrame (columnas: id, ruta, coleccion, bytes, mtime, creado, tags…)."""
        with self.conexion() as con:
            df = pd.read_sql_query(f"SELECT * FROM archivos {('WHERE ' + donde) if donde else ''}", con,
                                   params=parametros)
        for c in CAMPOS_TAGS + ("error", "huella"):
            df[c] = df[c].fillna("").astype(str)
        df["bytes"] = df["bytes"].astype("int64")
        return df

    def cuantos(self):
        with self.conexion() as con:
            return con.execute("SELECT COUNT(*) FROM archivos").fetchone()[0]

    def huellas(self, rutas, huella=None):
        """Huella de audio de cada ruta, calculándola solo si no estaba guardada (para duplicados)."""
        from src.utils.duplicados import huella as huella_audio
        huella = huella or huella_audio
        salida = {}
        with self.conexion() as con:
            guardadas = dict(con.execute(
                f"SELECT ruta, huella FROM archivos WHERE ruta IN ({','.join('?' * len(rutas))})", list(rutas)))
            for r in rutas:
                h = guardadas.get(r) or ""
                if not h:
                    try:
                        h = huella(r)
                    except OSError:
                        continue
                    con.execute("UPDATE archivos SET huella=? WHERE ruta=?", (h, r))
                salida[r] = h
        return salida
