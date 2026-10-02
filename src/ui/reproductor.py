"""
Reproductor único de la app: una sola cosa suena a la vez, se sabe siempre qué es y se para
desde cualquier sitio. Las vistas escuchan la señal `cambiado(clave)` para pintar ■ en lo que suena.

pygame reproduce mp3, flac, wav, aiff y ogg. Para m4a/aac/wma (que pygame no sabe leer) el audio se
decodifica en memoria con PyAV (FFmpeg) y se reproduce como sonido de pygame.
"""
import os
import time

import pygame
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


FORMATOS_PYAV = {".m4a", ".mp4", ".aac", ".wma", ".alac"}


class Reproductor(QObject):
    cambiado = pyqtSignal(object)      # clave de lo que suena, o None si nada
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clave = None
        self.descripcion = ""
        self._canal = None          # si suena un sonido decodificado con PyAV
        self._inicio = 0.0
        self._vigilar = QTimer(self, interval=300, timeout=self._comprobar)

    def sonando(self, clave):
        return clave is not None and clave == self.clave

    def alternar(self, clave, ruta, descripcion):
        """Clic en ▶/■: si ya suena eso, para; si no, lo pone."""
        if self.sonando(clave):
            self.parar()
        else:
            self.reproducir(clave, ruta, descripcion)

    def reproducir(self, clave, ruta, descripcion):
        if not ruta or not os.path.exists(ruta):
            self.error.emit(f"No se encuentra el audio: {ruta}")
            return
        self.parar(avisar=False)
        try:
            if os.path.splitext(ruta)[1].lower() in FORMATOS_PYAV:
                self._reproducir_decodificado(ruta)
            else:
                try:
                    pygame.mixer.music.load(ruta)
                    pygame.mixer.music.play()
                except pygame.error:
                    self._reproducir_decodificado(ruta)     # formato raro: probar con FFmpeg
        except Exception as e:
            self.parar()
            self.error.emit(f"No se puede reproducir {os.path.basename(ruta)}: {e}")
            return
        self._inicio = time.monotonic()
        self.clave, self.descripcion = clave, descripcion
        self._vigilar.start()
        self.cambiado.emit(clave)

    def _reproducir_decodificado(self, ruta):
        """Decodifica el archivo entero a PCM con PyAV y lo reproduce en un canal de pygame."""
        import av
        frecuencia, _, canales = pygame.mixer.get_init()
        remuestreo = av.AudioResampler(format="s16", layout="stereo" if canales == 2 else "mono", rate=frecuencia)
        trozos = []
        with av.open(ruta) as contenedor:
            for frame in contenedor.decode(audio=0):
                trozos.extend(f.to_ndarray().tobytes() for f in remuestreo.resample(frame))
            trozos.extend(f.to_ndarray().tobytes() for f in remuestreo.resample(None))
        sonido = pygame.mixer.Sound(buffer=b"".join(trozos))
        self._canal = sonido.play()

    def parar(self, avisar=True):
        try:
            pygame.mixer.music.stop()
            if self._canal is not None:
                self._canal.stop()
        except Exception:
            pass
        self._canal = None
        self._vigilar.stop()
        if self.clave is not None and avisar:
            self.clave, self.descripcion = None, ""
            self.cambiado.emit(None)

    def segundos(self):
        return int(time.monotonic() - self._inicio) if self.clave is not None else 0

    def _comprobar(self):
        try:
            sigue = self._canal.get_busy() if self._canal is not None else pygame.mixer.music.get_busy()
        except Exception:
            sigue = False
        if not sigue:
            self.parar()                 # terminó solo: todo vuelve a ▶
        else:
            self.cambiado.emit(self.clave)   # para refrescar el contador


class BarraSonando(QFrame):
    """'♪ Sonando: …  0:42  [■ Parar]'. Solo visible mientras suena algo."""

    def __init__(self, reproductor, parent=None):
        super().__init__(parent)
        self.reproductor = reproductor
        self.setStyleSheet("BarraSonando{background:#e8f5e9; border:1px solid #81c784; border-radius:6px;}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 4, 2)
        self.texto = QLabel()
        self.texto.setStyleSheet("color:#1b5e20; font-weight:bold;")
        self.texto.setMaximumWidth(520)
        boton = QPushButton("■  Parar")
        boton.setToolTip("Parar la música (Esc)")
        boton.setStyleSheet("QPushButton{background:#2e7d32; color:white; font-weight:bold; padding:3px 14px;"
                            " border-radius:4px;} QPushButton:hover{background:#1b5e20;}")
        boton.clicked.connect(reproductor.parar)
        lay.addWidget(self.texto)
        lay.addWidget(boton)
        reproductor.cambiado.connect(self.actualizar)
        self.hide()

    def actualizar(self, clave):
        if clave is None:
            self.hide()
            return
        s = self.reproductor.segundos()
        texto = f"♪  {self.reproductor.descripcion}"
        metricas = self.texto.fontMetrics()
        texto = metricas.elidedText(texto, 1, self.texto.maximumWidth() - 60)   # 1 = Qt.ElideRight
        self.texto.setText(f"{texto}   {s // 60}:{s % 60:02d}")
        self.texto.setToolTip(self.reproductor.descripcion)
        self.show()
