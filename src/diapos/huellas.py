"""
Huellas de audio para reconocer qué canción suena (y en qué segundo va), al estilo de Shazam.

    huella = huella_de(muestras)                 # [(código, instante), …] de una canción entera
    indice = Indice(); indice.añadir(n, huella)  # todas las canciones de la noche
    n, segundo, votos = indice.buscar(huella_de(trozo_del_microfono))

Cómo funciona:
1. Espectrograma (qué frecuencias suenan en cada instante), a FRECUENCIA Hz y en ventanas de SALTO muestras.
2. Picos: los puntos más fuertes de su entorno (las notas que destacan); el ruido de fondo no llega a pico.
3. Parejas de picos cercanos -> código (frecuencia 1, frecuencia 2, distancia en tiempo) + instante del primero.
4. Para reconocer: los códigos del trozo que coinciden con los de una canción y con el MISMO desfase de tiempo
   votan por esa canción y ese punto. La que más votos tiene es la que suena; el desfase dice en qué segundo va.
"""
import numpy as np

FRECUENCIA = 8000           # Hz (de sobra para reconocer; el audio se lee ya remuestreado)
VENTANA = 1024              # muestras (128 ms)
SALTO = 256                 # muestras (32 ms entre columnas del espectrograma)
VECINDAD_F, VECINDAD_T = 15, 15     # un pico es el máximo en ±15 bandas y ±15 columnas
PICOS_POR_SEGUNDO = 25
PAREJAS = 6                 # con cuántos picos siguientes se empareja cada uno
DT_MIN, DT_MAX = 1, 64      # distancia en columnas entre los picos de una pareja (hasta ~2 s)
BANDA_MIN, BANDA_MAX = 6, 480       # ~50 Hz … ~3,75 kHz


def segundos_por_columna():
    return SALTO / FRECUENCIA


def espectrograma(muestras):
    """Magnitud en dB: filas = bandas de frecuencia, columnas = tiempo."""
    muestras = np.asarray(muestras, dtype=np.float32)
    if len(muestras) < VENTANA:
        return np.zeros((VENTANA // 2 + 1, 0), dtype=np.float32)
    n = 1 + (len(muestras) - VENTANA) // SALTO
    marcos = np.lib.stride_tricks.as_strided(
        muestras, shape=(n, VENTANA), strides=(muestras.strides[0] * SALTO, muestras.strides[0]))
    espectro = np.abs(np.fft.rfft(marcos * np.hanning(VENTANA).astype(np.float32), axis=1)).T
    return 20 * np.log10(espectro + 1e-6)


def _maximo_movil(m, radio, eje):
    """Máximo en una ventana de ±radio a lo largo de un eje (sin scipy)."""
    relleno = [(0, 0), (0, 0)]
    relleno[eje] = (radio, radio)
    m = np.pad(m, relleno, mode="constant", constant_values=-np.inf)
    v = np.lib.stride_tricks.sliding_window_view(m, 2 * radio + 1, axis=eje)
    return v.max(axis=-1)


def picos(espec):
    """[(columna, banda)] de los picos, ordenados por tiempo (como mucho PICOS_POR_SEGUNDO)."""
    if espec.shape[1] == 0:
        return []
    zona = espec[BANDA_MIN:BANDA_MAX]
    maximos = _maximo_movil(_maximo_movil(zona, VECINDAD_F, 0), VECINDAD_T, 1)
    umbral = np.median(zona) + 10                      # por encima del fondo
    bandas, columnas = np.nonzero((zona == maximos) & (zona > umbral))
    if not len(columnas):
        return []
    fuerza = zona[bandas, columnas]
    # como mucho PICOS_POR_SEGUNDO de media: los más fuertes
    maximo = max(1, int(espec.shape[1] * segundos_por_columna() * PICOS_POR_SEGUNDO))
    if len(fuerza) > maximo:
        elegidos = np.argpartition(-fuerza, maximo)[:maximo]
        bandas, columnas = bandas[elegidos], columnas[elegidos]
    orden = np.lexsort((bandas, columnas))
    return list(zip(columnas[orden].tolist(), (bandas[orden] + BANDA_MIN).tolist()))


def huella_de(muestras):
    """[(código, columna)] de unas muestras mono a FRECUENCIA Hz. Código = f1 (9 bits) · f2 (9 bits) · dt (6 bits)."""
    p = picos(espectrograma(muestras))
    salida = []
    for i, (t1, f1) in enumerate(p):
        emparejados = 0
        for t2, f2 in p[i + 1:]:
            dt = t2 - t1
            if dt < DT_MIN:
                continue
            if dt > DT_MAX or emparejados >= PAREJAS:
                break
            salida.append(((f1 & 511) << 15 | (f2 & 511) << 6 | (dt & 63), t1))
            emparejados += 1
    return salida


class Indice:
    """Las huellas de todas las canciones: código -> [(canción, columna)]."""

    def __init__(self):
        self.codigos = {}

    def añadir(self, cancion, huella):
        for codigo, t in huella:
            self.codigos.setdefault(codigo, []).append((cancion, t))

    def buscar(self, huella, candidatas=None):
        """(canción, segundo en que va AL FINAL del trozo, votos) o (None, None, 0).
        candidatas: si se da, solo se miran esas canciones."""
        votos = {}
        ultimo = max((t for _, t in huella), default=0)
        for codigo, t_trozo in huella:
            for cancion, t_cancion in self.codigos.get(codigo, ()):
                if candidatas is not None and cancion not in candidatas:
                    continue
                clave = (cancion, t_cancion - t_trozo)
                votos[clave] = votos.get(clave, 0) + 1
        if not votos:
            return None, None, 0
        # el desfase puede bailar una columna: se suman los vecinos
        mejores = {}
        for (cancion, desfase), v in votos.items():
            total = v + votos.get((cancion, desfase - 1), 0) + votos.get((cancion, desfase + 1), 0)
            if total > mejores.get(cancion, (0, 0))[0]:
                mejores[cancion] = (total, desfase)
        cancion, (total, desfase) = max(mejores.items(), key=lambda x: x[1][0])
        return cancion, (desfase + ultimo) * segundos_por_columna(), total
