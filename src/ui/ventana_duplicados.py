"""Copias idénticas dentro de cada colección: elegir cuál conservar y mover el resto a _duplicados."""
import os

import pandas as pd
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QColor, QFont, QBrush
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QApplication, QMessageBox,
)

from src.utils import coleccion, duplicados
from src.ui.ventana_estado import raiz_musica


def tamano_texto(b):
    return f"{int(b) / 1e6:.1f} MB"


class VentanaDuplicados(QWidget):
    def __init__(self, parent, reproductor, colecciones=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Duplicados")
        self.resize(1300, 750)
        self.reproductor = reproductor
        self.colecciones = colecciones or []
        self.grupos = []          # listas de rutas
        self.conservar = {}       # nº de grupo -> ruta que se conserva
        self.fila_info = {}       # fila -> (grupo, ruta)
        self.tags = {}
        self._cancelar = False
        lay = QVBoxLayout(self)

        self.titulo = QLabel()
        self.titulo.setWordWrap(True)
        lay.addWidget(self.titulo)
        fila = QHBoxLayout()
        self.boton_buscar = QPushButton("Buscar copias")
        self.boton_buscar.clicked.connect(self.buscar)
        self.progreso = QProgressBar()
        self.progreso.hide()
        self.boton_cancelar = QPushButton("Cancelar")
        self.boton_cancelar.hide()
        self.boton_cancelar.clicked.connect(lambda: setattr(self, "_cancelar", True))
        fila.addWidget(self.boton_buscar)
        fila.addWidget(self.progreso, 1)
        fila.addWidget(self.boton_cancelar)
        fila.addStretch(1)
        lay.addLayout(fila)

        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(["Conservar", "▶", "Archivo", "Formato", "Tamaño", "Tags"])
        self.tabla.verticalHeader().hide()
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(5, QHeaderView.Stretch)
        self.tabla.itemChanged.connect(self.cambio_conservar)
        self.tabla.viewport().installEventFilter(self)
        lay.addWidget(self.tabla, 1)

        abajo = QHBoxLayout()
        self.resumen = QLabel()
        self.boton_mover = QPushButton("Mover las copias a _duplicados…")
        self.boton_mover.setStyleSheet("QPushButton{font-weight:bold; padding:6px 14px;}")
        self.boton_mover.clicked.connect(self.mover)
        self.boton_mover.setEnabled(False)
        deshacer = QPushButton("Deshacer último movimiento")
        deshacer.clicked.connect(self.deshacer)
        abrir = QPushButton("Abrir carpeta _duplicados")
        abrir.clicked.connect(self.abrir_carpeta)
        abajo.addWidget(self.resumen, 1)
        abajo.addWidget(abrir)
        abajo.addWidget(deshacer)
        abajo.addWidget(self.boton_mover)
        lay.addLayout(abajo)
        self.reproductor.cambiado.connect(lambda _: self.pintar_play())
        self.actualizar_titulo()

    def actualizar_titulo(self):
        donde = ", ".join(self.colecciones) if self.colecciones else "todas las colecciones"
        self.titulo.setText(
            f"Copias <b>idénticas</b> (mismo contenido) dentro de cada colección de <b>{raiz_musica()}</b> — "
            f"buscando en: <b>{donde}</b>.<br>Las copias no se borran: se mueven a <i>_duplicados</i> "
            "(misma estructura de carpetas) y se puede deshacer. Las colecciones distintas no se comparan entre sí.")

    # ------------------------------------------------------------------ buscar
    def buscar(self):
        self._cancelar = False
        raiz = raiz_musica()
        self.progreso.show()
        self.boton_cancelar.show()
        self.boton_buscar.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.progreso.setMaximum(0)
            self.progreso.setFormat("Mirando tamaños…")
            QApplication.processEvents()
            archivos = [(r, c, t) for r, c, t, _ in coleccion.listar(raiz)
                        if not self.colecciones or c in self.colecciones]

            def progreso(hechos, total):
                self.progreso.setMaximum(total)
                self.progreso.setValue(hechos)
                self.progreso.setFormat("Comparando contenido… %v de %m")
                QApplication.processEvents()

            self.grupos = duplicados.buscar(archivos, progreso, lambda: self._cancelar)
        finally:
            QApplication.restoreOverrideCursor()
            self.progreso.hide()
            self.boton_cancelar.hide()
            self.boton_buscar.setEnabled(True)
        self.cargar_tags()
        revisadas = {r for r, t in self.tags.items() if str(t.get("composer", "")).startswith("Musica:")}
        self.conservar = {i: duplicados.sugerir_conservar(g, revisadas) for i, g in enumerate(self.grupos)}
        self.pintar()

    def cargar_tags(self):
        self.tags = {}
        if os.path.exists(coleccion.CACHE):
            df = pd.read_csv(coleccion.CACHE, sep=";", na_filter=False, dtype=str, encoding="utf-8")
            rutas = {r for g in self.grupos for r in g}
            self.tags = {f["ruta"]: f for f in df[df["ruta"].isin(rutas)].to_dict("records")}

    # ------------------------------------------------------------------ tabla
    def pintar(self):
        raiz = raiz_musica()
        filas = sum(len(g) + 1 for g in self.grupos)
        self.tabla.blockSignals(True)
        self.tabla.clearSpans()
        self.tabla.setRowCount(filas)
        self.fila_info = {}
        n = 0
        for i, g in enumerate(self.grupos):
            tam = os.path.getsize(g[0]) if os.path.exists(g[0]) else 0
            cab = QTableWidgetItem(f"Grupo {i + 1}: {len(g)} copias idénticas de {tamano_texto(tam)} — "
                                   f"{os.path.relpath(os.path.dirname(g[0]), raiz)}")
            cab.setFont(QFont("", -1, QFont.Bold))
            cab.setBackground(QColor("#eceff1"))
            cab.setFlags(Qt.ItemIsEnabled)
            self.tabla.setItem(n, 0, cab)
            self.tabla.setSpan(n, 0, 1, 6)
            n += 1
            for ruta in g:
                self.fila_info[n] = (i, ruta)
                usar = QTableWidgetItem("")
                usar.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                usar.setCheckState(Qt.Checked if self.conservar.get(i) == ruta else Qt.Unchecked)
                self.tabla.setItem(n, 0, usar)
                self.tabla.setItem(n, 1, QTableWidgetItem("▶"))
                nombre = QTableWidgetItem(os.path.relpath(ruta, raiz))
                nombre.setToolTip(ruta)
                self.tabla.setItem(n, 2, nombre)
                self.tabla.setItem(n, 3, QTableWidgetItem(os.path.splitext(ruta)[1][1:].upper()))
                self.tabla.setItem(n, 4, QTableWidgetItem(tamano_texto(tam)))
                t = self.tags.get(ruta, {})
                self.tabla.setItem(n, 5, QTableWidgetItem(
                    " — ".join(x for x in (t.get("title", ""), t.get("artist", ""), t.get("year", "")) if x)))
                n += 1
        self.tabla.blockSignals(False)
        self.pintar_estado_filas()
        self.pintar_play()

    def pintar_estado_filas(self):
        """Lo que se conserva en blanco; lo que se moverá, tachado y en gris."""
        self.tabla.blockSignals(True)
        for fila, (i, ruta) in self.fila_info.items():
            se_mueve = self.conservar.get(i) != ruta
            for c in range(2, 6):
                it = self.tabla.item(fila, c)
                if it:
                    f = it.font()
                    f.setStrikeOut(se_mueve)
                    it.setFont(f)
                    it.setForeground(QBrush(QColor("#9e9e9e" if se_mueve else "#000")))
        self.tabla.blockSignals(False)
        copias = sum(len(g) - 1 for g in self.grupos)
        gb = sum((len(g) - 1) * (os.path.getsize(g[0]) if os.path.exists(g[0]) else 0) for g in self.grupos) / 1e9
        self.resumen.setText(f"{len(self.grupos)} grupos — se moverían <b>{copias}</b> copias ({gb:.1f} GB). "
                             "Marca en «Conservar» el que quieres quedarte (tachado = se mueve).")
        self.boton_mover.setEnabled(copias > 0)

    def cambio_conservar(self, item):
        if item.column() != 0 or item.row() not in self.fila_info:
            return
        i, ruta = self.fila_info[item.row()]
        if item.checkState() == Qt.Checked:
            self.conservar[i] = ruta
        elif self.conservar.get(i) == ruta:
            item.setCheckState(Qt.Checked)        # siempre se conserva uno por grupo
            return
        self.tabla.blockSignals(True)
        for fila, (j, r) in self.fila_info.items():
            if j == i:
                self.tabla.item(fila, 0).setCheckState(Qt.Checked if r == self.conservar[i] else Qt.Unchecked)
        self.tabla.blockSignals(False)
        self.pintar_estado_filas()

    # ------------------------------------------------------------------ escuchar
    def eventFilter(self, objeto, evento):
        if objeto is self.tabla.viewport() and evento.type() == QEvent.MouseButtonPress:
            indice = self.tabla.indexAt(evento.pos())
            if indice.column() == 1 and indice.row() in self.fila_info:
                ruta = self.fila_info[indice.row()][1]
                self.reproductor.alternar(("duplicado", ruta), ruta, f"Duplicado: {os.path.basename(ruta)}")
                return True
        return super().eventFilter(objeto, evento)

    def pintar_play(self):
        for fila, (_, ruta) in self.fila_info.items():
            it = self.tabla.item(fila, 1)
            if it:
                suena = self.reproductor.sonando(("duplicado", ruta))
                it.setText("■" if suena else "▶")
                it.setBackground(QColor("#66bb6a") if suena else QColor("white"))

    # ------------------------------------------------------------------ mover / deshacer
    def mover(self):
        mover = [r for i, g in enumerate(self.grupos) for r in g if self.conservar.get(i) != r]
        if not mover:
            return
        if QMessageBox.question(
                self, "Mover copias",
                f"Se van a mover {len(mover)} archivos a «{os.path.join(raiz_musica(), coleccion.CARPETA_DUPLICADOS)}».\n\n"
                "No se borra nada y se puede deshacer.\n\nOjo: si MusicBee o alguna playlist usaba esas copias, "
                "dejarán de encontrarlas (en MusicBee: Herramientas → Volver a escanear).\n\n¿Continuar?") != QMessageBox.Yes:
            return
        if self.reproductor.clave is not None:
            self.reproductor.parar()
        movidos, errores, registro = duplicados.mover(mover, raiz_musica())
        self.grupos = []
        self.pintar()
        mensaje = f"Movidos {movidos} archivos. Registro: {os.path.basename(registro)}"
        if errores:
            mensaje += f"\n\n{len(errores)} no se pudieron mover:\n" + "\n".join(f"{r}: {e}" for r, e in errores[:10])
        (QMessageBox.warning if errores else QMessageBox.information)(self, "Mover copias", mensaje)

    def deshacer(self):
        registro = duplicados.ultimo_registro()
        if not registro:
            QMessageBox.information(self, "Deshacer", "No hay movimientos que deshacer.")
            return
        n = len(pd.read_csv(registro, sep=";", dtype=str, encoding="utf-8-sig"))
        if QMessageBox.question(self, "Deshacer", f"¿Devolver a su sitio los {n} archivos del último movimiento?") \
                != QMessageBox.Yes:
            return
        restaurados, errores = duplicados.deshacer(registro)
        mensaje = f"Devueltos {restaurados} archivos a su sitio."
        if errores:
            mensaje += f"\n\n{len(errores)} con problemas:\n" + "\n".join(f"{r}: {e}" for r, e in errores[:10])
        (QMessageBox.warning if errores else QMessageBox.information)(self, "Deshacer", mensaje)

    def abrir_carpeta(self):
        carpeta = os.path.join(raiz_musica(), coleccion.CARPETA_DUPLICADOS)
        if os.path.isdir(carpeta):
            os.startfile(carpeta)
        else:
            QMessageBox.information(self, "_duplicados", "Todavía no se ha movido nada.")
