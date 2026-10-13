"""Ventana para elegir un cambio propuesto (tema, tanda o cortina): se puede escuchar antes de usarlo."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton, QCheckBox,
)


class DialogoPropuesta(QDialog):
    """
    obtener(solo_5) -> (columnas, filas, rutas): filas = listas de textos; rutas = por fila, la lista de archivos
    que se escuchan con ▶ (en una tanda, ▶ va pasando por sus temas).
    Tras exec_(): self.elegida = índice de la fila elegida (o None).
    """

    def __init__(self, parent, titulo, explicacion, obtener, reproductor=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(1000, 560)
        self.obtener = obtener
        self.reproductor = reproductor
        self.rutas = []
        self.elegida = None
        self._siguiente = {}

        lay = QVBoxLayout(self)
        texto = QLabel(explicacion)
        texto.setWordWrap(True)
        lay.addWidget(texto)
        self.solo_5 = QCheckBox("Solo 5 estrellas")
        self.solo_5.setChecked(True)
        self.solo_5.toggled.connect(self.rellenar)
        lay.addWidget(self.solo_5)

        self.tabla = QTableWidget(0, 0)
        self.tabla.verticalHeader().hide()
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.doubleClicked.connect(self.usar)
        lay.addWidget(self.tabla, 1)
        self.vacio = QLabel()
        lay.addWidget(self.vacio)

        botones = QHBoxLayout()
        self.escuchar = QPushButton("▶ Escuchar")
        self.escuchar.setToolTip("En una tanda, cada clic pasa al tema siguiente")
        self.escuchar.clicked.connect(self.alternar)
        self.escuchar.setEnabled(reproductor is not None)
        usar = QPushButton("Usar")
        usar.setDefault(True)
        usar.clicked.connect(self.usar)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        botones.addWidget(self.escuchar)
        botones.addStretch(1)
        botones.addWidget(usar)
        botones.addWidget(cancelar)
        lay.addLayout(botones)
        self.rellenar()

    def rellenar(self):
        columnas, filas, self.rutas = self.obtener(self.solo_5.isChecked())
        self.tabla.clear()
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        self.tabla.setRowCount(len(filas))
        for i, fila in enumerate(filas):
            for j, v in enumerate(fila):
                it = QTableWidgetItem(str(v))
                it.setToolTip(str(v))
                self.tabla.setItem(i, j, it)
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeToContents)
        h.setStretchLastSection(True)
        self.vacio.setText("" if filas else "<i>No hay nada que proponer con estas condiciones"
                                             + (" (prueba a quitar «Solo 5 estrellas»)" if self.solo_5.isChecked()
                                                else "") + ".</i>")
        if filas:
            self.tabla.selectRow(0)

    def _fila(self):
        filas = self.tabla.selectionModel().selectedRows()
        return filas[0].row() if filas else None

    def alternar(self):
        i = self._fila()
        if i is None or self.reproductor is None or not self.rutas[i]:
            return
        n = self._siguiente.get(i, 0) % len(self.rutas[i])
        ruta = self.rutas[i][n]
        clave = ("propuesta", ruta)
        if self.reproductor.sonando(clave) and len(self.rutas[i]) == 1:
            self.reproductor.parar()
            return
        self._siguiente[i] = n + 1
        self.reproductor.reproducir(clave, ruta, self.tabla.item(i, 0).text())

    def usar(self):
        self.elegida = self._fila()
        if self.elegida is not None:
            self.accept()

    def done(self, r):
        if self.reproductor is not None and isinstance(self.reproductor.clave, tuple) \
                and self.reproductor.clave[:1] == ("propuesta",):
            self.reproductor.parar()
        super().done(r)
