"""Copias idénticas dentro de cada colección: elegir cuál conservar y mover el resto a _duplicados."""
import os

import pandas as pd
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QColor, QFont, QBrush
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QApplication, QMessageBox,
)

from src.biblioteca.biblioteca import CARPETA_DUPLICADOS, raices_absolutas
from src.utils import duplicados


def tamano_texto(b):
    return f"{int(b) / 1e6:.1f} MB"


class VentanaDuplicados(QWidget):
    def __init__(self, parent, reproductor, biblioteca, colecciones=None):
        super().__init__(parent, Qt.Window)
        self.biblioteca = biblioteca
        self.raiz_de = {}         # ruta -> carpeta raíz de la biblioteca (para mover a su _duplicados)
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
            "Copias <b>idénticas</b> (mismo audio) dentro de cada colección de tu biblioteca — "
            f"buscando en: <b>{donde}</b>.<br>Las copias no se borran: se mueven a <i>_duplicados</i> "
            "(misma estructura de carpetas) y se puede deshacer. Las colecciones distintas no se comparan entre sí.")

    # ------------------------------------------------------------------ buscar
    def buscar(self):
        self._cancelar = False
        self.progreso.show()
        self.boton_cancelar.show()
        self.boton_buscar.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            df = self.biblioteca.dataframe("en_nube=0")
            if self.colecciones:
                df = df[df["coleccion"].isin(self.colecciones)]
            self.raiz_de = dict(zip(df["ruta"], df["raiz"]))
            self.tags = {f["ruta"]: f for f in df[["ruta", "title", "artist", "year", "composer"]].to_dict("records")}
            archivos = list(zip(df["ruta"], df["coleccion"], df["bytes"]))

            def progreso(hechos, total):
                self.progreso.setMaximum(total)
                self.progreso.setValue(hechos)
                self.progreso.setFormat("Comparando contenido… %v de %m")
                QApplication.processEvents()

            # Las huellas de audio se guardan en la biblioteca: la segunda vez es casi instantáneo
            self.grupos = duplicados.buscar(archivos, progreso, lambda: self._cancelar,
                                            huellas_de=self.biblioteca.huellas)
        finally:
            QApplication.restoreOverrideCursor()
            self.progreso.hide()
            self.boton_cancelar.hide()
            self.boton_buscar.setEnabled(True)
        revisadas = {r for r, t in self.tags.items() if str(t.get("composer", "")).startswith("Musica:")}
        self.conservar = {i: duplicados.sugerir_conservar(g, revisadas) for i, g in enumerate(self.grupos)}
        self.pintar()

    def relativa(self, ruta):
        raiz = self.raiz_de.get(ruta, "")
        return os.path.join(os.path.basename(raiz), os.path.relpath(ruta, raiz)) if raiz else ruta

    # ------------------------------------------------------------------ tabla
    def pintar(self):
        filas = sum(len(g) + 1 for g in self.grupos)
        self.tabla.blockSignals(True)
        self.tabla.clearSpans()
        self.tabla.setRowCount(filas)
        self.fila_info = {}
        n = 0
        for i, g in enumerate(self.grupos):
            tam = os.path.getsize(g[0]) if os.path.exists(g[0]) else 0
            cab = QTableWidgetItem(f"Grupo {i + 1}: {len(g)} copias idénticas de {tamano_texto(tam)} — "
                                   f"{os.path.dirname(self.relativa(g[0]))}")
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
                nombre = QTableWidgetItem(self.relativa(ruta))
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
                f"Se van a mover {len(mover)} archivos a la carpeta «{CARPETA_DUPLICADOS}» de su biblioteca "
                "(misma estructura de carpetas).\n\nNo se borra nada y se puede deshacer.\n\nOjo: si MusicBee o alguna "
                "playlist usaba esas copias, dejarán de encontrarlas (Reparar playlists las arregla; en MusicBee: "
                "Herramientas → Volver a escanear).\n\n¿Continuar?") != QMessageBox.Yes:
            return
        if self.reproductor.clave is not None:
            self.reproductor.parar()
        por_raiz = {}
        for r in mover:
            por_raiz.setdefault(self.raiz_de.get(r) or os.path.dirname(r), []).append(r)
        movidos, errores, registros = 0, [], []
        for raiz, rutas in por_raiz.items():
            n, e, registro = duplicados.mover(rutas, raiz)
            movidos, errores = movidos + n, errores + e
            registros.append(os.path.basename(registro))
        self.grupos = []
        self.pintar()
        self.avisar_biblioteca(mover)
        mensaje = f"Movidos {movidos} archivos. Registro: {', '.join(registros)}"
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
        movidos = pd.read_csv(registro, sep=";", na_filter=False, dtype=str, encoding="utf-8-sig")["origen"].tolist()
        restaurados, errores = duplicados.deshacer(registro)
        self.avisar_biblioteca(movidos)
        mensaje = f"Devueltos {restaurados} archivos a su sitio."
        if errores:
            mensaje += f"\n\n{len(errores)} con problemas:\n" + "\n".join(f"{r}: {e}" for r, e in errores[:10])
        (QMessageBox.warning if errores else QMessageBox.information)(self, "Deshacer", mensaje)

    def avisar_biblioteca(self, rutas):
        """La biblioteca (y Mi biblioteca) se enteran al momento de lo movido."""
        refrescar = getattr(self.parent(), "refrescar_biblioteca", None)
        if refrescar is not None:
            refrescar(rutas)

    def abrir_carpeta(self):
        for raiz, _, _ in raices_absolutas(self.biblioteca.config):
            carpeta = os.path.join(raiz, CARPETA_DUPLICADOS)
            if os.path.isdir(carpeta):
                os.startfile(carpeta)
                return
        QMessageBox.information(self, "_duplicados", "Todavía no se ha movido nada.")
