"""TangoTags: poner bien las tags de tango y crear las diapos de las tandas.

Arrancar con:  python tangotags.py   (o doble clic en TangoTags.bat)
"""
import sys
import threading

import pygame
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap, QColor

from src.config.config import DB_CSV_PATH
from src.config.database import Database
from src.ui.tango_tags_qt_ventana import tango_tags_qt_ventana


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()     # necesario para los procesos aparte de la biblioteca en el .exe
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    fondo = QPixmap(420, 120)
    fondo.fill(QColor("#263238"))
    splash = QSplashScreen(fondo)
    splash.showMessage("TangoTags\n\nCargando base de datos…", Qt.AlignCenter, QColor("white"))
    splash.show()
    app.processEvents()

    Database().load_data(DB_CSV_PATH)
    pygame.mixer.init()

    ventana = tango_tags_qt_ventana()
    ventana.showMaximized()
    splash.finish(ventana)

    # Preparar el índice del buscador en segundo plano, para que "Buscar en BD" abra al instante
    threading.Thread(target=Database().get_indice_busqueda, daemon=True).start()
    # Y la biblioteca (toda tu música) se pone al día, también en segundo plano
    ventana.iniciar_biblioteca()
    sys.exit(app.exec_())
