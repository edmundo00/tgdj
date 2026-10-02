"""
Búsqueda de la orquesta de un archivo en la base de datos.

Entiende las formas habituales de escribir el artista en las tags:
    "Juan D'Arienzo / Héctor Mauré"      (formato propio)
    "Juan D'Arienzo; Alberto Echagüe"    (varios artistas separados por ;)
    "Juan D'Arienzo feat. Héctor Mauré"
    "D'Arienzo, Juan"                    (apellido, nombre)
    "Orquesta Típica de Juan D'Arienzo"  (palabras de relleno)
y compara sin tener en cuenta mayúsculas, acentos ni apóstrofos.
"""
import re

from unidecode import unidecode

# Separa la orquesta del cantor (la orquesta es siempre lo primero)
SEPARADORES = re.compile(r"\s+/\s+|\s*;\s*|\s+feat\.?\s+|\s+ft\.?\s+|\s+canta:?\s+|\s+con\s+", re.IGNORECASE)

PALABRAS_RELLENO = {"orquesta", "orq", "tipica", "su", "la", "el", "los", "las", "de", "del", "y", "and"}

# Nivel de coincidencia (lo usa compare_tags para los colores)
EXACTA, NORMALIZADA, PARCIAL, NINGUNA = 3, 2, 1, 0


def separar_orquesta_cantor(artista):
    """'Orquesta / Cantor' (o con ; feat. canta: con) -> ('Orquesta', 'Cantor')."""
    if not isinstance(artista, str):
        return "", ""
    partes = SEPARADORES.split(artista.strip(), maxsplit=1)
    orquesta = partes[0].strip()
    cantor = partes[1].strip() if len(partes) > 1 else ""
    return orquesta, cantor


def normalizar_nombre(texto):
    """"Orquesta Típica de Juan D'Arienzo" -> 'juan darienzo'."""
    texto = unidecode(str(texto or "")).lower()
    texto = texto.replace("'", "").replace("`", "").replace("´", "")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    palabras = [p for p in texto.split() if p not in PALABRAS_RELLENO]
    return " ".join(palabras)


def variantes_orquesta(artista):
    """Posibles formas de la orquesta, de más a menos probable."""
    orquesta, _ = separar_orquesta_cantor(artista)
    variantes = [orquesta]
    if "," in orquesta:
        a, b = [p.strip() for p in orquesta.split(",", 1)]
        variantes += [f"{b} {a}", a, b]       # "D'Arienzo, Juan" -> "Juan D'Arienzo"
    return [v for i, v in enumerate(variantes) if v and v not in variantes[:i]]


class IndiceArtistas:
    def __init__(self, claves):
        self.claves = list(claves)
        self.normalizadas = {}
        for clave in self.claves:
            n = normalizar_nombre(clave)
            if n:
                self.normalizadas.setdefault(n, []).append(clave)

    def buscar(self, artista):
        """Devuelve (lista de claves de la BD, nivel) o (None, NINGUNA)."""
        variantes = variantes_orquesta(artista)

        # Exacta solo si la tag está escrita tal cual (no al darle la vuelta, por ejemplo)
        if variantes and variantes[0] in self.claves:
            return self.normalizadas.get(normalizar_nombre(variantes[0]), [variantes[0]]), EXACTA
        for v in variantes:
            n = normalizar_nombre(v)
            if n in self.normalizadas:
                return self.normalizadas[n], NORMALIZADA

        # Parcial: el nombre buscado aparece entero dentro de una clave, o al revés
        for v in variantes:
            n = normalizar_nombre(v)
            if not n:
                continue
            dentro = [k for nk, ks in self.normalizadas.items()
                      if re.search(rf"\b{re.escape(n)}\b", nk) for k in ks]
            contiene = [k for nk, ks in self.normalizadas.items()
                        if len(nk.split()) >= 2 and re.search(rf"\b{re.escape(nk)}\b", n) for k in ks]
            if dentro or contiene:
                return (contiene or dentro), PARCIAL

        # Por palabras: al menos dos palabras en común
        for v in variantes:
            palabras = set(normalizar_nombre(v).split())
            mejores, maximo = [], 1
            for nk, ks in self.normalizadas.items():
                comunes = len(palabras & set(nk.split()))
                if comunes > maximo:
                    mejores, maximo = list(ks), comunes
                elif comunes == maximo and maximo > 1:
                    mejores += ks
            if mejores:
                return mejores, PARCIAL

        return None, NINGUNA


_cache = {}


def indice_para(dic_art):
    """Índice cacheado para el diccionario de artistas de la base de datos."""
    clave = id(dic_art)
    if clave not in _cache:
        _cache.clear()
        _cache[clave] = IndiceArtistas(dic_art.keys())
    return _cache[clave]
