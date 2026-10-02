"""Abre solo la ventana de crear diapos (también está en TangoTags → Crear diapos)."""
import sys

from PyQt5.QtWidgets import QApplication

from src.ui.ventana_diapos import VentanaDiapos

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = VentanaDiapos()
    ventana.show()
    sys.exit(app.exec_())
