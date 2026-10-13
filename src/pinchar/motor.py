"""
El motor de sonido, en un PROCESO APARTE de la ventana: si la ventana se cuelga o va lenta, la música sigue.

    motor = Motor().arrancar()
    motor.orden("cargar", [ruta1, ruta2, …], 0)
    motor.orden("play") / ("fundido_siguiente",) / ("fundido_pausa",) / ("seguir",) / ("ir", 5) / ("buscar", 30.0)
    motor.situacion()        # lo último que ha contado el motor (dict), o None
    motor.parar()

Dentro del proceso:
- La tarjeta de sonido pide sonido cada pocos ms y el mezclador (mezclador.py) se lo da de lo que ya está en
  memoria: el tema que suena y los dos siguientes se leen enteros ANTES (un hilo aparte), así un disco lento o
  Dropbox no pueden cortar la música.
- Latencia alta a propósito (más margen = más difícil que se corte; para pinchar tango no hace falta rapidez).
"""
import multiprocessing as mp
import queue
import threading
import time
import traceback

import numpy as np

ADELANTE = 2                        # temas que se preparan por adelantado además del que suena


def decodificar(ruta, frecuencia):
    """El archivo entero, estéreo, a `frecuencia` Hz, como int16 (muestras, 2). Error si no se puede leer."""
    import av
    trozos = []
    with av.open(ruta) as contenedor:
        flujo = contenedor.streams.audio[0]
        conversor = av.AudioResampler(format="s16", layout="stereo", rate=frecuencia)
        for marco in contenedor.decode(flujo):
            for r in conversor.resample(marco):
                trozos.append(r.to_ndarray().reshape(-1, 2))
        for r in conversor.resample(None):
            trozos.append(r.to_ndarray().reshape(-1, 2))
    if not trozos:
        raise ValueError("sin sonido")
    return np.ascontiguousarray(np.concatenate(trozos), dtype=np.int16)


class Almacen:
    """Los temas ya leídos: el que suena y los ADELANTE siguientes (los demás se sueltan para no gastar memoria)."""

    def __init__(self, frecuencia, leer=decodificar):
        self.f, self.leer = frecuencia, leer
        self.rutas = []
        self.listos = {}             # índice -> array
        self.fallidos = {}           # índice -> motivo
        self.quiero = set()
        self._cambio = threading.Event()
        self._cerrar = False
        threading.Thread(target=self._trabajar, daemon=True, name="lector").start()

    def poner_rutas(self, rutas):
        self.rutas = list(rutas)
        self.listos, self.fallidos = {}, {}
        self._cambio.set()

    def audio(self, i):              # lo llama el mezclador: nunca espera
        if i in self.fallidos:
            return False
        return self.listos.get(i)

    def preparar(self, actual):
        quiero = {i for i in range(actual, actual + ADELANTE + 1) if 0 <= i < len(self.rutas)}
        if quiero != self.quiero:
            self.quiero = quiero
            self._cambio.set()

    def _trabajar(self):
        while not self._cerrar:
            self._cambio.wait(0.5)
            self._cambio.clear()
            for i in list(self.listos):
                if i not in self.quiero:
                    self.listos.pop(i, None)
            for i in sorted(self.quiero):                       # primero el que suena, luego los siguientes
                if i in self.listos or i in self.fallidos or i >= len(self.rutas):
                    continue
                ruta = self.rutas[i]
                try:
                    a = self.leer(ruta, self.f)
                except Exception as e:
                    if self.rutas[i:i + 1] == [ruta]:
                        self.fallidos[i] = f"{type(e).__name__}: {e}"
                    continue
                if self.rutas[i:i + 1] == [ruta] and i in self.quiero:   # no se ha cambiado la lista mientras
                    self.listos[i] = a

    def cerrar(self):
        self._cerrar = True
        self._cambio.set()


def _proceso(ordenes, estados, ajustes):
    """Lo que corre en el proceso del motor."""
    import sounddevice as sd
    from src.pinchar.mezclador import Mezclador

    def contar(**datos):
        try:
            estados.put_nowait(datos)
        except queue.Full:
            pass

    try:
        dispositivo = ajustes.get("dispositivo")
        info = sd.query_devices(dispositivo, "output")
        frecuencia = int(info["default_samplerate"])
        almacen = Almacen(frecuencia)
        mezclador = Mezclador(frecuencia, almacen.audio, ajustes.get("silencio", 2.0), ajustes.get("fundido", 3.0))
        cerrojo = threading.Lock()
        cortes = [0]

        def llamada(salida, frames, _tiempo, estado):
            if estado.output_underflow:
                cortes[0] += 1
            with cerrojo:
                salida[:] = mezclador.rellenar(frames)

        flujo = sd.OutputStream(samplerate=frecuencia, channels=2, dtype="float32", device=dispositivo,
                                latency="high", callback=llamada)
        flujo.start()
    except Exception:
        contar(error=traceback.format_exc())
        return

    nombre = info["name"]
    ultimo = 0.0
    while True:
        try:
            orden = ordenes.get(timeout=0.05)
        except queue.Empty:
            orden = None
        if orden:
            nombre_orden, args = orden[0], orden[1:]
            if nombre_orden == "salir":
                break
            with cerrojo:
                if nombre_orden == "cargar":
                    rutas, indice = args
                    almacen.poner_rutas(rutas)
                    mezclador.cargar(len(rutas), indice)
                    mezclador.saltadas.clear()
                elif nombre_orden == "ajustes":
                    for k, v in args[0].items():
                        setattr(mezclador, k, v)
                elif hasattr(mezclador, nombre_orden):
                    getattr(mezclador, nombre_orden)(*args)
        almacen.preparar(mezclador.indice)
        ahora = time.monotonic()
        if ahora - ultimo >= 0.1:
            ultimo = ahora
            with cerrojo:
                s = mezclador.situacion()
            s.update(listos=sorted(almacen.listos), fallidos=dict(almacen.fallidos), cortes=cortes[0],
                     dispositivo=nombre, activo=flujo.active, hora=time.time())
            contar(**s)
    flujo.stop()
    flujo.close()
    almacen.cerrar()


class Motor:
    """Lo que usa la ventana: lanza el proceso del motor y habla con él por colas."""

    def __init__(self, **ajustes):
        self.ajustes = ajustes
        self.proceso = None
        self._ultima = None

    def arrancar(self):
        ctx = mp.get_context("spawn")
        self.ordenes, self.estados = ctx.Queue(), ctx.Queue(maxsize=50)
        self.proceso = ctx.Process(target=_proceso, args=(self.ordenes, self.estados, self.ajustes),
                                   name="motor de sonido", daemon=False)
        self.proceso.start()
        return self

    def orden(self, *orden):
        self.ordenes.put(orden)

    def situacion(self):
        """Lo último que ha contado el motor (se vacía la cola y se queda lo más reciente)."""
        while True:
            try:
                self._ultima = self.estados.get_nowait()
            except queue.Empty:
                return self._ultima

    def vivo(self):
        return self.proceso is not None and self.proceso.is_alive()

    def parar(self, espera=3):
        if self.vivo():
            self.orden("salir")
            self.proceso.join(espera)
            if self.proceso.is_alive():
                self.proceso.terminate()
