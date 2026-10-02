"""Archivo → Estado de la colección: cómo está de ordenada cada carpeta de música."""
import os

import pandas as pd
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QFileDialog, QApplication, QMessageBox,
)

from src.config.config import dropbox_path
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
    "copias": "Archivos del mismo tamaño exacto dentro de la carpeta (usa Duplicados para comprobarlo)",
}


def raiz_musica():
    return QSettings("TangoTags", "TangoTags").value("raiz_musica", os.path.join(dropbox_path, "TDJ", "MUSICA"))


class VentanaEstado(QWidget):
    def __init__(self, parent, revisar_carpeta, abrir_duplicados):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Estado de la colección")
        self.resize(1300, 560)
        self.revisar_carpeta, self.abrir_duplicados = revisar_carpeta, abrir_duplicados
        self.df = pd.DataFrame()
        self._cancelar = False
        lay = QVBoxLayout(self)

        fila = QHBoxLayout()
        self.etiqueta_raiz = QLabel()
        cambiar = QPushButton("Cambiar carpeta…")
        cambiar.clicked.connect(self.cambiar_raiz)
        self.boton_actualizar = QPushButton("⟳  Actualizar")
        self.boton_actualizar.setToolTip("Vuelve a mirar la música. La primera vez tarda unos minutos; "
                                         "después solo lee lo que haya cambiado")
        self.boton_actualizar.clicked.connect(self.actualizar)
        duplicados = QPushButton("Buscar duplicados…")
        duplicados.clicked.connect(lambda: self.abrir_duplicados(self.colecciones_seleccionadas()))
        fila.addWidget(self.etiqueta_raiz, 1)
        fila.addWidget(cambiar)
        fila.addWidget(duplicados)
        fila.addWidget(self.boton_actualizar)
        lay.addLayout(fila)

        self.progreso = QProgressBar()
        self.progreso.hide()
        self.boton_cancelar = QPushButton("Cancelar")
        self.boton_cancelar.hide()
        self.boton_cancelar.clicked.connect(lambda: setattr(self, "_cancelar", True))
        fila2 = QHBoxLayout()
        fila2.addWidget(self.progreso, 1)
        fila2.addWidget(self.boton_cancelar)
        lay.addLayout(fila2)

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
        self.info = QLabel("Doble clic en una carpeta para revisarla en la ventana principal.")
        self.info.setStyleSheet("color:#666;")
        lay.addWidget(self.info)

        self.etiqueta_raiz.setText(f"Música: <b>{raiz_musica()}</b>")
        if os.path.exists(coleccion.CACHE):
            self.cargar_cache()

    def cambiar_raiz(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta de la música", raiz_musica())
        if carpeta:
            QSettings("TangoTags", "TangoTags").setValue("raiz_musica", carpeta)
            self.etiqueta_raiz.setText(f"Música: <b>{carpeta}</b>")

    def cargar_cache(self):
        df = pd.read_csv(coleccion.CACHE, sep=";", na_filter=False, dtype=str, encoding="utf-8")
        raiz = os.path.normcase(os.path.normpath(raiz_musica()))
        self.df = df[df["ruta"].map(lambda r: os.path.normcase(r).startswith(raiz))]
        self.pintar()
        self.info.setText("Datos de la última vez (pulsa Actualizar para volver a mirar). "
                          "Doble clic en una carpeta para revisarla.")

    def actualizar(self):
        self._cancelar = False
        self.progreso.show()
        self.boton_cancelar.show()
        self.boton_actualizar.setEnabled(False)

        def progreso(hechos, total, leidos):
            self.progreso.setMaximum(total)
            self.progreso.setValue(hechos)
            self.progreso.setFormat(f"%v de %m archivos  ({leidos} leídos del disco)")
            QApplication.processEvents()

        try:
            self.df = coleccion.escanear(raiz_musica(), progreso=progreso, cancelado=lambda: self._cancelar)
        finally:
            self.progreso.hide()
            self.boton_cancelar.hide()
            self.boton_actualizar.setEnabled(True)
        self.pintar()
        self.info.setText(("Cancelado: se muestra lo que dio tiempo a mirar. " if self._cancelar else "")
                          + "Doble clic en una carpeta para revisarla en la ventana principal.")

    def pintar(self):
        if self.df.empty:
            return
        r = coleccion.resumen(self.df, no_tocar.claves())
        tam = pd.to_numeric(self.df["bytes"], errors="coerce")
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
        carpeta = os.path.join(raiz_musica(), nombre)
        if QMessageBox.question(self, "Revisar carpeta",
                                f"¿Cargar «{nombre}» en la ventana principal para revisarla?") == QMessageBox.Yes:
            self.revisar_carpeta(carpeta)
