"""Archivo → Grafías de nombres…: elegir cómo se escribe cada orquesta/cantor."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QDialogButtonBox, QCheckBox,
)

from src.utils import grafias



def contar_nombres(extra=None):
    """{grafía: nº de archivos} de tu colección (la calcula la ventana principal desde la biblioteca)."""
    return dict(extra or {})


class DialogoGrafias(QDialog):
    def __init__(self, parent, nombres_bd, extra=None):
        super().__init__(parent)
        self.setWindowTitle("Grafías de nombres")
        self.resize(1100, 700)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Orquestas y cantores que se escriben distinto en tu colección y en la base de datos. "
            "Elige cómo quieres que se escriban: es lo que se pondrá en las tags.<br>"
            "Por defecto, la forma que más usas en tu colección (así no se cambia lo que ya tienes)."))
        fila = QHBoxLayout()
        self.filtro = QLineEdit()
        self.filtro.setPlaceholderText("Filtrar por nombre…")
        self.filtro.textChanged.connect(self.filtrar)
        self.solo_dudas = QCheckBox("Solo donde tu colección tiene varias formas o difiere de la BD")
        self.solo_dudas.setChecked(True)
        self.solo_dudas.toggled.connect(self.filtrar)
        fila.addWidget(self.filtro, 1)
        fila.addWidget(self.solo_dudas)
        lay.addLayout(fila)

        self.datos = grafias.diferencias(contar_nombres(extra), nombres_bd).reset_index(drop=True)
        self.tabla = QTableWidget(len(self.datos), 3)
        self.tabla.setHorizontalHeaderLabels(["En tu colección (nº de archivos)", "En la base de datos", "Escribir como"])
        self.tabla.verticalHeader().hide()
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        self.combos = []
        for i, f in self.datos.iterrows():
            variantes = sorted(f["grafias_coleccion"].items(), key=lambda x: -x[1])
            texto = "   ·   ".join(f"{g} ({k})" for g, k in variantes)
            self.tabla.setItem(i, 0, QTableWidgetItem(texto))
            bd = QTableWidgetItem(f["grafia_bd"])
            bd.setForeground(QColor("#666"))
            self.tabla.setItem(i, 1, bd)
            combo = QComboBox()
            combo.setEditable(True)        # también se puede escribir otra forma
            opciones = [g for g, _ in variantes] + ([f["grafia_bd"]] if f["grafia_bd"] not in f["grafias_coleccion"] else [])
            combo.addItems(opciones)
            combo.setCurrentText(f["elegida"])
            self.tabla.setCellWidget(i, 2, combo)
            self.combos.append(combo)
        lay.addWidget(self.tabla)

        self.info = QLabel()
        lay.addWidget(self.info)
        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Save).setText("Guardar grafías")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botones.accepted.connect(self.guardar)
        botones.rejected.connect(self.reject)
        lay.addWidget(botones)
        self.filtrar()

    def filtrar(self):
        texto = self.filtro.text().strip().lower()
        visibles = 0
        for i, f in self.datos.iterrows():
            dudosa = len(f["grafias_coleccion"]) > 1 or f["grafia_bd"] not in f["grafias_coleccion"]
            ver = (not texto or texto in self.tabla.item(i, 0).text().lower()) and (dudosa or not self.solo_dudas.isChecked())
            self.tabla.setRowHidden(i, not ver)
            visibles += ver
        self.info.setText(f"{visibles} nombres")

    def guardar(self):
        actuales = grafias.leer()
        for i, combo in enumerate(self.combos):
            actuales[self.datos.iloc[i]["normalizado"]] = combo.currentText().strip()
        grafias.guardar(actuales.values())
        self.accept()
