import gc
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication, QTableWidget

from src.ui.columnas import preparar_columnas

app = QApplication.instance() or QApplication([])


class ColumnasTest(unittest.TestCase):
    def tearDown(self):
        QSettings("TangoTags", "TangoTags").remove("columnas/test_columnas")

    def test_cambiar_ancho_tras_recolectar_basura(self):
        # Python 3.13 + PyQt5: si las funciones conectadas se liberan, esto tumba la app (access violation)
        tabla = QTableWidget(3, 4)
        preparar_columnas(tabla, "test_columnas", {})
        gc.collect()
        tabla.setColumnWidth(1, 200)
        tabla.setColumnHidden(2, True)
        app.processEvents()
        self.assertTrue(tabla.isColumnHidden(2))


if __name__ == "__main__":
    unittest.main()
