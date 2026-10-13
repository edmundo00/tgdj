"""Pinchar: el programa para pinchar milongas (tandas, cortinas y fundidos), con la música en un proceso aparte.

Arrancar con:  python pinchar.py   (o doble clic en Pinchar.bat)
"""
import sys

from PyQt5.QtWidgets import QApplication

from src.pinchar.ventana import VentanaPinchar


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()     # el motor de sonido va en su propio proceso (también en el .exe)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = VentanaPinchar()
    ventana.showMaximized()
    sys.exit(app.exec_())
