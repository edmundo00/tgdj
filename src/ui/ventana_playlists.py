"""Archivo → Reparar playlists: encontrar las canciones que se movieron y reescribir la playlist."""
import glob
import os

import pandas as pd
from PyQt5.QtCore import Qt, QSettings, QEvent
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QFileDialog, QMessageBox, QSplitter, QApplication, QCheckBox,
)

from src.config.config import dropbox_path, m3u_start_path
from src.utils import playlists, coleccion

NO_CAMBIAR = "— dejar como está —"


def corta(ruta):
    """Ruta a partir de MUSICA (lo que importa), para que no se corte por el principio."""
    for sep in ("MUSICA\\", "MUSICA/"):
        if sep in ruta:
            return "…\\" + ruta.split(sep, 1)[1]
    return ruta


def carpeta_playlists():
    defecto = os.path.dirname(m3u_start_path.rstrip("\\/"))       # ...\TDJ\playlists
    return QSettings("TangoTags", "TangoTags").value("carpeta_playlists", defecto) or defecto


class VentanaPlaylists(QWidget):
    def __init__(self, parent, reproductor, obtener_indice_coleccion):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Reparar playlists")
        self.resize(1450, 750)
        self.reproductor = reproductor
        self.obtener_indice_coleccion = obtener_indice_coleccion
        self.indice = None
        self.analisis = {}       # playlist -> entradas
        self.actual = None
        lay = QVBoxLayout(self)

        fila = QHBoxLayout()
        self.etiqueta = QLabel()
        cambiar = QPushButton("Cambiar carpeta…")
        cambiar.clicked.connect(self.cambiar_carpeta)
        self.boton_analizar = QPushButton("⟳  Analizar")
        self.boton_analizar.clicked.connect(self.analizar)
        self.boton_todas = QPushButton("Reparar todas las seguras…")
        self.boton_todas.setToolTip("En todas las playlists, sustituir solo las canciones con propuesta segura "
                                    "(mismo tamaño de archivo = la misma grabación)")
        self.boton_todas.clicked.connect(self.reparar_todas)
        fila.addWidget(self.etiqueta, 1)
        fila.addWidget(cambiar)
        fila.addWidget(self.boton_analizar)
        fila.addWidget(self.boton_todas)
        lay.addLayout(fila)

        division = QSplitter(Qt.Horizontal)
        izquierda = QWidget()
        li = QVBoxLayout(izquierda)
        li.setContentsMargins(0, 0, 0, 0)
        self.solo_rotas = QCheckBox("Solo las que tienen canciones que no se encuentran")
        self.solo_rotas.setChecked(True)
        self.solo_rotas.toggled.connect(self.pintar_lista)
        li.addWidget(self.solo_rotas)
        self.lista = QTableWidget(0, 3)
        self.lista.setHorizontalHeaderLabels(["Playlist", "No se encuentran", "Seguras"])
        self.lista.verticalHeader().hide()
        self.lista.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lista.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lista.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lista.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.lista.itemSelectionChanged.connect(self.elegir_playlist)
        li.addWidget(self.lista)
        division.addWidget(izquierda)

        derecha = QWidget()
        ld = QVBoxLayout(derecha)
        ld.setContentsMargins(0, 0, 0, 0)
        self.titulo = QLabel("Elige una playlist de la lista.")
        self.titulo.setWordWrap(True)
        ld.addWidget(self.titulo)
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Canción", "Ruta que ya no existe", "Sustituir por", "▶"])
        self.tabla.verticalHeader().hide()
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tabla.setColumnWidth(3, 34)
        self.tabla.viewport().installEventFilter(self)
        ld.addWidget(self.tabla, 1)
        botones = QHBoxLayout()
        self.boton_guardar = QPushButton("Guardar playlist reparada")
        self.boton_guardar.setStyleSheet("QPushButton{font-weight:bold; padding:6px 14px;}")
        self.boton_guardar.clicked.connect(self.guardar)
        self.boton_restaurar = QPushButton("Restaurar la copia anterior")
        self.boton_restaurar.clicked.connect(self.restaurar)
        botones.addStretch(1)
        botones.addWidget(self.boton_restaurar)
        botones.addWidget(self.boton_guardar)
        ld.addLayout(botones)
        division.addWidget(derecha)
        division.setSizes([420, 1030])
        lay.addWidget(division, 1)

        self.reproductor.cambiado.connect(lambda _: self.pintar_play())
        self.etiqueta.setText(f"Playlists de: <b>{carpeta_playlists()}</b>")

    # ------------------------------------------------------------------ análisis
    def cambiar_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta de las playlists", carpeta_playlists())
        if carpeta:
            QSettings("TangoTags", "TangoTags").setValue("carpeta_playlists", carpeta)
            self.etiqueta.setText(f"Playlists de: <b>{carpeta}</b>")
            self.analizar()

    def analizar(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.indice is None:
                self.titulo.setText("Preparando el índice de la colección…")
                QApplication.processEvents()
                self.indice = self.obtener_indice_coleccion()
                if self.indice is None:
                    return
            self.analisis = {}
            for p in sorted(glob.glob(os.path.join(carpeta_playlists(), "**", "*.m3u*"), recursive=True)):
                try:
                    self.analisis[p] = playlists.analizar(p, self.indice, dropbox_path)
                except Exception as e:
                    print(f"No se pudo leer {p}: {e}")
        finally:
            QApplication.restoreOverrideCursor()
        self.pintar_lista()
        rotas = sum(1 for es in self.analisis.values() for e in es if not e.existe)
        seguras = sum(1 for es in self.analisis.values() for e in es if not e.existe and playlists.propuesta_segura(e))
        self.titulo.setText(f"{len(self.analisis)} playlists: {rotas} canciones no se encuentran, "
                            f"{seguras} con sustituto seguro. Elige una playlist a la izquierda.")

    def pintar_lista(self):
        filas = [(p, es) for p, es in self.analisis.items()
                 if not self.solo_rotas.isChecked() or any(not e.existe for e in es)]
        self.lista.setRowCount(len(filas))
        self.filas_lista = [p for p, _ in filas]
        for i, (p, es) in enumerate(filas):
            rotas = [e for e in es if not e.existe]
            seguras = sum(bool(playlists.propuesta_segura(e)) for e in rotas)
            nombre = QTableWidgetItem(os.path.relpath(p, carpeta_playlists()))
            nombre.setToolTip(p)
            self.lista.setItem(i, 0, nombre)
            for c, v in ((1, len(rotas)), (2, seguras)):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignCenter)
                if c == 1 and v:
                    it.setBackground(QColor("#ffcdd2"))
                self.lista.setItem(i, c, it)

    # ------------------------------------------------------------------ una playlist
    def elegir_playlist(self):
        filas = self.lista.selectionModel().selectedRows()
        if not filas:
            return
        self.actual = self.filas_lista[filas[0].row()]
        self.pintar_tabla()

    def pintar_tabla(self):
        entradas = [e for e in self.analisis.get(self.actual, []) if not e.existe]
        self.entradas = entradas
        self.combos = []
        self.tabla.setRowCount(len(entradas))
        for i, e in enumerate(entradas):
            cancion = " — ".join(x for x in (e.artista, e.titulo) if x) or os.path.basename(e.ruta.replace("\\", "/"))
            self.tabla.setItem(i, 0, QTableWidgetItem(cancion))
            vieja = QTableWidgetItem(corta(e.ruta))
            vieja.setForeground(QColor("#b71c1c"))
            vieja.setToolTip(e.ruta)
            self.tabla.setItem(i, 1, vieja)
            combo = QComboBox()
            combo.addItem(NO_CAMBIAR, "")
            segura = playlists.propuesta_segura(e)
            for ruta, motivo, _ in e.candidatos:
                combo.addItem(f"{'✔ ' if ruta == segura else ''}{corta(ruta)}   ({motivo})", ruta)
            if segura:
                combo.setCurrentIndex([combo.itemData(k) for k in range(combo.count())].index(segura))
            elif not e.candidatos:
                combo.setItemText(0, "— no se encuentra en tu colección —")
            combo.setToolTip("✔ = mismo tamaño de archivo: casi seguro la misma grabación")
            combo.currentIndexChanged.connect(lambda _: self.pintar_play())
            self.tabla.setCellWidget(i, 2, combo)
            self.combos.append(combo)
            self.tabla.setItem(i, 3, QTableWidgetItem("▶"))
        self.titulo.setText(f"<b>{os.path.basename(self.actual)}</b>: {len(entradas)} canciones no se encuentran. "
                            "Elige por qué sustituirlas (✔ = mismo archivo, seguro) y pulsa <b>Guardar</b>. "
                            "Antes de guardar se hace una copia de la playlist.")
        self.pintar_play()

    def eventFilter(self, objeto, evento):
        if objeto is self.tabla.viewport() and evento.type() == QEvent.MouseButtonPress:
            indice = self.tabla.indexAt(evento.pos())
            if indice.column() == 3 and 0 <= indice.row() < len(self.combos):
                ruta = self.combos[indice.row()].currentData()
                if ruta:
                    self.reproductor.alternar(("playlist", ruta), ruta, f"Sustituto: {os.path.basename(ruta)}")
                return True
        return super().eventFilter(objeto, evento)

    def pintar_play(self):
        for i, combo in enumerate(getattr(self, "combos", [])):
            it = self.tabla.item(i, 3)
            if it is None:
                continue
            ruta = combo.currentData()
            suena = bool(ruta) and self.reproductor.sonando(("playlist", ruta))
            it.setText("■" if suena else ("▶" if ruta else ""))
            it.setBackground(QColor("#66bb6a") if suena else QColor("white"))

    def guardar(self):
        if not self.actual:
            return
        reemplazos = {e.linea: c.currentData() for e, c in zip(self.entradas, self.combos) if c.currentData()}
        if not reemplazos:
            QMessageBox.information(self, "Guardar", "No has elegido ningún sustituto.")
            return
        copia = playlists.reparar(self.actual, reemplazos)
        QMessageBox.information(self, "Playlist reparada",
                                f"Sustituidas {len(reemplazos)} canciones en {os.path.basename(self.actual)}.\n"
                                f"Copia de la versión anterior: {os.path.basename(copia)}")
        self.analisis[self.actual] = playlists.analizar(self.actual, self.indice, dropbox_path)
        self.pintar_lista()
        self.pintar_tabla()

    def restaurar(self):
        if not self.actual:
            return
        base, ext = os.path.splitext(os.path.basename(self.actual))
        copias = sorted(glob.glob(os.path.join(playlists.CARPETA_COPIAS, f"{base}_*{ext}")))
        if not copias:
            QMessageBox.information(self, "Restaurar", "No hay copias de esta playlist.")
            return
        if QMessageBox.question(self, "Restaurar", f"¿Volver a la versión guardada en {os.path.basename(copias[-1])}?") \
                != QMessageBox.Yes:
            return
        playlists.restaurar(copias[-1], self.actual)
        os.replace(copias[-1], copias[-1] + ".restaurada")
        self.analisis[self.actual] = playlists.analizar(self.actual, self.indice, dropbox_path)
        self.pintar_lista()
        self.pintar_tabla()

    def reparar_todas(self):
        cambios = {p: {e.linea: playlists.propuesta_segura(e) for e in es if not e.existe and playlists.propuesta_segura(e)}
                   for p, es in self.analisis.items()}
        cambios = {p: r for p, r in cambios.items() if r}
        total = sum(len(r) for r in cambios.values())
        if not total:
            QMessageBox.information(self, "Reparar todas", "No hay sustitutos seguros (pulsa Analizar primero).")
            return
        if QMessageBox.question(self, "Reparar todas",
                                f"Se van a sustituir {total} canciones en {len(cambios)} playlists, solo las seguras "
                                "(mismo tamaño de archivo). Se hace una copia de cada playlist.\n\n¿Continuar?") \
                != QMessageBox.Yes:
            return
        for p, r in cambios.items():
            playlists.reparar(p, r)
            self.analisis[p] = playlists.analizar(p, self.indice, dropbox_path)
        self.pintar_lista()
        if self.actual:
            self.pintar_tabla()
        QMessageBox.information(self, "Reparar todas", f"Sustituidas {total} canciones en {len(cambios)} playlists.")
