"""
Velocidad (BPM) de las canciones, calculada del audio gastando poco.

Solo se leen SEGUNDOS del centro del tema, en mono y a FRECUENCIA Hz (con av, que ya usa el reproductor).
El pulso se busca con la autocorrelación del "flujo espectral" (dónde empiezan las notas). El resultado se
guarda (bpm.sqlite junto a la biblioteca) por ruta relativa a Dropbox + tamaño, para no repetirlo nunca.

En el tango el mismo tema puede medirse a la mitad o al doble; por eso el pulso se busca solo dentro del
RANGO de su género (cada rango abarca una octava: de x a 2x), y así las canciones de una tanda se comparan
en la misma escala.
"""
import os
import re
import sqlite3
import threading
from contextlib import contextmanager

import numpy as np

SEGUNDOS = 30
FRECUENCIA = 11025
VENTANA, SALTO = 512, 128
RANGOS = {"tango": (85, 170), "vals": (150, 300), "milonga": (70, 140)}
VERSION = 2                     # subirla si cambia el cálculo: se recalcula todo
# Actividad de las cortinas (se guarda en la misma caché con tipo "actividad"). Límites sacados de los tercios
# de las 145 cortinas de 5 estrellas de Edmundo (oct. 2026): Billie Eilish 3,8 … LISA «Rockstar» 22,3
ACTIVIDAD = "actividad"
CORTINA_TRANQUILA, CORTINA_ANIMADA = 8.3, 11.75
# Volumen (dB del centro del tema) y silencio al principio y al final (s): otros tipos en la misma caché
VOLUMEN, SILENCIO_INICIO, SILENCIO_FIN = "volumen", "silencio_inicio", "silencio_fin"
SEGUNDOS_BORDE = 12             # se miran 12 s del principio y del final
UMBRAL_SILENCIO = -45           # dB: por debajo es silencio (el soplido de los 78 queda por debajo)

_lock = threading.Lock()


def ruta_cache():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "TangoTags", "bpm.sqlite")


def _clave(ruta):
    """Ruta relativa a Dropbox (vale en el fijo y en el portátil) + tamaño."""
    m = re.search(r"[\\/]Dropbox[\\/]", ruta)
    relativa = ruta[m.end():] if m else ruta
    try:
        tamano = os.path.getsize(ruta)
    except OSError:
        tamano = -1
    return relativa.replace("/", "\\").lower(), tamano


def leer_trozo(ruta, segundos=SEGUNDOS, frecuencia=FRECUENCIA, donde="centro"):
    """Muestras mono float32 de `segundos` del tema: del "centro", del "principio" o del "final"."""
    import av
    with av.open(ruta) as contenedor:
        stream = contenedor.streams.audio[0]
        duracion = float(contenedor.duration or 0) / av.time_base
        inicio = {"centro": duracion / 2 - segundos / 2, "principio": 0.0, "final": duracion - segundos}[donde]
        inicio = max(0.0, inicio)
        if inicio > 1:
            contenedor.seek(int(inicio * av.time_base))
        remuestreo = av.AudioResampler(format="flt", layout="mono", rate=frecuencia)
        trozos, total, necesarias = [], 0, int(segundos * frecuencia)
        for frame in contenedor.decode(stream):
            for f in remuestreo.resample(frame):
                datos = f.to_ndarray().reshape(-1)
                trozos.append(datos)
                total += len(datos)
            if total >= necesarias:
                break
    return np.concatenate(trozos)[:necesarias] if trozos else np.zeros(0, dtype=np.float32)


