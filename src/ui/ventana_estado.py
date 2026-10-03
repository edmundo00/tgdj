"""Archivo → Estado de la colección: cómo está de ordenada cada colección (datos de la biblioteca)."""
import os

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox,
)

from src.biblioteca.biblioteca import raices_absolutas
from src.utils import coleccion, no_tocar

COLUMNAS = [
    ("archivos", "Archivos", "n"), ("gb", "GB", "gb"),
    ("revisadas", "Revisadas", "%bueno"), ("fecha_completa", "Fecha completa", "%bueno"),
    ("fecha_cd", "Fecha de CD", "%malo"), ("sin_fecha", "Sin fecha", "%malo"),
    ("artista_raro", "Artista en otro formato", "%malo"), ("sin_genero", "Sin género", "%malo"),
    ("no_tocar", "No tocar", "n"), ("copias", "Posibles copias", "n"),
]
AYUDA = {
    "revisadas": "Ya pasaron por la base de datos (compositor «Musica: … - Letra: …»)",
    "fecha_completa": "Fecha de grabación AAAA-MM-DD",
    "fecha_cd": "Año 1990 o posterior: casi seguro es la fecha del CD, no la de grabación",
    "artista_raro": "Artista con ; , - o feat en vez de «Orquesta / Cantor»",
    "copias": "Archivos del mismo tamaño exacto dentro de la colección (usa Duplicados para comprobarlo)",
}


class VentanaEstado(QWidget):
    def __init__(self, parent, biblioteca, actualizar, revisar_coleccion, abrir_duplicados, editar_carpetas):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Estado de la colección")
        self.resize(1300, 560)
        self.biblioteca = biblioteca
        self.revisar_coleccion, self.abrir_duplicados = revisar_coleccion, abrir_duplicados
        self.df = pd.DataFrame()
        lay = QVBoxLayout(self)

        fila = QHBoxLayout()
        self.etiqueta_raices = QLabel()
        self.etiqueta_raices.setWordWrap(True)
        carpetas = QPushButton("Carpetas…")
        carpetas.setToolTip("Qué carpetas forman tu biblioteca")
        carpetas.clicked.connect(editar_carpetas)
        duplicados = QPushButton("Buscar duplicados…")
        duplicados.clicked.connect(lambda: self.abrir_duplicados(self.colecciones_seleccionadas()))
        self.boton_actualizar = QPushButton("⟳  Actualizar")
        self.boton_actualizar.setToolTip("Buscar cambios en la música (en segundo plano; solo lee lo nuevo o cambiado)")
        self.boton_actualizar.clicked.connect(actualizar)
        fila.addWidget(self.etiqueta_raices, 1)
        fila.addWidget(carpetas)
        fila.addWidget(duplicados)
        fila.addWidget(self.boton_actualizar)
        lay.addLayout(fila)

        self.tabla = QTableWidget(0, len(COLUMNAS) + 1)
        self.tabla.setHorizontalHeaderLabels(["Colección"] + [n for _, n, _ in COLUMNAS])
        for i, (clave, _, _) in enumerate(COLUMNAS, 1):
            if clave in AYUDA:
                self.tabla.horizontalHeaderItem(i).setToolTip(AYUDA[clave])
        self.tabla.verticalHeader().hide()
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla.cellDoubleClicked.connect(self.doble_clic)
        lay.addWidget(self.tabla, 1)
        self.info = QLabel()
        self.info.setStyleSheet("color:#666;")
        lay.addWidget(self.info)
        self.cargar()

    def cargar(self):
        """Vuelve a leer la biblioteca y repinta (rápido: es una consulta)."""
        raices = [r for r, _, _ in raices_absolutas(self.biblioteca.config)]
        self.etiqueta_raices.setText("Biblioteca: " + " · ".join(f"<b>{r}</b>" for r in raices))
        self.df = self.biblioteca.dataframe()
        self.pintar()
        actualizando = " (buscando cambios…)" if self.biblioteca.actualizando() else ""
        self.info.setText(f"{len(self.df):,} canciones{actualizando}. ".replace(",", ".")
                          + "Doble clic en una colección para revisarla en la ventana principal.")

    def pintar(self):
        self.tabla.setRowCount(0)
        if self.df.empty:
            return
        r = coleccion.resumen(self.df, no_tocar.claves())
        tam = self.df["bytes"]
        copias = self.df[tam.duplicated(keep=False) & (tam > 100_000)].groupby(["coleccion", "bytes"]).size()
        copias = (copias - 1).groupby(level=0).sum()
        r["copias"] = copias.reindex(r.index).fillna(0)
        r.loc["TOTAL", "copias"] = r.drop(index="TOTAL")["copias"].sum()
        self.tabla.setRowCount(len(r))
        for i, (nombre, f) in enumerate(r.iterrows()):
            total = f["archivos"] or 1
            it = QTableWidgetItem(str(nombre))
            if nombre == "TOTAL":
                it.setFont(QFont("", -1, QFont.Bold))
            self.tabla.setItem(i, 0, it)
            for j, (clave, _, tipo) in enumerate(COLUMNAS, 1):
                v = f[clave]
                if tipo == "gb":
                    texto = f"{v:.1f}"
                elif tipo.startswith("%"):
                    texto = f"{100 * v / total:.0f}%  ({int(v)})"
                else:
                    texto = f"{int(v):,}".replace(",", ".")
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if tipo.startswith("%"):
                    p = v / total
                    bueno = p if tipo == "%bueno" else 1 - p
                    celda.setBackground(QColor.fromHsv(int(120 * bueno), 70, 250))   # rojo -> verde
                if nombre == "TOTAL":
                    celda.setFont(QFont("", -1, QFont.Bold))
                self.tabla.setItem(i, j, celda)

    def colecciones_seleccionadas(self):
        filas = {i.row() for i in self.tabla.selectionModel().selectedRows()}
        nombres = [self.tabla.item(f, 0).text() for f in filas if self.tabla.item(f, 0)]
        return [n for n in nombres if n != "TOTAL"]

    def doble_clic(self, fila, _):
        nombre = self.tabla.item(fila, 0).text()
        if nombre == "TOTAL":
            return
        if QMessageBox.question(self, "Revisar colección",
                                f"¿Cargar «{nombre}» en la ventana principal para revisarla?") == QMessageBox.Yes:
            self.revisar_coleccion(nombre)
