"""
Reglas únicas de formato para las tags de tango.

Todo lo que se escribe en un archivo pasa por aquí, para que siempre quede igual:

    Título     -> tal cual la base de datos, sin espacios sobrantes
    Artista    -> "Orquesta / Cantor"  (varios cantores: "A y B", "A, B y C")
    Fecha      -> "YYYY-MM-DD"  (o "YYYY-MM" / "YYYY" si solo se sabe eso)
    Género     -> en minúsculas: "tango", "tango vals", "tango milonga"...
    Compositor -> "Musica: X - Letra: Y"  (siempre; "?" en lo que no se sepa)

Si un dato no se conoce (vacío, "?", "-", "Desconocido"...) se devuelve "" y
update_tags no toca esa tag del archivo. Excepción: el compositor siempre se
escribe, y "Musica: ? - Letra: ?" sirve de marca de que pasó por la base de datos.
"""
import re
from datetime import datetime

SEPARADOR_ARTISTA = " / "

_DESCONOCIDOS = {"", "?", "-", "desconocido", "unknown", "nan", "none"}

_ESTILOS_EQUIVALENTES = {
    "foxtrot": "fox trot",
    "vals": "tango vals",
    "milonga": "tango milonga",
}


def _limpio(valor):
    """Devuelve el texto sin espacios sobrantes, o "" si es un valor desconocido."""
    if valor is None:
        return ""
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    return "" if texto.lower() in _DESCONOCIDOS else texto


def formatear_titulo(titulo):
    return _limpio(titulo)


def formatear_cantores(cantor):
    """'A,B' / 'A, B' / 'A y B' -> 'A y B'; tres o más -> 'A, B y C'."""
    texto = _limpio(cantor)
    if not texto:
        return ""
    partes = [p for p in (_limpio(x) for x in re.split(r",| y ", texto)) if p]
    if len(partes) <= 1:
        return partes[0] if partes else ""
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def formatear_artista(orquesta, cantor=""):
    """'Orquesta / Cantor', o solo 'Orquesta' si es instrumental."""
    orquesta = _limpio(orquesta)
    cantores = formatear_cantores(cantor)
    if orquesta and cantores:
        return f"{orquesta}{SEPARADOR_ARTISTA}{cantores}"
    return orquesta or cantores


def formatear_fecha(fecha):
    """
    Normaliza la fecha de grabación a YYYY-MM-DD.
    Acepta YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, YYYYMMDD, YYYY-MM y YYYY.
    Los rangos ('1930--1941') o fechas inválidas devuelven "".
    """
    texto = _limpio(fecha)
    if not texto:
        return ""

    # Quitar partes a cero: 1941-00-00 -> 1941, 1941-03-00 -> 1941-03
    texto = re.sub(r"(-00)+$", "", texto)

    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.fullmatch(r"(\d{4})-(\d{1,2})", texto)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    if re.fullmatch(r"\d{4}", texto):
        return texto

    return ""


def formatear_estilo(estilo):
    texto = _limpio(estilo).lower()
    return _ESTILOS_EQUIVALENTES.get(texto, texto)


def formatear_compositor(compositor="", letrista=""):
    """
    Siempre 'Musica: X - Letra: Y', con '?' en lo que no se sepa.
    Así 'Musica: ? - Letra: ?' indica que la canción ya pasó por la base de datos.
    """
    return f"Musica: {_limpio(compositor) or '?'} - Letra: {_limpio(letrista) or '?'}"


def separar_compositor_autor(texto):
    """'Musica: X - Letra: Y' -> ('X', 'Y'). Texto sin ese formato se toma como compositor."""
    texto = _limpio(texto)
    if not texto:
        return "", ""
    m = re.fullmatch(r"(?:Musica:\s*(.*?))?\s*(?:-?\s*Letra:\s*(.*))?", texto, flags=re.IGNORECASE)
    if m and (m.group(1) is not None or m.group(2) is not None):
        return _limpio(m.group(1)), _limpio(m.group(2))
    return texto, ""


def normalizar_compositor_autor(texto):
    return formatear_compositor(*separar_compositor_autor(texto))


def combinar_compositor(del_archivo, de_la_bd):
    """
    Compositor final sin perder información: lo que la base de datos no sabe ('?') se toma del
    archivo. 'Richard Russo' + 'Musica: ? - Letra: ?' -> 'Musica: Richard Russo - Letra: ?'.
    """
    musica_a, letra_a = separar_compositor_autor(del_archivo)
    musica_b, letra_b = separar_compositor_autor(de_la_bd)
    return formatear_compositor(musica_b or musica_a, letra_b or letra_a)


def tags_desde_coincidencia(coincidencia):
    """
    Construye las tags finales a partir de una fila de la base de datos
    (dict o pandas Series con titulo, artista, cantor, fecha, estilo, compositor_autor).
    """
    get = (lambda k: coincidencia.get(k, "")) if hasattr(coincidencia, "get") else (lambda k: "")
    return {
        "title": formatear_titulo(get("titulo")),
        "artist": formatear_artista(get("artista"), get("cantor")),
        "year": formatear_fecha(get("fecha")),
        "genre": formatear_estilo(get("estilo")),
        "composer": normalizar_compositor_autor(get("compositor_autor")),
    }
