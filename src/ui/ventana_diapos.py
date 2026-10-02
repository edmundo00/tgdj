"""Ventana para crear la presentación de las tandas a partir de una playlist."""
import os

from PyQt5.QtCore import Qt, QDate, QTime, QSettings
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDateEdit, QTimeEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QSplitter,
    QApplication, QProgressBar,
)

from src.config.config import m3u_start_path, presentations_start_path, default_milonga_data
from src.diapos.generador import (
    leer_playlist, agrupar_tandas, crear_presentacion, duracion_texto, nombre_archivo, compositor_para_diapo,
)
from src.utils.utils import convertir_segundos


class VentanaDiapos(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear diapos de las tandas")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1400, 800)
        self.settings = QSettings("TangoTags", "TangoTags")
        self.tandas = []
        self.playlist = None

        lay = QVBoxLayout(self)

        # --- Datos de la milonga (se recuerdan para la próxima vez)
        datos = QGridLayout()
        self.nombre = QLineEdit(self.settings.value("diapos_nombre", default_milonga_data["nombre"]))
        self.fecha = QDateEdit(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("dd/MM/yyyy")
        self.inicio = QTimeEdit(QTime.fromString(self.settings.value("diapos_inicio", default_milonga_data["hora_inicio"]), "HH:mm"))
        self.fin = QTimeEdit(QTime.fromString(self.settings.value("diapos_fin", default_milonga_data["hora_final"]), "HH:mm"))
        self.fecha.setMaximumWidth(130)
        for t in (self.inicio, self.fin):
            t.setDisplayFormat("HH:mm")
            t.setMaximumWidth(90)
            t.timeChanged.connect(self.actualizar_duracion)
        self.duracion = QLabel()
        datos.addWidget(QLabel("<b>Milonga:</b>"), 0, 0)
        datos.addWidget(self.nombre, 0, 1, 1, 6)
        datos.addWidget(QLabel("<b>Fecha:</b>"), 0, 7)
        datos.addWidget(self.fecha, 0, 8)
        datos.addWidget(QLabel("<b>De</b>"), 1, 0)
        datos.addWidget(self.inicio, 1, 1)
        datos.addWidget(QLabel("<b>a</b>"), 1, 2)
        datos.addWidget(self.fin, 1, 3)
        datos.addWidget(self.duracion, 1, 4, 1, 2)
        datos.setColumnStretch(6, 1)
        lay.addLayout(datos)

        fila = QHBoxLayout()
        self.boton_playlist = QPushButton("① Elegir playlist…")
        self.boton_playlist.clicked.connect(self.elegir_playlist)
        self.etiqueta_playlist = QLabel("<i>Ninguna playlist cargada</i>")
        fila.addWidget(self.boton_playlist)
        fila.addWidget(self.etiqueta_playlist, 1)
        lay.addLayout(fila)

        # --- Vista previa: tandas arriba, canciones de la tanda seleccionada abajo
        self.tabla_tandas = QTableWidget(0, 6)
        self.tabla_tandas.setHorizontalHeaderLabels(["#", "Tipo", "Título de la diapo", "Subtítulo", "Temas", "Duración"])
        self.tabla_tandas.verticalHeader().hide()
        self.tabla_tandas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_tandas.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_tandas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.tabla_tandas.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabla_tandas.itemSelectionChanged.connect(self.mostrar_canciones)

        self.tabla_canciones = QTableWidget(0, 5)
        self.tabla_canciones.setHorizontalHeaderLabels(["Título", "Artista", "Año", "Compositor (en la diapo)", "Duración"])
        self.tabla_canciones.verticalHeader().hide()
        self.tabla_canciones.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.tabla_canciones.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        division = QSplitter(Qt.Vertical)
        division.addWidget(self.tabla_tandas)
        division.addWidget(self.tabla_canciones)
        division.setSizes([500, 200])
        lay.addWidget(division, 1)

        self.resumen = QLabel()
        lay.addWidget(self.resumen)

        abajo = QHBoxLayout()
        self.progreso = QProgressBar()
        self.progreso.hide()
        abajo.addWidget(self.progreso, 1)
        abajo.addStretch(1)
        self.boton_crear = QPushButton("② Crear presentación")
        self.boton_crear.setEnabled(False)
        self.boton_crear.setStyleSheet("QPushButton{font-weight:bold; padding:6px 18px;}")
        self.boton_crear.clicked.connect(self.crear)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.close)
        abajo.addWidget(self.boton_crear)
        abajo.addWidget(cerrar)
        lay.addLayout(abajo)

        self.actualizar_duracion()

    def datos(self):
        return {"milonga": self.nombre.text().strip(), "fecha": self.fecha.date().toPyDate(),
                "inicio": self.inicio.time().toString("HH:mm"), "fin": self.fin.time().toString("HH:mm")}

    def actualizar_duracion(self):
        d = self.datos()
        self.duracion.setText(f"Duración: {duracion_texto(d['inicio'], d['fin'])}")

    def elegir_playlist(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elegir playlist", self.settings.value("dir_playlist_diapos", m3u_start_path) or m3u_start_path,
            "Playlists (*.m3u *.m3u8);;Todos (*.*)")
        if ruta:
            self.settings.setValue("dir_playlist_diapos", os.path.dirname(ruta))
            self.cargar_playlist(ruta)

    def cargar_playlist(self, ruta):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            canciones, faltan = leer_playlist(ruta)
        finally:
            QApplication.restoreOverrideCursor()
        self.playlist = ruta
        self.tandas = agrupar_tandas(canciones)
        self.etiqueta_playlist.setText(f"<b>{os.path.basename(ruta)}</b> — {len(canciones)} canciones")
        self.rellenar_tandas()
        self.boton_crear.setEnabled(bool(self.tandas))
        if faltan:
            QMessageBox.warning(self, "Canciones no encontradas",
                                f"{len(faltan)} canción(es) de la playlist no existen y no saldrán en las diapos:\n\n"
                                + "\n".join(faltan[:15]))

    def rellenar_tandas(self):
        t = self.tabla_tandas
        t.setRowCount(len(self.tandas))
        n_tanda = 0
        avisos = 0
        for fila, tanda in enumerate(self.tandas):
            if not tanda.es_cortina:
                n_tanda += 1
            valores = [str(n_tanda) if not tanda.es_cortina else "",
                       "Cortina" if tanda.es_cortina else tanda.genero.capitalize(),
                       tanda.titulo_orquesta, tanda.subtitulo, str(len(tanda.canciones)),
                       convertir_segundos(tanda.duracion)]
            color = QColor("#eeeeee") if tanda.es_cortina else QColor("#ffffff")
            if tanda.avisos:
                color = QColor("#ffcdd2")
                avisos += 1
            for col, v in enumerate(valores):
                it = QTableWidgetItem(v)
                it.setBackground(color)
                it.setToolTip("\n".join(tanda.avisos) if tanda.avisos else v)
                if col == 2 and not tanda.es_cortina:
                    it.setFont(QFont("", -1, QFont.Bold))
                t.setItem(fila, col, it)
        reales = [x for x in self.tandas if not x.es_cortina]
        musica = sum(x.duracion for x in reales)
        texto = (f"{len(reales)} tandas, {len(self.tandas) - len(reales)} cortinas — música: "
                 f"{convertir_segundos(musica, 'x minutos y x segundos')}, estimado con cortinas: "
                 f"{convertir_segundos(musica + max(len(reales) - 1, 0) * 60, 'x minutos y x segundos')}")
        if avisos:
            texto += f" — <span style='background:#ffcdd2'>&nbsp;{avisos} con avisos (pasa el ratón por encima)&nbsp;</span>"
        self.resumen.setText(texto)
        if self.tandas:
            t.selectRow(0)

    def mostrar_canciones(self):
        filas = self.tabla_tandas.selectionModel().selectedRows()
        if not filas:
            return
        df = self.tandas[filas[0].row()].canciones
        self.tabla_canciones.setRowCount(len(df))
        for i, (_, c) in enumerate(df.iterrows()):
            for col, v in enumerate([c["title"], c["artist"], c["ano"], compositor_para_diapo(c["composer"]),
                                     convertir_segundos(c["duration"])]):
                it = QTableWidgetItem(str(v))
                it.setToolTip(f"{v}\n\n{c['ruta']}")
                self.tabla_canciones.setItem(i, col, it)

    def crear(self):
        d = self.datos()
        if not d["milonga"]:
            QMessageBox.warning(self, "Falta el nombre", "Escribe el nombre de la milonga.")
            return
        for clave, valor in (("diapos_nombre", d["milonga"]), ("diapos_inicio", d["inicio"]), ("diapos_fin", d["fin"])):
            self.settings.setValue(clave, valor)
        destino, _ = QFileDialog.getSaveFileName(
            self, "Guardar presentación", os.path.join(presentations_start_path, nombre_archivo(d)),
            "PowerPoint (*.pptx)")
        if not destino:
            return
        self.progreso.setMaximum(len(self.tandas))
        self.progreso.show()
        self.boton_crear.setEnabled(False)

        def progreso(hechas, total):
            self.progreso.setValue(hechas)
            QApplication.processEvents()

        try:
            crear_presentacion(self.tandas, d, destino, progreso)
        except PermissionError:
            QMessageBox.critical(self, "No se pudo guardar",
                                 "El archivo está abierto en PowerPoint. Ciérralo y vuelve a intentarlo.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear la presentación:\n{e}")
            return
        finally:
            self.progreso.hide()
            self.boton_crear.setEnabled(True)
        if QMessageBox.question(self, "Presentación creada", f"Guardada en:\n{destino}\n\n¿Abrirla ahora?") \
                == QMessageBox.Yes:
            os.startfile(destino)
