"""Leer las playlists de MusicBee (.mbp), que son binarias."""
import re

EXTENSIONES = ('.flac', '.mp3', '.m4a', '.wav', '.aiff', '.aif', '.ogg', '.wma', '.ape', '.opus')


def leer_mbp(ruta):
    """
    Rutas de las canciones de una playlist .mbp, en orden.
    Cada ruta va guardada como longitud (entero de 7 bits por byte, el bit alto dice "sigue") + texto UTF-8;
    se buscan las unidades ("D:\\") y se comprueba la longitud que llevan delante.
    """
    from src.config.config import ruta_local
    with open(ruta, 'rb') as f:
        datos = f.read()
    rutas = []
    for m in re.finditer(rb'[A-Za-z]:\x5c', datos):
        i = m.start()
        for n_bytes in (1, 2, 3):
            if i - n_bytes < 0:
                break
            prefijo = datos[i - n_bytes:i]
            if prefijo[-1] & 0x80 or not all(b & 0x80 for b in prefijo[:-1]):
                continue
            longitud = sum((b & 0x7f) << (7 * k) for k, b in enumerate(prefijo))
            texto = datos[i:i + longitud].decode('utf-8', 'replace')
            if texto.lower().endswith(EXTENSIONES):
                rutas.append(ruta_local(texto))
                break
    return rutas
