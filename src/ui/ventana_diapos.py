"""Ventana para crear la presentación de las tandas a partir de una playlist."""
import os

from PyQt5.QtCore import Qt, QDate, QTime, QSettings
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDateEdit, QTimeEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QSplitter,
    QApplication, QProgressBar, QListWidget, QListWidgetItem, QWidget, QComboBox, QSpinBox,
)

from src.config.config import m3u_start_path, presentations_start_path, default_milonga_data
from src.diapos.generador import (
    leer_playlist, agrupar_tandas, crear_presentacion, duracion_texto, nombre_archivo, compositor_para_diapo,
)
from src.diapos import bpm, caracter
from src.diapos.revision import (
    revisar, horas_de_inicio, ERROR, AVISO, AUTO, LIBRE, PATRONES, MINUTOS_SIN_MILONGA,
)
from src.utils.utils import convertir_segundos


def _texto_bpm(valor):
    try:
        return f"{float(valor):.0f}" if valor and float(valor) == float(valor) else ""
    except (TypeError, ValueError):
        return ""


class VentanaDiapos(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear diapos de las tandas")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1400, 800)
        self.settings = QSettings("TangoTags", "TangoTags")
        self.tandas = []
        self.faltan = []
        self.avisos = []
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
        # Reglas de la revisión (se recuerdan)
        self.patron = QComboBox()
        self.patron.addItem("Detectarlo", AUTO)
        for clave, (_, dibujo) in PATRONES.items():
            self.patron.addItem(f"{clave}  ({dibujo})", clave)
        self.patron.addItem("Libre (no mirar)", LIBRE)
        guardado = self.patron.findData(self.settings.value("diapos_patron", AUTO))
        self.patron.setCurrentIndex(max(guardado, 0))
        self.patron.currentIndexChanged.connect(self.cambiar_reglas)
        self.sin_milonga = QSpinBox()
        self.sin_milonga.setRange(0, 120)
        self.sin_milonga.setSingleStep(5)
        self.sin_milonga.setSuffix(" min")
        self.sin_milonga.setValue(int(self.settings.value("diapos_sin_milonga", MINUTOS_SIN_MILONGA)))
        self.sin_milonga.setToolTip("Al final de la noche no se ponen milongas (0 = no mirar)")
        self.sin_milonga.valueChanged.connect(self.cambiar_reglas)
        reglas = QHBoxLayout()
        reglas.addWidget(QLabel("<b>Patrón de bloques:</b>"))
        reglas.addWidget(self.patron)
        reglas.addSpacing(20)
        reglas.addWidget(QLabel("<b>Sin milonga los últimos</b>"))
        reglas.addWidget(self.sin_milonga)
        reglas.addStretch(1)
        editar_caracter = QPushButton("Editar tabla de carácter…")
        editar_caracter.setToolTip("Carácter, energía y dificultad de cada orquesta y época (se abre con Excel).\n"
                                   "Guarda y pulsa «Volver a revisar».")
        editar_caracter.clicked.connect(lambda: os.startfile(caracter.ARCHIVO))
        volver = QPushButton("↻ Volver a revisar")
        volver.clicked.connect(self.cambiar_reglas)
        reglas.addWidget(editar_caracter)
        reglas.addWidget(volver)
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
        lay.addLayout(reglas)

        fila = QHBoxLayout()
        self.boton_playlist = QPushButton("① Elegir playlist…")
        self.boton_playlist.clicked.connect(self.elegir_playlist)
        self.etiqueta_playlist = QLabel("<i>Ninguna playlist cargada</i>")
        fila.addWidget(self.boton_playlist)
        fila.addWidget(self.etiqueta_playlist, 1)
        lay.addLayout(fila)

        # --- Vista previa: tandas arriba, canciones de la tanda seleccionada abajo
        self.tabla_tandas = QTableWidget(0, 9)
        self.tabla_tandas.setHorizontalHeaderLabels(["#", "Tipo", "Título de la diapo", "Subtítulo", "Temas", "Duración",
                                                     "Empieza", "Carácter", "BPM"])
        self.tabla_tandas.verticalHeader().hide()
        self.tabla_tandas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_tandas.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_tandas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.tabla_tandas.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabla_tandas.itemSelectionChanged.connect(self.mostrar_canciones)

        self.tabla_canciones = QTableWidget(0, 6)
        self.tabla_canciones.setHorizontalHeaderLabels(["Título", "Artista", "Año", "Compositor (en la diapo)", "Duración",
                                                        "BPM"])
        self.tabla_canciones.verticalHeader().hide()
        self.tabla_canciones.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.tabla_canciones.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        # --- Revisión: lo que conviene mirar antes de crear la presentación (clic = ir a la tanda)
        self.lista_revision = QListWidget()
        self.lista_revision.itemClicked.connect(self.ir_a_aviso)
        caja_revision = QWidget()
        lay_revision = QVBoxLayout(caja_revision)
        lay_revision.setContentsMargins(0, 0, 0, 0)
        self.titulo_revision = QLabel("<b>Revisión</b>")
        lay_revision.addWidget(self.titulo_revision)
        lay_revision.addWidget(self.lista_revision)

        division = QSplitter(Qt.Vertical)
        division.addWidget(self.tabla_tandas)
        division.addWidget(self.tabla_canciones)
        division.addWidget(caja_revision)
        division.setSizes([450, 170, 170])
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
        if self.tandas:
            self.revisar()

    def cambiar_reglas(self):
        self.settings.setValue("diapos_patron", self.patron.currentData())
        self.settings.setValue("diapos_sin_milonga", self.sin_milonga.value())
        if self.tandas:
            self.revisar()

    def elegir_playlist(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elegir playlist", self.settings.value("dir_playlist_diapos", m3u_start_path) or m3u_start_path,
            "Playlists (*.m3u *.m3u8 *.mbp);;Todos (*.*)")
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
        self.faltan = faltan
        self.tandas = agrupar_tandas(canciones)
        self.etiqueta_playlist.setText(f"<b>{os.path.basename(ruta)}</b> — {len(canciones)} canciones")
        self.rellenar_tandas()
        self.boton_crear.setEnabled(bool(self.tandas))
        if faltan:
            QMessageBox.warning(self, "Canciones no encontradas",
                                f"{len(faltan)} canción(es) de la playlist no existen y no saldrán en las diapos:\n\n"
                                + "\n".join(faltan[:15]))
        self.calcular_bpm()

    def calcular_bpm(self):
        """BPM de las canciones de las tandas: los guardados al momento, los nuevos (~0,2 s cada uno) con barra."""
        try:
            cache = bpm.CacheBpm()
        except Exception:
            return
        pendientes = []
        for fila, tanda in enumerate(self.tandas):
            if tanda.es_cortina:
                continue
            tanda.canciones["bpm"] = None
            for idx, c in tanda.canciones.iterrows():
                encontrado, valor = cache.guardado(c["ruta"], c["genre"])
                if encontrado:
                    tanda.canciones.at[idx, "bpm"] = valor
                else:
                    pendientes.append((fila, idx))
        if pendientes:
            self.progreso.setMaximum(len(pendientes))
            self.progreso.setFormat("Calculando BPM… %v de %m")
            self.progreso.show()
            for n, (fila, idx) in enumerate(pendientes, 1):
                c = self.tandas[fila].canciones.loc[idx]
                self.tandas[fila].canciones.at[idx, "bpm"] = cache.bpm(c["ruta"], c["genre"])
                self.progreso.setValue(n)
                QApplication.processEvents()
            self.progreso.hide()
            self.progreso.setFormat("%p%")
        for fila, tanda in enumerate(self.tandas):
            if not tanda.es_cortina:
                valores = [v for v in tanda.canciones["bpm"] if v]
                texto = "" if not valores else (f"{min(valores):.0f}" if min(valores) == max(valores)
                                                else f"{min(valores):.0f}–{max(valores):.0f}")
                self.tabla_tandas.item(fila, 8).setText(texto)
        self.revisar()
        self.mostrar_canciones()

    def rellenar_tandas(self):
        t = self.tabla_tandas
        t.setRowCount(len(self.tandas))
        n_tanda = 0
        for fila, tanda in enumerate(self.tandas):
            es_tanda = not tanda.es_cortina and not tanda.es_cumparsita
            if es_tanda:
                n_tanda += 1
            valores = [str(n_tanda) if es_tanda else "",
                       "Cortina" if tanda.es_cortina else "Final" if tanda.es_cumparsita else tanda.genero.capitalize(),
                       tanda.titulo_orquesta, tanda.subtitulo, str(len(tanda.canciones)),
                       convertir_segundos(tanda.duracion), "", "", ""]
            for col, v in enumerate(valores):
                it = QTableWidgetItem(v)
                if col == 2 and not tanda.es_cortina:
                    it.setFont(QFont("", -1, QFont.Bold))
                t.setItem(fila, col, it)
        self.revisar()
        if self.tandas:
            t.selectRow(0)

    def revisar(self):
        """Revisa la playlist, colorea las filas con problemas y llena la lista de la revisión."""
        d = self.datos()
        self.avisos = revisar(self.tandas, self.faltan, d["inicio"], d["fin"], patron=self.patron.currentData(),
                              minutos_sin_milonga=self.sin_milonga.value())
        por_fila = {}
        for a in self.avisos:
            if a.fila is not None:
                por_fila.setdefault(a.fila, []).append(a)
        colores = {ERROR: QColor("#ffcdd2"), AVISO: QColor("#fff3c4")}
        horas = horas_de_inicio(self.tandas, d["inicio"])
        for fila, tanda in enumerate(self.tandas):
            suyos = por_fila.get(fila, [])
            niveles = {a.nivel for a in suyos}
            nivel = ERROR if ERROR in niveles else AVISO if AVISO in niveles else None
            color = colores.get(nivel, QColor("#eeeeee") if tanda.es_cortina else QColor("#ffffff"))
            self.tabla_tandas.item(fila, 6).setText(horas[fila])
            car = None if tanda.es_cumparsita else caracter.de_tanda(tanda)
            self.tabla_tandas.item(fila, 7).setText(car.texto if car else "")
            for col in range(self.tabla_tandas.columnCount()):
                it = self.tabla_tandas.item(fila, col)
                it.setBackground(color)
                it.setToolTip("\n".join(a.texto for a in suyos) if suyos else it.text())
            if car and not suyos:
                self.tabla_tandas.item(fila, 7).setToolTip(
                    f"{car.texto}, dificultad {car.dificultad}" + (f"\n{car.notas}" if car.notas else ""))

        self.lista_revision.clear()
        iconos = {ERROR: "❌", AVISO: "⚠", "info": "ℹ"}
        for a in self.avisos:
            item = QListWidgetItem(f"{iconos[a.nivel]}  {a.texto}")
            item.setData(Qt.UserRole, a.fila)
            if a.nivel in colores:
                item.setBackground(colores[a.nivel])
            self.lista_revision.addItem(item)
        errores = sum(a.nivel == ERROR for a in self.avisos)
        avisos = sum(a.nivel == AVISO for a in self.avisos)
        if not self.avisos:
            self.lista_revision.addItem("✔  Todo bien")
        self.titulo_revision.setText(f"<b>Revisión</b> — {errores} error(es), {avisos} aviso(s)"
                                     + ("" if errores or avisos else " ✔"))

        reales = [x for x in self.tandas if not x.es_cortina]
        musica = sum(x.duracion for x in reales)
        texto = (f"{len(reales)} tandas, {len(self.tandas) - len(reales)} cortinas — música: "
                 f"{convertir_segundos(musica, 'x minutos y x segundos')}, estimado con cortinas: "
                 f"{convertir_segundos(musica + max(len(reales) - 1, 0) * 60, 'x minutos y x segundos')}")
        if errores:
            texto += f" — <span style='background:#ffcdd2'>&nbsp;{errores} error(es): mira la revisión&nbsp;</span>"
        self.resumen.setText(texto)

    def ir_a_aviso(self, item):
        fila = item.data(Qt.UserRole)
        if fila is not None:
            self.tabla_tandas.selectRow(fila)
            self.tabla_tandas.scrollToItem(self.tabla_tandas.item(fila, 0))

    def mostrar_canciones(self):
        filas = self.tabla_tandas.selectionModel().selectedRows()
        if not filas:
            return
        df = self.tandas[filas[0].row()].canciones
        self.tabla_canciones.setRowCount(len(df))
        for i, (_, c) in enumerate(df.iterrows()):
            for col, v in enumerate([c["title"], c["artist"], c["ano"], compositor_para_diapo(c["composer"]),
                                     convertir_segundos(c["duration"]), _texto_bpm(c.get("bpm"))]):
                it = QTableWidgetItem(str(v))
                it.setToolTip(f"{v}\n\n{c['ruta']}")
                self.tabla_canciones.setItem(i, col, it)

    def crear(self):
        d = self.datos()
        if not d["milonga"]:
            QMessageBox.warning(self, "Falta el nombre", "Escribe el nombre de la milonga.")
            return
        errores = [a.texto for a in self.avisos if a.nivel == ERROR]
        if errores and QMessageBox.question(
                self, "La playlist tiene errores",
                f"La revisión encontró {len(errores)} error(es):\n\n" + "\n".join(errores[:10])
                + ("\n…" if len(errores) > 10 else "") + "\n\n¿Crear la presentación igualmente?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
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
