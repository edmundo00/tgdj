"""
Revisión de la playlist antes de crear las diapos (sin interfaz).

    avisos = revisar(tandas, faltan, inicio="21:00", fin="00:00")

Cada Aviso dice su gravedad, el texto y a qué fila de `tandas` se refiere (None = a toda la playlist):
  ERROR  algo que en la milonga falla (no está en el portátil, falta una cortina, tema repetido…)
  AVISO  algo que rompe las reglas de las tandas (cantores mezclados, años lejanos, orquesta repetida cerca…)
  INFO   para tenerlo en cuenta (duración total, Pugliese pronto, pocas instrumentales…)
"""
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from unidecode import unidecode

from src.config.config import carpeta_portatil
from src.diapos.generador import compositor_para_diapo
from src.utils.buscar_artista import normalizar_nombre

ERROR, AVISO, INFO = "error", "aviso", "info"

TEMAS_POR_TANDA = (3, 4)
MAX_ANOS_EN_TANDA = 5          # más años de diferencia dentro de una tanda -> aviso
DISTANCIA_ORQUESTA = 4         # la misma orquesta / cantor a menos de estas tandas -> aviso
MAX_TANGOS_SEGUIDOS = 4
SEGUNDOS_CORTINA = 60          # lo mismo que estima la ventana de diapos
_EN_NUBE = 0x400000 | 0x1000   # Dropbox "solo en la nube" (como en la biblioteca)


@dataclass
class Aviso:
    nivel: str
    texto: str
    fila: int = None           # índice en la lista de tandas (incluidas las cortinas)


def _genero_corto(genero):
    if "vals" in genero:
        return "vals"
    if "milonga" in genero:
        return "milonga"
    return "tango"


def _personas(cantor):
    """'Lita Morales y Horacio Lagos' -> {'lita morales', 'horacio lagos'}."""
    return {normalizar_nombre(p) for p in re.split(r"\s+y\s+|,\s*|\s*/\s*", cantor or "") if p.strip()}


def _titulo(t):
    t = re.sub(r"\(.*?\)", "", unidecode(str(t or "")).lower())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _dentro_de(ruta, carpeta):
    ruta, carpeta = os.path.normcase(os.path.abspath(ruta)), os.path.normcase(os.path.abspath(carpeta))
    return ruta.startswith(carpeta.rstrip("\\/") + os.sep)


def _en_nube(ruta):
    try:
        return bool(getattr(os.stat(ruta), "st_file_attributes", 0) & _EN_NUBE)
    except OSError:
        return False


def _bloques_orquesta(df):
    """Trozos seguidos de la misma orquesta: [(orquesta, n_temas), …]."""
    bloques = []
    for orq in df["artist1"]:
        if bloques and normalizar_nombre(bloques[-1][0]) == normalizar_nombre(orq):
            bloques[-1][1] += 1
        else:
            bloques.append([orq, 1])
    return bloques


def minutos(segundos):
    return int(round(segundos / 60))


def horas_de_inicio(tandas, inicio):
    """Hora a la que empieza cada fila ('21:37'), estimando SEGUNDOS_CORTINA por cortina."""
    try:
        t = datetime.strptime(inicio, "%H:%M")
    except (TypeError, ValueError):
        return [""] * len(tandas)
    horas = []
    for tanda in tandas:
        horas.append(t.strftime("%H:%M"))
        t += timedelta(seconds=SEGUNDOS_CORTINA * len(tanda.canciones) if tanda.es_cortina else tanda.duracion)
    return horas