def flujo_espectral(muestras, frecuencia=FRECUENCIA):
    """Dónde empiezan las notas: subida de energía por bandas, ~86 valores por segundo."""
    if len(muestras) < VENTANA * 4:
        return np.zeros(0), frecuencia / SALTO
    n = 1 + (len(muestras) - VENTANA) // SALTO
    marcos = np.lib.stride_tricks.as_strided(
        muestras, shape=(n, VENTANA), strides=(muestras.strides[0] * SALTO, muestras.strides[0]))
    espectro = np.abs(np.fft.rfft(marcos * np.hanning(VENTANA), axis=1))
    espectro = np.log1p(100 * espectro)
    flujo = np.maximum(np.diff(espectro, axis=0), 0).sum(axis=1)
    media = np.convolve(flujo, np.ones(16) / 16, mode="same")
    return np.maximum(flujo - media, 0), frecuencia / SALTO


def pulso(muestras, frecuencia=FRECUENCIA, minimo=50, maximo=240):
    """BPM con más fuerza entre minimo y maximo (sin ajustar al género), o None si no hay pulso claro."""
    flujo, fps = flujo_espectral(muestras, frecuencia)
    if len(flujo) < fps * 5 or not flujo.any():
        return None
    flujo = flujo - flujo.mean()
    ac = np.correlate(flujo, flujo, mode="full")[len(flujo) - 1:]
    ac /= ac[0] or 1
    bpms = np.arange(minimo, maximo + 0.25, 0.25)

    def valor(retardo):
        return np.interp(retardo, np.arange(len(ac)), ac, right=0)

    # cada candidato suma también sus múltiplos (un pulso de verdad se repite)
    retardos = fps * 60 / bpms
    puntos = valor(retardos) + 0.5 * valor(2 * retardos) + 0.25 * valor(4 * retardos)
    return float(bpms[int(np.argmax(puntos))])


def tipo(genero):
    if genero in (ACTIVIDAD, VOLUMEN, SILENCIO_INICIO, SILENCIO_FIN):
        return genero
    return "vals" if "vals" in (genero or "") else "milonga" if "milonga" in (genero or "") else "tango"


def actividad(muestras, frecuencia=FRECUENCIA):
    """Cuánto "se mueve" la música (media del flujo espectral): baja = tranquila, alta = animada."""
    flujo, _ = flujo_espectral(muestras, frecuencia)
    return round(float(flujo.mean()), 2) if len(flujo) else None


def calcular_actividad(ruta):
    try:
        return actividad(leer_trozo(ruta))
    except Exception:
        return None


def nivel(muestras):
    """Volumen medio (dB respecto al máximo digital): -10 fuerte, -20 flojo."""
    if not len(muestras):
        return None
    return round(float(20 * np.log10(np.sqrt(np.mean(muestras.astype(np.float64) ** 2)) + 1e-9)), 1)


def _segundos_de_silencio(muestras, frecuencia=FRECUENCIA, desde_el_final=False):
    """Segundos seguidos por debajo de UMBRAL_SILENCIO al principio (o al final) de las muestras."""
    paso = frecuencia // 20                                     # ventanas de 50 ms
    n = len(muestras) // paso
    if not n:
        return 0.0
    ventanas = muestras[:n * paso].astype(np.float64).reshape(n, paso)
    niveles = 20 * np.log10(np.sqrt((ventanas ** 2).mean(axis=1)) + 1e-9)
    sonido = np.where(niveles > UMBRAL_SILENCIO)[0]
    if not len(sonido):
        return round(n * 0.05, 2)
    return round((n - 1 - sonido[-1]) * 0.05 if desde_el_final else sonido[0] * 0.05, 2)


def silencios(ruta):
    """(segundos de silencio al principio, al final)."""
    try:
        inicio = _segundos_de_silencio(leer_trozo(ruta, SEGUNDOS_BORDE, donde="principio"))
        fin = _segundos_de_silencio(leer_trozo(ruta, SEGUNDOS_BORDE, donde="final"), desde_el_final=True)
        return inicio, fin
    except Exception:
        return None, None


def calcular(ruta, genero="tango"):
    """BPM del tema dentro del rango de su género, o None."""
    bajo, alto = RANGOS[tipo(genero)]
    try:
        valor = pulso(leer_trozo(ruta), minimo=bajo, maximo=alto - 0.25)
    except Exception:
        return None
    return round(valor) if valor else None


