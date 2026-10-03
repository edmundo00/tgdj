"""Archivo → Carpetas de la biblioteca: qué carpetas forman tu biblioteca (data/biblioteca.json)."""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFileDialog, QDialogButtonBox, QAbstractItemView,
)

from src.biblioteca.biblioteca import leer_config, guardar_config
from src.config.config import dropbox_path


class DialogoCarpetas(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Carpetas de la biblioteca")
        self.resize(900, 380)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "La biblioteca conoce toda la música de estas carpetas. Las rutas dentro de Dropbox se guardan "
            "relativas, así valen en todos tus ordenadores.<br>"
            "<b>Subcarpetas = colecciones</b>: cada subcarpeta es una colección (como MUSICA\\Eduardo, MUSICA\\Dan…); "
            "si no, toda la carpeta es una sola colección (como TIDAL Download).<br>"
            "<b>Excluir</b>: subcarpetas que no entran (separadas por comas)."))
        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["Carpeta", "Subcarpetas = colecciones", "Excluir subcarpetas"])
        self.tabla.verticalHeader().hide()
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        lay.addWidget(self.tabla)
        botones = QHBoxLayout()
        anadir = QPushButton("Añadir carpeta…")
        anadir.clicked.connect(self.anadir)
        quitar = QPushButton("Quitar")
        quitar.clicked.connect(self.quitar)
        botones.addWidget(anadir)
        botones.addWidget(quitar)
        botones.addStretch(1)
        caja = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        caja.button(QDialogButtonBox.Save).setText("Guardar")
        caja.button(QDialogButtonBox.Cancel).setText("Cancelar")
        caja.accepted.connect(self.guardar)
        caja.rejected.connect(self.reject)
        botones.addWidget(caja)
        lay.addLayout(botones)
        for r in leer_config()["raices"]:
            self.fila(r["ruta"], r.get("subcarpetas_son_colecciones", False), ", ".join(r.get("excluir", [])))

    def fila(self, ruta, subcarpetas, excluir):
        i = self.tabla.rowCount()
        self.tabla.insertRow(i)
        it = QTableWidgetItem(ruta)
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        it.setToolTip(os.path.join(dropbox_path, ruta) if not os.path.isabs(ruta) else ruta)
        self.tabla.setItem(i, 0, it)
        marca = QTableWidgetItem("")
        marca.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        marca.setCheckState(Qt.Checked if subcarpetas else Qt.Unchecked)
        self.tabla.setItem(i, 1, marca)
        self.tabla.setItem(i, 2, QTableWidgetItem(excluir))

    def anadir(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta con música", dropbox_path)
        if not carpeta:
            return
        carpeta = os.path.normpath(carpeta)
        base = os.path.normpath(dropbox_path)
        if carpeta.lower().startswith(base.lower() + os.sep):
            carpeta = os.path.relpath(carpeta, base).replace("\\", "/")
        self.fila(carpeta, False, "")

    def quitar(self):
        for i in sorted({x.row() for x in self.tabla.selectionModel().selectedRows()}, reverse=True):
            self.tabla.removeRow(i)

    def guardar(self):
        raices = []
        for i in range(self.tabla.rowCount()):
            excluir = [x.strip() for x in (self.tabla.item(i, 2).text() if self.tabla.item(i, 2) else "").split(",")]
            raices.append({"ruta": self.tabla.item(i, 0).text(),
                           "subcarpetas_son_colecciones": self.tabla.item(i, 1).checkState() == Qt.Checked,
                           "excluir": [x for x in excluir if x]})
        guardar_config({"raices": raices})
        self.accept()