def revisar(tandas, faltan=(), inicio=None, fin=None, carpeta=carpeta_portatil):
    avisos = []
    nombre_carpeta = os.path.relpath(carpeta, os.path.dirname(os.path.dirname(carpeta))) if carpeta else ""

    for ruta in faltan:
        avisos.append(Aviso(ERROR, f"No existe el archivo: {ruta}"))

    reales = [(i, t) for i, t in enumerate(tandas) if not t.es_cortina]
    numero = {i: n for n, (i, _) in enumerate(reales, 1)}      # fila -> número de tanda

    def nombre(i):
        return f"Tanda {numero[i]}" if i in numero else "Cortina"

    # --- Archivos: en el portátil, descargados, una sola vez
    vistas = {}
    for i, t in enumerate(tandas):
        for _, c in t.canciones.iterrows():
            ruta = c["ruta"]
            if carpeta and not _dentro_de(ruta, carpeta):
                avisos.append(Aviso(ERROR, f"{nombre(i)}: «{c['title']}» no está en {nombre_carpeta} "
                                           f"(no estará en el portátil): {ruta}", i))
            elif _en_nube(ruta):
                avisos.append(Aviso(AVISO, f"{nombre(i)}: «{c['title']}» está solo en la nube en este ordenador", i))
            clave = os.path.normcase(ruta)
            if clave in vistas and not t.es_cortina:
                avisos.append(Aviso(ERROR, f"{nombre(i)}: «{c['title']}» ya suena en {nombre(vistas[clave])}", i))
            vistas.setdefault(clave, i)

    # --- Estructura: cortina entre tandas, nada de cortinas dobles
    if tandas and tandas[0].es_cortina:
        avisos.append(Aviso(INFO, "La playlist empieza con una cortina", 0))
    for i, t in enumerate(tandas):
        siguiente = tandas[i + 1] if i + 1 < len(tandas) else None
        if not t.es_cortina and siguiente is not None and not siguiente.es_cortina:
            avisos.append(Aviso(ERROR, f"Falta una cortina entre la {nombre(i)} ({t.genero}) y la "
                                       f"{nombre(i + 1)} ({siguiente.genero})", i))
        if t.es_cortina:
            n = len(t.canciones)
            ultima = i == len(tandas) - 1
            if n > 1 and not ultima:
                avisos.append(Aviso(AVISO, f"{n} cortinas seguidas", i))
            elif n > 1 and ultima:
                avisos.append(Aviso(INFO, f"Acaba con {n} cortinas seguidas (¿de reserva?)", i))
            if "cortina" not in t.genero:
                avisos.append(Aviso(AVISO, f"«{t.canciones['title'].iloc[0]}» no tiene género de tango, vals ni "
                                           f"milonga: ¿es una cortina? (género: «{t.genero or 'vacío'}»)", i))

    # --- Cada tanda por dentro
    for i, t in reales:
        df = t.canciones
        bloques = _bloques_orquesta(df)
        if len(bloques) > 1 and all(n >= 2 for _, n in bloques):
            avisos.append(Aviso(ERROR, f"{nombre(i)}: parecen {len(bloques)} tandas sin cortina en medio ("
                                       + " · ".join(f"{o}, {n} temas" for o, n in bloques) + ")", i))
        elif not t.misma_orquesta:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: mezcla orquestas: "
                                       + ", ".join(dict.fromkeys(df["artist1"])), i))
        elif len(df) not in TEMAS_POR_TANDA:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: tiene {len(df)} temas", i))
        if not t.genero:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: sin género", i))

        cantores = [c.strip() for c in df["artist2"]]
        con_voz = [c for c in cantores if c]
        if con_voz and len(con_voz) < len(cantores):
            avisos.append(Aviso(AVISO, f"{nombre(i)}: mezcla instrumentales y cantadas", i))
        distintos = list(dict.fromkeys(con_voz))
        if len(distintos) > 1:
            comunes = set.intersection(*(_personas(c) for c in distintos))
            nivel = INFO if comunes else AVISO
            avisos.append(Aviso(nivel, f"{nombre(i)}: cantores distintos: " + " · ".join(distintos), i))

        anos = sorted(int(a) for a in df["ano"] if str(a).isdigit())
        if len(anos) < len(df):
            sin = [c["title"] for _, c in df.iterrows() if not str(c["ano"]).isdigit()]
            avisos.append(Aviso(AVISO, f"{nombre(i)}: sin año: " + ", ".join(sin), i))
        if anos and anos[-1] - anos[0] > MAX_ANOS_EN_TANDA:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: años muy separados ({anos[0]} – {anos[-1]})", i))

        titulos = [_titulo(x) for x in df["title"]]
        if len(set(titulos)) < len(titulos):
            avisos.append(Aviso(ERROR, f"{nombre(i)}: tiene un tema repetido", i))
        if not all(str(a).strip() for a in df["artist"]):
            avisos.append(Aviso(AVISO, f"{nombre(i)}: alguna canción sin artista", i))
        sin_compositor = [c["title"] for _, c in df.iterrows() if not compositor_para_diapo(c["composer"])]
        if sin_compositor:
            avisos.append(Aviso(INFO, f"{nombre(i)}: sin compositor en la diapo: " + ", ".join(sin_compositor), i))

    # --- Entre tandas
    generos = [(i, _genero_corto(t.genero)) for i, t in reales]
    for (i, g1), (j, g2) in zip(generos, generos[1:]):
        if g1 != "tango" and g2 != "tango":
            avisos.append(Aviso(AVISO, f"{nombre(i)} ({g1}) y {nombre(j)} ({g2}) seguidas, sin tango en medio", j))
    seguidos = 0
    for i, g in generos:
        seguidos = seguidos + 1 if g == "tango" else 0
        if seguidos == MAX_TANGOS_SEGUIDOS + 1:
            avisos.append(Aviso(INFO, f"{seguidos} tandas de tango seguidas hasta la {nombre(i)}", i))
    if generos and generos[0][1] != "tango":
        avisos.append(Aviso(INFO, f"Empieza con {generos[0][1]}", generos[0][0]))

    for n, (i, t) in enumerate(reales):
        for m in range(n + 1, min(n + DISTANCIA_ORQUESTA, len(reales))):
            j, u = reales[m]
            if t.orquesta and normalizar_nombre(t.orquesta) == normalizar_nombre(u.orquesta):
                avisos.append(Aviso(AVISO, f"{t.orquesta} en la {nombre(i)} y otra vez en la {nombre(j)}", j))
            comunes = set().union(*map(_personas, t.canciones["artist2"])) & \
                      set().union(*map(_personas, u.canciones["artist2"]))
            if comunes and not (t.orquesta and normalizar_nombre(t.orquesta) == normalizar_nombre(u.orquesta)):
                avisos.append(Aviso(AVISO, f"Cantor repetido muy cerca ({', '.join(sorted(comunes)).title()}): "
                                           f"{nombre(i)} y {nombre(j)}", j))

    vistos = {}
    for i, t in reales:
        for titulo, original in zip(map(_titulo, t.canciones["title"]), t.canciones["title"]):
            if titulo in vistos and vistos[titulo] != i:
                avisos.append(Aviso(AVISO, f"«{original}» suena dos veces: {nombre(vistos[titulo])} y {nombre(i)}", i))
            vistos.setdefault(titulo, i)

    if len(reales) >= 6:
        tercio = reales[:len(reales) // 3]
        for i, t in tercio:
            if "pugliese" in normalizar_nombre(t.orquesta):
                avisos.append(Aviso(INFO, f"Pugliese muy pronto ({nombre(i)}): mejor en el último tercio", i))
        instrumentales = sum(1 for _, t in reales if not any(c.strip() for c in t.canciones["artist2"]))
        if instrumentales * 3 < len(reales):
            avisos.append(Aviso(INFO, f"Pocas tandas instrumentales: {instrumentales} de {len(reales)}"))

    # --- Duración
    if inicio and fin:
        try:
            h1, h2 = datetime.strptime(inicio, "%H:%M"), datetime.strptime(fin, "%H:%M")
            if h2 <= h1:
                h2 += timedelta(days=1)
            disponible = (h2 - h1).total_seconds()
        except ValueError:
            disponible = None
        if disponible:
            musica = sum(t.duracion for _, t in reales)
            cortinas = sum(len(t.canciones) for t in tandas if t.es_cortina)
            total = musica + cortinas * SEGUNDOS_CORTINA
            diferencia = minutos(total - disponible)
            texto = f"Música {minutos(musica)} min + cortinas ≈ {minutos(total)} min, para {minutos(disponible)} min"
            if diferencia > 0:
                avisos.append(Aviso(AVISO, f"{texto}: sobran {diferencia} min"))
            else:
                avisos.append(Aviso(INFO, f"{texto}: quedan {-diferencia} min libres (charla, cumpleaños…)"))

    orden = {ERROR: 0, AVISO: 1, INFO: 2}
    return sorted(avisos, key=lambda a: (orden[a.nivel], a.fila if a.fila is not None else -1))