class CacheBpm:
    """Los BPM ya calculados, por archivo y género."""

    def __init__(self, ruta=None):
        self.ruta = ruta or ruta_cache()
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        with self._conectar() as con:
            con.execute("CREATE TABLE IF NOT EXISTS bpm (clave TEXT, bytes INTEGER, tipo TEXT, version INTEGER, "
                        "bpm REAL, PRIMARY KEY (clave, bytes, tipo))")

    @contextmanager
    def _conectar(self):
        con = sqlite3.connect(self.ruta, timeout=10)
        try:
            with con:
                yield con
        finally:
            con.close()

    def guardado(self, ruta, genero="tango"):
        """(encontrado, bpm o None)"""
        clave, tamano = _clave(ruta)
        with _lock, self._conectar() as con:
            fila = con.execute("SELECT bpm FROM bpm WHERE clave=? AND bytes=? AND tipo=? AND version=?",
                               (clave, tamano, tipo(genero), VERSION)).fetchone()
        return (True, fila[0]) if fila else (False, None)

    def guardar(self, ruta, genero, valor):
        clave, tamano = _clave(ruta)
        with _lock, self._conectar() as con:
            con.execute("INSERT OR REPLACE INTO bpm VALUES (?,?,?,?,?)", (clave, tamano, tipo(genero), VERSION, valor))

    def bpm(self, ruta, genero="tango", calcular_si_falta=True):
        encontrado, valor = self.guardado(ruta, genero)
        if not encontrado and calcular_si_falta:
            valor = calcular(ruta, genero)
            self.guardar(ruta, genero, valor)
        return valor

    def actividad(self, ruta, calcular_si_falta=True):
        encontrado, valor = self.guardado(ruta, ACTIVIDAD)
        if not encontrado and calcular_si_falta:
            valor = calcular_actividad(ruta)
            self.guardar(ruta, ACTIVIDAD, valor)
        return valor

    def medidas(self, ruta, genero="tango", es_cortina=False, calcular_si_falta=True):
        """
        Todo lo que hace falta de una canción, leyendo el audio solo si falta algo (y una vez para todo):
        tandas: {"bpm", "volumen", "silencio_inicio", "silencio_fin"}; cortinas: {"actividad", "volumen"}.
        """
        tipos = [ACTIVIDAD, VOLUMEN] if es_cortina else [genero, VOLUMEN, SILENCIO_INICIO, SILENCIO_FIN]
        nombres = ["actividad", "volumen"] if es_cortina else ["bpm", "volumen", "silencio_inicio", "silencio_fin"]
        guardados = [self.guardado(ruta, t) for t in tipos]
        valores = [v for _, v in guardados]
        if calcular_si_falta and not all(e for e, _ in guardados):
            centro = None
            if not (guardados[0][0] and guardados[1][0]):
                try:
                    centro = leer_trozo(ruta)
                except Exception:
                    centro = np.zeros(0, dtype=np.float32)
            for n, (tipo_, (encontrado, _)) in enumerate(zip(tipos, guardados)):
                if encontrado:
                    continue
                if tipo_ == ACTIVIDAD:
                    valor = actividad(centro)
                elif tipo_ == VOLUMEN:
                    valor = nivel(centro)
                elif tipo_ == SILENCIO_INICIO:
                    valor, valores[3] = silencios(ruta)
                    self.guardar(ruta, SILENCIO_FIN, valores[3])
                    guardados[3] = (True, valores[3])
                elif tipo_ == SILENCIO_FIN:
                    valor = silencios(ruta)[1]
                else:
                    bajo, alto = RANGOS[tipo(genero)]
                    bruto = pulso(centro, minimo=bajo, maximo=alto - 0.25) if len(centro) else None
                    valor = round(bruto) if bruto else None
                self.guardar(ruta, tipo_, valor)
                valores[n] = valor
        return dict(zip(nombres, valores))
