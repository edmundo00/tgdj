"""
Tandas de reserva para la noche (vals de cumpleaños, tango rítmico extra, tango tranquilo para el final), cada una
con su cortina delante. Se pueden escuchar, cambiar por otra opción y guardar en un .m3u aparte.
Todo sale de catalogo (solo MUSICA\\Edmundo) y no repite nada de la noche.
"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton, QCheckBox, QFileDialog, QMessageBox, QApplication,
)

from src.diapos import catalogo
from src.utils.buscar_artista import normalizar_nombre


class DialogoReserva(QDialog):
    def __init__(self, parent, cat, tandas, historial, playlist, reproductor=None):
        super().__init__(parent)
        self.setWindowTitle("Tandas de reserva")
        self.resize(1250, 420)
        self.cat, self.tandas, self.historial, self.playlist = cat, tandas, historial, playlist
        self.reproductor = reproductor
        self._siguiente = {}

        lay = QVBoxLayout(self)
        texto = QLabel("Tandas preparadas por si hacen falta (cumpleaños, sobra tiempo, hay que cerrar antes), cada "
                       "una con su cortina delante. No repiten nada de la noche ni orquesta entre ellas; solo de "
                       "MUSICA\\Edmundo. Se guardan en un .m3u aparte para tenerlas a mano en MusicBee.")
        texto.setWordWrap(True)
        lay.addWidget(texto)
        self.solo_5 = QCheckBox("Solo 5 estrellas")
        self.solo_5.setChecked(True)
        self.solo_5.toggled.connect(self.calcular)
        lay.addWidget(self.solo_5)

        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels(["Para qué", "Orquesta", "Cantor", "Años", "Carácter", "Temas",
                                              "Cortina delante"])
        self.tabla.verticalHeader().hide()
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setWordWrap(True)
        lay.addWidget(self.tabla, 1)

        botones = QHBoxLayout()
        escuchar = QPushButton("▶ Escuchar")
        escuchar.setToolTip("Cada clic pasa al tema siguiente de la tanda")
        escuchar.clicked.connect(self.escuchar)
        escuchar.setEnabled(reproductor is not None)
        otra = QPushButton("Otra opción")
        otra.clicked.connect(self.otra_opcion)
        otra_cortina = QPushButton("Otra cortina")
        otra_cortina.clicked.connect(self.otra_cortina)
        guardar = QPushButton("Guardar reserva…")
        guardar.setDefault(True)
        guardar.clicked.connect(self.guardar)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.reject)
        for b in (escuchar, otra, otra_cortina):
            botones.addWidget(b)
        botones.addStretch(1)
        botones.addWidget(guardar)
        botones.addWidget(cerrar)
        lay.addLayout(botones)
        self.calcular()

    # ------------------------------------------------------------------ datos
    def calcular(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.elegidas, self.cortinas, self.cortina_de = catalogo.reserva(self.cat, self.tandas, self.historial,
                                                                             self.solo_5.isChecked())
        finally:
            QApplication.restoreOverrideCursor()
        self.rellenar()

    def _tanda(self, clave):
        opciones, indice = self.elegidas[clave]
        return opciones[indice] if indice is not None else None

    def _cortina(self, clave):
        n = self.cortina_de.get(clave)
        return self.cortinas.iloc[n] if n is not None else None

    def rellenar(self):
        self.tabla.setRowCount(len(catalogo.RESERVAS))
        for fila, (clave, para_que, _) in enumerate(catalogo.RESERVAS):
            t, c = self._tanda(clave), self._cortina(clave)
            valores = [para_que] + ([t.orquesta, t.cantor, t.anos, t.motivo or "—", " · ".join(t.canciones["title"])]
                                    if t else ["(no hay ninguna)", "", "", "", ""])
            valores.append(f"{c['title']} ({c['artist']})" if c is not None else "")
            for col, v in enumerate(valores):
                it = QTableWidgetItem(v)
                it.setToolTip(v)
                self.tabla.setItem(fila, col, it)
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.Stretch)
        self.tabla.resizeRowsToContents()
        if self.tabla.currentRow() < 0:
            self.tabla.selectRow(0)

    def _clave(self):
        fila = self.tabla.currentRow()
        return catalogo.RESERVAS[fila][0] if fila >= 0 else None

    # ------------------------------------------------------------------ acciones
    def otra_opcion(self):
        clave = self._clave()
        if clave is None:
            return
        opciones, indice = self.elegidas[clave]
        if not opciones:
            return
        otras = {normalizar_nombre(self._tanda(k).orquesta) for k in self.elegidas if k != clave and self._tanda(k)}
        for paso in range(1, len(opciones) + 1):
            n = ((indice or 0) + paso) % len(opciones)
            if normalizar_nombre(opciones[n].orquesta) not in otras:
                self.elegidas[clave] = (opciones, n)
                break
        fila = self.tabla.currentRow()
        self.rellenar()
        self.tabla.selectRow(fila)

    def otra_cortina(self):
        clave = self._clave()
        if clave is None or self.cortinas.empty:
            return
        ocupadas = {n for k, n in self.cortina_de.items() if k != clave}
        actual = self.cortina_de.get(clave, -1)
        for paso in range(1, len(self.cortinas) + 1):
            n = (actual + paso) % len(self.cortinas)
            if n not in ocupadas:
                self.cortina_de[clave] = n
                break
        fila = self.tabla.currentRow()
        self.rellenar()
        self.tabla.selectRow(fila)

    def escuchar(self):
        clave = self._clave()
        t = self._tanda(clave) if clave else None
        if t is None or self.reproductor is None:
            return
        rutas = list(t.canciones["ruta"])
        n = self._siguiente.get(clave, 0) % len(rutas)
        self._siguiente[clave] = n + 1
        self.reproductor.reproducir(("reserva", rutas[n]), rutas[n], t.canciones["title"].iloc[n])

    def rutas(self):
        """Cortina + tanda de cada reserva, en orden."""
        salida = []
        for clave, _, _ in catalogo.RESERVAS:
            t, c = self._tanda(clave), self._cortina(clave)
            if t is None:
                continue
            if c is not None:
                salida.append(c["ruta"])
            salida += list(t.canciones["ruta"])
        return salida

    def guardar(self):
        rutas = self.rutas()
        if not rutas:
            return
        base, _ = os.path.splitext(os.path.basename(self.playlist))
        destino, _ = QFileDialog.getSaveFileName(self, "Guardar tandas de reserva",
                                                 os.path.join(os.path.dirname(self.playlist), f"{base}_reserva.m3u"),
                                                 "Playlist (*.m3u)")
        if not destino:
            return
        if os.path.normcase(os.path.abspath(destino)) == os.path.normcase(os.path.abspath(self.playlist)):
            QMessageBox.warning(self, "Guardar", "Elige otro nombre: la playlist de la noche no se sobrescribe.")
            return
        try:
            with open(destino, "w", encoding="utf-8-sig", newline="\r\n") as f:
                f.write("\n".join(rutas) + "\n")
        except OSError as e:
            QMessageBox.critical(self, "Guardar", f"No se pudo guardar:\n{e}")
            return
        QMessageBox.information(self, "Guardada", f"Reserva guardada en:\n{destino}\n\n"
                                                  f"Para tenerla en MusicBee, arrástrala a la lista de playlists.")
        self.accept()

    def done(self, r):
        if self.reproductor is not None and isinstance(self.reproductor.clave, tuple) \
                and self.reproductor.clave[:1] == ("reserva",):
            self.reproductor.parar()
        super().done(r)
