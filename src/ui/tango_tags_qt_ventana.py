"""
Ventana principal de TangoTags.

Flujo de trabajo (de izquierda a derecha en la barra de herramientas):
    1. CARGAR   canciones (archivos, carpeta, playlist o biblioteca de MusicBee)
    2. REVISAR  la tabla: a la izquierda las tags del archivo, a la derecha las
                coincidencias de la base de datos. Marca "Usar" en la buena.
    3. APLICAR  las tags marcadas (se muestra antes/después y se pide confirmación)
    4. DIAPOS   crear la presentación de las tandas / controlar las diapos en la milonga
"""
import os
import subprocess

import pandas as pd
import pygame
from PyQt5.QtCore import Qt, QSize, QSettings, QThread, QEvent, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QBrush, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QToolBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QHeaderView, QDialog, QPushButton, QFileDialog, QLineEdit, QCheckBox,
    QFrame, QMessageBox, QProgressBar, QApplication, QStyle, QToolButton, QDialogButtonBox,
    QAbstractItemView, QInputDialog,
)

import re

import src.utils.utils as utils
from src.config.config import (
    icon_paths, m3u_start_path, musicbee_start_folder, dropbox_path, residuos,
    DEFAULT_DATE_CHECKED,
)
from src.config.database import Database
from src.motor.emparejar import (
    Motor, Cancion, NOMBRE_CAMPO, categoria_de, tags_actuales, texto, ya_revisada, cambios_de,
    contexto_disco, leer_tags_lista,
)
from src.utils.MusicBeeLibraryTools import MusicBeeLibraryTools
from src.utils import historial, no_tocar
from src.ui.reproductor import Reproductor, BarraSonando
from src.utils.formato_tags import (
    tags_desde_coincidencia, combinar_compositor, formatear_cantores, formatear_fecha, formatear_estilo,
    normalizar_compositor_autor, formatear_titulo,
)

EXTENSIONES_AUDIO = (".mp3", ".flac", ".m4a", ".wav", ".aif", ".aiff", ".wma", ".ogg")

# ---- Columnas de la tabla ------------------------------------------------------------
COL_ESTADO, COL_TITULO, COL_ARTISTA, COL_ANO, COL_GENERO, COL_COMPOSITOR, COL_PLAY, \
    COL_USAR, COL_BD_TITULO, COL_BD_ORQUESTA, COL_BD_CANTOR, COL_BD_FECHA, COL_BD_ESTILO, \
    COL_BD_COMPOSITOR, COL_BD_PLAY30, COL_BD_PLAY10 = range(16)

CABECERAS = ["Estado", "Título", "Artista", "Año", "Género", "Compositor", "▶",
             "Usar", "Título BD", "Orquesta BD", "Cantor BD", "Fecha BD", "Estilo BD",
             "Compositor BD", "▶30s", "▶10s"]

COLUMNAS_ARCHIVO = range(COL_ESTADO, COL_PLAY + 1)

# Columna de la tabla -> (columna en la base de datos, función que la deja en formato final)
COLUMNAS_BD = {
    COL_BD_TITULO: ("titulo", formatear_titulo),
    COL_BD_ORQUESTA: ("artista", formatear_titulo),
    COL_BD_CANTOR: ("cantor", formatear_cantores),
    COL_BD_FECHA: ("fecha", formatear_fecha),
    COL_BD_ESTILO: ("estilo", formatear_estilo),
    COL_BD_COMPOSITOR: ("compositor_autor", normalizar_compositor_autor),
}

# Columna de la tabla -> nombre del color que calcula coincidencias_a_colores()
COLORES_COLUMNA = {
    COL_BD_TITULO: "TITULO", COL_BD_ORQUESTA: "ORQUESTA", COL_BD_CANTOR: "CANTOR",
    COL_BD_FECHA: "FECHA", COL_BD_ESTILO: "ESTILO", COL_BD_COMPOSITOR: "COMPOSITOR",
}
COLORES_SUAVES = {"lightgreen": "#c8e6c9", "yellow": "#fff59d", "orange": "#ffcc80",
                  "red": "#ef9a9a", "grey": "#e0e0e0"}

# ---- Categorías de cada archivo tras buscarlo en la base de datos ------------------------
CATEGORIAS = {
    # clave: (texto en la columna Estado, texto del filtro, explicación)
    "perfecta": ("✔ Perfecta", "Perfectas", "Las tags ya coinciden con la base de datos: no se tocan"),
    "preferida": ("★ Sugerida", "Con sugerencia", "Hay una coincidencia clara, ya marcada en 'Usar'"),
    "dudosa": ("? Elegir", "Hay que elegir", "Varias opciones posibles: marca tú la buena"),
    "sin_titulo": ("✖ Sin título", "Título no encontrado", "El artista está en la BD pero el título no"),
    "sin_artista": ("✖ Sin artista", "Artista no encontrado", "El artista no está en la BD"),
}

TEXTO_AYUDA = """
<h3>Cómo se usa TangoTags</h3>
<ol>
<li><b>Cargar</b>: elige canciones con <i>Archivos</i>, <i>Carpeta</i>, <i>Playlist</i> (.m3u)
o <i>MusicBee</i> (archivo .mbl de la biblioteca).</li>
<li><b>Revisar</b>: a la izquierda están las tags actuales del archivo; a la derecha las
coincidencias encontradas en la base de datos, <u>ya con el formato final</u>.
Los colores indican cuánto se parece cada campo
(<span style="background:#c8e6c9">igual</span>, <span style="background:#fff59d">parecido</span>,
<span style="background:#ffcc80">parcial</span>, <span style="background:#ef9a9a">distinto</span>).
<ul>
<li>Marca la casilla <b>Usar</b> de la coincidencia correcta (solo una por canción).
Las sugeridas ya vienen marcadas.</li>
<li>Puedes <b>editar</b> cualquier celda de la parte BD antes de aplicar.</li>
<li>Si no hay coincidencias, haz <b>doble clic</b> en la parte BD para buscar a mano. El buscador (Ctrl+F) usa una sola caja: palabras en cualquier orden, años como 1944, 1940-1945 o 1940s; puede quedarse abierto y sigue a la canción seleccionada. Si ves un error en la base de datos, <i>Corregir datos…</i> en su ficha.</li>
<li>Al marcar una opción, lo que va a cambiar en tu archivo sale en <span style='background:#fff59d'>amarillo</span> como «antes → después».</li>
<li>Doble clic en la parte del archivo (o tecla E, o <i>Editar a mano</i>): escribir las tags a mano, con el formato correcto, copia y deshacer.</li>
<li>Clic derecho en la cabecera de la tabla: ocultar/mostrar columnas; arrastra los bordes para cambiar anchos (se recuerdan).</li>
<li>Clic en ▶ para escuchar (no cambia la fila seleccionada). Lo que suena se ve en verde con ■; clic otra vez para parar, o <b>■ Parar</b> abajo a la derecha, o Esc.</li>
</ul></li>
<li><b>Aplicar tags</b>: muestra el antes/después de cada archivo y pide confirmación.
Antes de escribir se guarda una copia de las tags anteriores: <b>Deshacer</b> (Ctrl+Z) las
vuelve a poner, y <i>Archivo → Historial de cambios</i> permite deshacer cambios más antiguos.
Si cargaste desde MusicBee, después haz en MusicBee <i>Herramientas → Volver a leer tags</i>.</li>
<li><b>Diapos</b>: <i>Crear diapos</i> genera la presentación de las tandas a partir de una playlist
(con vista previa de las tandas; las que mezclan orquestas salen en rojo);
<i>Control diapos</i> va pasando las diapos durante la milonga.</li>
</ol>
<p><b>Teclado</b> en la tabla: 1–9 elegir · 0 ninguna · Espacio escuchar · S siguiente por decidir · X no tocar.</p>
<p><b>Archivo</b>: Estado de la colección, Duplicados, Grafías de nombres, Canciones «No tocar», Historial de cambios.</p>
<p>Al cargar se <b>saltan las canciones ya revisadas</b> (compositor con formato
<i>Musica: … - Letra: …</i>). Se puede desactivar en <i>Opciones</i>.
<i>Cancelar</i> (abajo a la derecha) para una carga o una escritura larga.</p>
<h4>Formato de las tags</h4>
<table cellpadding=3>
<tr><td><b>Artista</b></td><td>Orquesta / Cantor &nbsp; (varios: A y B)</td></tr>
<tr><td><b>Fecha</b></td><td>AAAA-MM-DD &nbsp; (o AAAA si solo se sabe el año)</td></tr>
<tr><td><b>Género</b></td><td>tango, tango vals, tango milonga…</td></tr>
<tr><td><b>Compositor</b></td><td>Musica: X - Letra: Y &nbsp; (siempre; ? si no se sabe)</td></tr>
</table>
<p>Si un dato no se conoce en la base de datos, esa tag del archivo no se toca. El compositor se escribe siempre: <i>Musica: ? - Letra: ?</i> indica que la canción ya pasó por la base de datos.</p>
"""


MENSAJE_INICIAL = ("<p style='font-size:15px; color:#555'>Empieza cargando canciones con los botones de "
                   "<b>① Cargar</b> (arriba a la izquierda).<br>Menú <b>Ayuda</b> para ver cómo funciona.</p>")

class tango_tags_qt_ventana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_store = Database()
        self.settings = QSettings("TangoTags", "TangoTags")
        self.archivos = []          # Cancion (motor) cargadas
        self.fila_a_archivo = {}    # fila de la tabla -> (archivo, posición de la coincidencia o None)
        self._rellenando = False

        self.setWindowTitle("TangoTags")
        self.setWindowIcon(QIcon(icon_paths["musicbee"]))
        self.resize(1700, 850)

        self.crear_menus()
        self.crear_barra_herramientas()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 0)
        layout.addWidget(self.crear_barra_filtros())
        self.tabla = self.crear_tabla()
        layout.addWidget(self.tabla, 1)
        self.mensaje_inicial = QLabel(MENSAJE_INICIAL)
        self.mensaje_inicial.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mensaje_inicial, 1)
        self.tabla.hide()
        self.setCentralWidget(central)

        self.reproductor = Reproductor(self)
        self.reproductor.cambiado.connect(self.pintar_sonando)
        self.reproductor.error.connect(lambda m: QMessageBox.warning(self, "No se puede reproducir", m))
        self.statusBar().addPermanentWidget(BarraSonando(self.reproductor))
        self.etiqueta_biblioteca = QLabel("")
        self.etiqueta_biblioteca.setStyleSheet("color:#555; padding:0 8px;")
        self.statusBar().addPermanentWidget(self.etiqueta_biblioteca)
        self._hilo_biblioteca = None
        self._biblioteca = None
        self.celdas_audio = {}      # (fila, col) -> (clave, ruta, descripción, fondo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.boton_cancelar = QPushButton("Cancelar")
        self.boton_cancelar.setToolTip("Parar la operación en curso (lo hecho hasta ahora se mantiene)")
        self.boton_cancelar.clicked.connect(self.cancelar)
        self.boton_cancelar.hide()
        self.statusBar().addPermanentWidget(self.boton_cancelar)
        self._cancelado = False
        self.statusBar().showMessage("Listo")

    # ------------------------------------------------------------------ construcción UI
    def icono(self, nombre=None, estandar=None):
        if nombre:
            return QIcon(icon_paths[nombre])
        return self.style().standardIcon(estandar)

    def accion(self, texto_boton, icono, funcion, ayuda, atajo=None):
        a = QAction(icono, texto_boton, self)
        a.setToolTip(f"<b>{texto_boton.replace(chr(10), ' ')}</b><br>{ayuda}")
        a.setStatusTip(ayuda)
        a.triggered.connect(funcion)
        if atajo:
            a.setShortcut(atajo)
        return a

    def crear_barra_herramientas(self):
        tb = QToolBar("Herramientas")
        tb.setMovable(False)
        tb.setIconSize(QSize(28, 28))
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(tb)

        def titulo_seccion(t):
            lbl = QLabel(t)
            lbl.setStyleSheet("font-weight:bold; color:#444; padding:0 6px 0 10px;")
            tb.addWidget(lbl)

        titulo_seccion("① Cargar")
        tb.addAction(self.accion("Archivos", self.icono("archivo"), self.cargar_archivos,
                                 "Elegir uno o varios archivos de música", "Ctrl+O"))
        tb.addAction(self.accion("Carpeta", self.icono("directorio"), self.cargar_carpeta,
                                 "Cargar todas las canciones de una carpeta (y subcarpetas)"))
        tb.addAction(self.accion("Playlist", self.icono("playlist"), self.cargar_playlist,
                                 "Cargar las canciones de una playlist .m3u / .m3u8"))
        tb.addAction(self.accion("MusicBee", self.icono("musicbee"), self.cargar_musicbee,
                                 "Cargar una biblioteca de MusicBee (.mbl)"))
        tb.addSeparator()

        titulo_seccion("② Revisar")
        tb.addAction(self.accion("Marcar\nsugeridas", self.icono(estandar=QStyle.SP_DialogApplyButton),
                                 self.marcar_sugeridas, "Marcar 'Usar' en todas las coincidencias sugeridas"))
        tb.addAction(self.accion("Marcar\npor disco", self.icono(estandar=QStyle.SP_DriveCDIcon), self.marcar_por_disco,
                                 "En las canciones en las que hay que elegir, marcar la opción cuya fecha encaja con "
                                 "las demás canciones del mismo disco (solo si encaja una)"))
        tb.addAction(self.accion("Desmarcar\ntodo", self.icono(estandar=QStyle.SP_DialogResetButton),
                                 self.desmarcar_todo, "Quitar todas las marcas de 'Usar'"))
        tb.addAction(self.accion("Editar\na mano", self.icono(estandar=QStyle.SP_FileDialogDetailedView), self.editar_a_mano,
                                 "Escribir a mano las tags de la canción seleccionada (para las que no están en la BD). "
                                 "También con doble clic en la parte del archivo o la tecla E"))
        tb.addAction(self.accion("No\ntocar", self.icono(estandar=QStyle.SP_DialogNoButton), self.marcar_no_tocar,
                                 "Dejar la canción seleccionada como está y no volver a enseñarla al cargar "
                                 "(Archivo → Canciones «No tocar» para deshacerlo). Tecla X"))
        tb.addAction(self.accion("Buscar\nen BD", self.icono("searchdb"), self.buscar_en_bd,
                                 "Buscar en la base de datos. Si hay una canción seleccionada, "
                                 "puedes asignarle el resultado", "Ctrl+F"))
        tb.addAction(self.accion("Parar\nmúsica", self.icono(estandar=QStyle.SP_MediaStop), self.stop_music,
                                 "Detener la reproducción", "Esc"))
        tb.addSeparator()

        titulo_seccion("③ Aplicar")
        aplicar = self.accion("Aplicar\ntags", self.icono(estandar=QStyle.SP_DialogSaveButton), self.aplicar_tags,
                              "Escribir en los archivos las tags marcadas en 'Usar' "
                              "(antes se muestra un resumen para confirmar)", "Ctrl+S")
        tb.addAction(aplicar)
        tb.widgetForAction(aplicar).setStyleSheet("QToolButton{font-weight:bold; color:#1b5e20;}")
        tb.addAction(self.accion("Deshacer", self.icono(estandar=QStyle.SP_ArrowBack), self.deshacer_ultimo,
                                 "Volver a poner las tags que había antes del último 'Aplicar tags'", "Ctrl+Z"))
        tb.addSeparator()

        titulo_seccion("④ Diapos")
        tb.addAction(self.accion("Crear\ndiapos", self.icono("presentacion"), self.abrir_crear_diapos,
                                 "Crear la presentación PowerPoint de las tandas a partir de una playlist"))
        tb.addAction(self.accion("Control\ndiapos", self.icono(estandar=QStyle.SP_MediaPlay),
                                 self.abrir_control_diapos,
                                 "Durante la milonga: pasa las diapos según la canción que suena"))
        tb.addSeparator()
        tb.addAction(self.accion("Limpiar", self.icono("trash"), self.borrar_todo,
                                 "Vaciar la lista de canciones cargadas"))

    def crear_menus(self):
        mb = self.menuBar()
        m_archivo = mb.addMenu("&Archivo")
        m_archivo.addAction("Cargar archivos…", self.cargar_archivos)
        m_archivo.addAction("Cargar carpeta…", self.cargar_carpeta)
        m_archivo.addAction("Cargar playlist…", self.cargar_playlist)
        m_archivo.addAction("Cargar MusicBee…", self.cargar_musicbee)
        m_archivo.addSeparator()
        m_archivo.addAction("Deshacer último cambio de tags", self.deshacer_ultimo)
        m_archivo.addAction("Historial de cambios…", self.historial_cambios)
        m_archivo.addAction("Abrir carpeta de copias de seguridad", self.abrir_carpeta_backups)
        m_archivo.addSeparator()
        m_archivo.addAction("Regenerar base de datos limpia (desde mergeddb.csv)…", self.regenerar_bd)
        m_archivo.addAction("Canciones marcadas «No tocar»…", self.ver_no_tocar)
        m_archivo.addAction("Grafías de nombres (di Sarli / Di Sarli…)…", self.editar_grafias)
        m_archivo.addSeparator()
        m_archivo.addAction("Estado de la colección…", self.abrir_estado)
        m_archivo.addAction("Actualizar la biblioteca ahora", self.actualizar_biblioteca)
        m_archivo.addAction("Carpetas de la biblioteca…", self.editar_carpetas)
        m_archivo.addAction("Duplicados…", lambda: self.abrir_duplicados([]))
        m_archivo.addAction("Reparar playlists…", self.abrir_reparar_playlists)
        m_archivo.addSeparator()
        m_archivo.addAction("Salir", self.close)

        m_opciones = mb.addMenu("&Opciones")
        self.opt_saltar = m_opciones.addAction("Saltar las canciones ya revisadas (compositor 'Musica: … - Letra: …')")
        self.opt_saltar.setCheckable(True)
        self.opt_saltar.setChecked(self.settings.value("opt_saltar", True, type=bool))
        self.opt_no_tocar = m_opciones.addAction("Ocultar las canciones marcadas «No tocar»")
        self.opt_no_tocar.setCheckable(True)
        self.opt_no_tocar.setChecked(self.settings.value("opt_no_tocar", True, type=bool))
        m_opciones.addSeparator()
        self.opt_fecha = m_opciones.addAction("Usar la fecha del archivo para elegir la sugerida")
        self.opt_fecha.setCheckable(True)
        self.opt_fecha.setChecked(self.settings.value("opt_fecha", DEFAULT_DATE_CHECKED, type=bool))
        self.opt_fecha.toggled.connect(lambda _: self.actualizar_biblioteca())
        self.opt_guardar_coinc = m_opciones.addAction("Guardar CSV de coincidencias al cargar (carpeta output)")
        self.opt_guardar_coinc.setCheckable(True)
        self.opt_guardar_coinc.setChecked(self.settings.value("opt_guardar_coinc", False, type=bool))
        self.opt_guardar_resid = m_opciones.addAction("Guardar CSV de residuos de títulos al cargar")
        self.opt_guardar_resid.setCheckable(True)
        self.opt_guardar_resid.setChecked(self.settings.value("opt_guardar_resid", False, type=bool))

        m_ayuda = mb.addMenu("A&yuda")
        m_ayuda.addAction("Cómo se usa…", self.mostrar_ayuda, "F1")

    def crear_barra_filtros(self):
        barra = QFrame()
        lay = QHBoxLayout(barra)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.addWidget(QLabel("<b>Mostrar:</b>"))
        self.filtros = {}
        for clave, (_, nombre, explicacion) in CATEGORIAS.items():
            cb = QCheckBox(nombre)
            cb.setChecked(self.settings.value(f"mostrar_{clave}", clave != "perfecta", type=bool))
            cb.setToolTip(explicacion)
            cb.stateChanged.connect(self.rellenar_tabla)
            self.filtros[clave] = cb
            lay.addWidget(cb)
        lay.addStretch(1)
        teclas = QLabel("Teclado: <b>1–9</b> elegir · <b>0</b> ninguna · <b>Espacio</b> escuchar · "
                        "<b>S</b> siguiente por decidir · <b>X</b> no tocar · <b>E</b> editar a mano")
        teclas.setStyleSheet("color:#666;")
        lay.addWidget(teclas)
        lay.addSpacing(20)
        lay.addWidget(QLabel("Colores:"))
        for nombre, color in (("igual", "lightgreen"), ("parecido", "yellow"),
                              ("parcial", "orange"), ("distinto", "red")):
            lbl = QLabel(f" {nombre} ")
            lbl.setStyleSheet(f"background:{COLORES_SUAVES[color]}; border-radius:3px;")
            lay.addWidget(lbl)
        return barra

    def crear_tabla(self):
        t = QTableWidget(0, len(CABECERAS))
        t.setHorizontalHeaderLabels(CABECERAS)
        t.verticalHeader().hide()
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked)
        t.setWordWrap(False)
        cabecera_bd = QColor("#e3f2fd")
        for col in range(COL_USAR, len(CABECERAS)):
            t.horizontalHeaderItem(col).setBackground(cabecera_bd)
            t.horizontalHeaderItem(col).setToolTip("Datos de la base de datos (con el formato final). "
                                                   "Clic derecho: ocultar/mostrar columnas")
        from src.ui.columnas import preparar_columnas
        preparar_columnas(t, "principal", {
            COL_ESTADO: 165, COL_TITULO: 190, COL_ARTISTA: 210, COL_ANO: 95, COL_GENERO: 95, COL_COMPOSITOR: 230,
            COL_PLAY: 32, COL_USAR: 56, COL_BD_TITULO: 190, COL_BD_ORQUESTA: 160, COL_BD_CANTOR: 160,
            COL_BD_FECHA: 95, COL_BD_ESTILO: 100, COL_BD_COMPOSITOR: 330, COL_BD_PLAY30: 42, COL_BD_PLAY10: 42,
        }, siempre_visibles={COL_ESTADO, COL_USAR, COL_BD_TITULO})
        t.viewport().installEventFilter(self)
        t.installEventFilter(self)          # teclado: 1-9, 0, Espacio, S, X
        t.itemChanged.connect(self.on_item_changed)
        t.itemSelectionChanged.connect(self.seleccion_cambiada)
        t.cellDoubleClicked.connect(self.on_cell_double_clicked)
        return t

    # ------------------------------------------------------------------ progreso
    def empezar_progreso(self, total):
        self._cancelado = False
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.boton_cancelar.show()

    def terminar_progreso(self):
        self.progress_bar.hide()
        self.boton_cancelar.hide()

    def cancelar(self):
        self._cancelado = True
        self.statusBar().showMessage("Cancelando…")

    # ------------------------------------------------------------------ carga
    def ultima_carpeta(self, clave, defecto):
        return self.settings.value(clave, defecto) or defecto

    def cargar_archivos(self):
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Elegir archivos de música", self.ultima_carpeta("dir_archivos", dropbox_path),
            "Audio (" + " ".join("*" + e for e in EXTENSIONES_AUDIO) + ");;Todos (*.*)")
        if rutas:
            self.settings.setValue("dir_archivos", os.path.dirname(rutas[0]))
            self.procesar_archivos([(r, None) for r in rutas], origen="archivos")

    def cargar_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(
            self, "Elegir carpeta de música", self.ultima_carpeta("dir_carpeta", dropbox_path))
        if not carpeta:
            return
        self.settings.setValue("dir_carpeta", carpeta)
        rutas = []
        for raiz, _, ficheros in os.walk(carpeta):
            rutas += [os.path.join(raiz, f) for f in sorted(ficheros) if f.lower().endswith(EXTENSIONES_AUDIO)]
        if not rutas:
            QMessageBox.information(self, "Carpeta vacía", "No hay archivos de música en esa carpeta.")
            return
        self.procesar_archivos([(r, None) for r in rutas], origen=carpeta)

    def cargar_playlist(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elegir playlist", self.ultima_carpeta("dir_playlist", m3u_start_path),
            "Playlists (*.m3u *.m3u8);;Todos (*.*)")
        if not ruta:
            return
        self.settings.setValue("dir_playlist", os.path.dirname(ruta))
        rutas = []
        for linea in utils.load_m3u_file_helper(ruta):
            if not os.path.exists(linea) and "Dropbox" in linea:
                # La playlist se creó en otro ordenador: rehacer la ruta con el Dropbox de este
                alternativa = os.path.join(dropbox_path, linea.split("Dropbox", 1)[1].lstrip("\\/"))
                if os.path.exists(alternativa):
                    linea = alternativa
            rutas.append((linea, None))
        self.procesar_archivos(rutas, origen=ruta)

    def cargar_musicbee(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elegir biblioteca de MusicBee", self.ultima_carpeta("dir_musicbee", musicbee_start_folder),
            "Biblioteca MusicBee (*.mbl);;Todos (*.*)")
        if not ruta:
            return
        self.settings.setValue("dir_musicbee", os.path.dirname(ruta))
        self.statusBar().showMessage("Leyendo biblioteca de MusicBee…")
        self.progress_bar.setMaximum(0)   # barra "ocupada" sin porcentaje
        self.progress_bar.show()
        hilo = EnSegundoPlano(lambda: MusicBeeLibraryTools(None, ruta).library_df)
        hilo.start()
        while hilo.isRunning():
            QApplication.processEvents()
            hilo.wait(50)
        self.progress_bar.hide()
        if hilo.error is not None:
            QMessageBox.critical(self, "Error", f"No se pudo leer la biblioteca:\n{hilo.error}")
            return
        biblioteca = hilo.resultado
        columnas = ['title', 'artist', 'year', 'genre', 'composer', 'file_path']
        rutas = [(fila[-1], fila) for fila in biblioteca[columnas].values.tolist()]
        self.procesar_archivos(rutas, origen=ruta)

    def procesar_archivos(self, rutas_y_tags, origen):
        """rutas_y_tags: lista de (ruta, tags de MusicBee o None para leerlas del archivo)."""
        self.borrar_todo()
        utils.guardar_residuos = self.opt_guardar_resid.isChecked()
        residuos.clear()
        no_encontrados = []
        favoritas = []
        saltadas = 0
        ocultas_no_tocar = 0
        marcadas_no_tocar = no_tocar.claves() if self.opt_no_tocar.isChecked() else set()

        motor = Motor(usar_fecha=self.opt_fecha.isChecked())
        self.empezar_progreso(len(rutas_y_tags))
        try:
            for i, (ruta, tags) in enumerate(rutas_y_tags, 1):
                if self._cancelado:
                    break
                self.progress_bar.setValue(i)
                self.statusBar().showMessage(f"Buscando en la base de datos… {i} de {len(rutas_y_tags)}")
                QApplication.processEvents()
                if not os.path.exists(ruta):
                    no_encontrados.append(ruta)
                    continue
                if marcadas_no_tocar and no_tocar.esta(ruta, marcadas_no_tocar):
                    ocultas_no_tocar += 1
                    continue
                if tags is None:
                    tags = leer_tags_lista(ruta)
                if self.opt_saltar.isChecked() and tags is not None and ya_revisada(tags[4]):
                    saltadas += 1
                    continue
                try:
                    archivo = motor.emparejar(ruta, tags)
                except Exception as e:
                    print(f"Error procesando {ruta}: {e}")
                    no_encontrados.append(ruta)
                    continue
                self.archivos.append(archivo)
                if self.opt_guardar_coinc.isChecked():
                    fav = archivo.get_coincidencia_favorita()
                    if fav is not None:
                        favoritas.append(fav)
        finally:
            self.terminar_progreso()

        if favoritas:
            utils.guardar_archivo_output(tipo='coincidencias', dataframe=pd.concat(favoritas, ignore_index=True))
        if self.opt_guardar_resid.isChecked() and residuos:
            utils.guardar_archivo_output(
                tipo='residuos', encabezados=f"Origen: {origen}\n",
                dataframe=pd.DataFrame(residuos, columns=['Titulo Archivo', 'Titulo base de datos',
                                                          'Residuo', 'Ruta completa']))

        self.calcular_contexto_disco()
        self.actualizar_contadores()
        self.rellenar_tabla()
        resumen = self.resumen()
        if saltadas:
            resumen += f" — {saltadas} saltadas por estar ya revisadas (Opciones para cambiarlo)"
        if ocultas_no_tocar:
            resumen += f" — {ocultas_no_tocar} marcadas «No tocar»"
        self.statusBar().showMessage(f"{os.path.basename(origen) or origen}: {resumen}")
        if saltadas and not self.archivos:
            self.mensaje_inicial.setText(
                f"<p style='font-size:15px; color:#555'>Las {saltadas} canciones ya estaban revisadas "
                f"(tienen el compositor con formato <i>Musica: … - Letra: …</i>).<br>"
                f"Para verlas igualmente, desmarca <b>Opciones → Saltar las canciones ya revisadas</b>.</p>")
        if no_encontrados:
            QMessageBox.warning(
                self, "Archivos no encontrados",
                f"{len(no_encontrados)} archivo(s) no existen o no se pudieron leer:\n\n"
                + "\n".join(no_encontrados[:15]) + ("\n…" if len(no_encontrados) > 15 else ""))

    def calcular_contexto_disco(self):
        contexto_disco(self.archivos)

    def marcar_por_disco(self):
        marcadas = 0
        for a in self.archivos:
            d = getattr(a, "disco", None)
            if a.categoria == "dudosa" and d and len(d["encajan"]) == 1 and a.seleccion is None:
                a.seleccion = next(iter(d["encajan"]))
                marcadas += 1
        self.rellenar_tabla()
        QMessageBox.information(
            self, "Marcar por disco",
            f"Marcadas {marcadas} canción(es) en las que solo una opción encaja con los años del resto del disco "
            "(💿 en la columna Usar).\n\nRevísalas antes de aplicar: es una pista, no una certeza."
            if marcadas else "No hay canciones en las que solo una opción encaje con los años del disco.")

    def resumen(self):
        if not self.archivos:
            return "ninguna canción para revisar"
        cuenta = pd.Series([a.categoria for a in self.archivos]).value_counts()
        partes = [f"{cuenta.get(k, 0)} {CATEGORIAS[k][1].lower()}" for k in CATEGORIAS if cuenta.get(k, 0)]
        return f"{len(self.archivos)} canciones — " + ", ".join(partes)

    def actualizar_contadores(self):
        cuenta = pd.Series([a.categoria for a in self.archivos], dtype=object).value_counts()
        for clave, cb in self.filtros.items():
            cb.setText(f"{CATEGORIAS[clave][1]} ({cuenta.get(clave, 0)})")

    def borrar_todo(self):
        self.celdas_audio = {}
        self.archivos = []
        self.fila_a_archivo = {}
        self.tabla.setRowCount(0)
        self.tabla.hide()
        self.mensaje_inicial.setText(MENSAJE_INICIAL)
        self.mensaje_inicial.show()
        self.actualizar_contadores()

    # ------------------------------------------------------------------ tabla
    def rellenar_tabla(self):
        for clave, cb in self.filtros.items():
            self.settings.setValue(f"mostrar_{clave}", cb.isChecked())
        if not self.archivos:
            return
        visibles = [a for a in self.archivos if self.filtros[a.categoria].isChecked()]
        if not visibles:
            self.tabla.hide()
            if all(a.categoria == "perfecta" for a in self.archivos):
                texto_oculto = (f"Las {len(self.archivos)} canciones ya están <b>perfectas</b>: "
                                "no hay nada que cambiar.<br>Marca <b>Perfectas</b> arriba si quieres verlas.")
            else:
                texto_oculto = (f"Las {len(self.archivos)} canciones cargadas están ocultas por los filtros de "
                                "<b>Mostrar</b>.<br>Marca las casillas de arriba para verlas.")
            self.mensaje_inicial.setText(f"<p style='font-size:15px; color:#555'>{texto_oculto}</p>")
            self.mensaje_inicial.show()
            return
        self.mensaje_inicial.hide()
        self.tabla.show()
        filas = sum(max(1, len(self.coincidencias(a))) for a in visibles)

        self._rellenando = True
        self.tabla.setUpdatesEnabled(False)
        self.tabla.clearSpans()
        self.celdas_audio = {}
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(filas)
        self.fila_a_archivo = {}
        fila = 0
        for n, archivo in enumerate(visibles):
            fondo = QColor("#ffffff") if n % 2 == 0 else QColor("#f5f5f5")
            inicio = fila
            archivo._fila, archivo._fondo = fila, fondo
            coincidencias = self.coincidencias(archivo)
            self.pintar_archivo(fila, archivo, fondo)
            if coincidencias.empty:
                self.fila_a_archivo[fila] = (archivo, None)
                self.pintar_sin_coincidencias(fila, fondo)
                fila += 1
            else:
                for pos in range(len(coincidencias)):
                    self.fila_a_archivo[fila] = (archivo, pos)
                    self.pintar_coincidencia(fila, archivo, pos, fondo)
                    fila += 1
            if fila - inicio > 1:
                for col in COLUMNAS_ARCHIVO:
                    self.tabla.setSpan(inicio, col, fila - inicio, 1)
        self.tabla.setUpdatesEnabled(True)
        self._rellenando = False

    @staticmethod
    def coincidencias(archivo):
        c = getattr(archivo, "coincidencias", None)
        return c if c is not None else pd.DataFrame()

    def item(self, valor, fondo, editable=False, tooltip=None):
        it = QTableWidgetItem(texto(valor))
        it.setBackground(fondo)
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if editable:
            flags |= Qt.ItemIsEditable
        it.setFlags(flags)
        it.setToolTip(tooltip if tooltip is not None else texto(valor))
        return it

    def pintar_archivo(self, fila, archivo, fondo):
        actuales = tags_actuales(archivo)
        if archivo.estado_guardado is True:
            estado, color = "✔ Guardado", QColor("#a5d6a7")
        elif archivo.estado_guardado is False:
            estado, color = "✖ Error al guardar", QColor("#ef9a9a")
        else:
            estado, color = CATEGORIAS[archivo.categoria][0], fondo
        explicacion = [CATEGORIAS[archivo.categoria][2]]
        motivo = getattr(archivo, "motivo_fecha", "")
        disco = getattr(archivo, "disco", None)
        if motivo and archivo.estado_guardado is None and archivo.categoria == "dudosa":
            estado += " · fecha del CD"
        if motivo:
            explicacion.append(f"La fecha del archivo no sirve para elegir: {motivo}.")
        if disco:
            explicacion.append(disco["texto"])
        _, _, cambia = self.cambios_de(archivo) if archivo.estado_guardado is None else ({}, {}, {})
        if archivo.seleccion is not None and archivo.estado_guardado is None:
            explicacion.append("Al aplicar cambia: " + ", ".join(NOMBRE_CAMPO[k] for k in cambia) if cambia
                               else "Con la opción marcada no cambia nada.")
        it = self.item(estado, color, tooltip="\n\n".join(explicacion))
        it.setFont(QFont("", -1, QFont.Bold))
        self.tabla.setItem(fila, COL_ESTADO, it)
        ruta = archivo.ruta_archivo
        album = texto(getattr(archivo.tags, "album", ""))
        for col, clave in ((COL_TITULO, "title"), (COL_ARTISTA, "artist"), (COL_ANO, "year"),
                           (COL_GENERO, "genre"), (COL_COMPOSITOR, "composer")):
            tip = f"{actuales[clave]}\n\n{ruta}" + (f"\nÁlbum: {album}" if album else "")
            celda = self.item(actuales[clave], fondo, tooltip=tip)
            if col == COL_ANO and motivo:
                celda.setForeground(QBrush(QColor("#999")))
                celda.setText(f"{actuales[clave][:4]} (CD)")
                celda.setToolTip(f"{motivo}.\nNo se usa para elegir la grabación.")
            if clave in cambia:
                # Lo que va a cambiar: en amarillo, "antes → después"
                antes = celda.text() or "(vacío)"
                celda.setText(f"{antes}  →  {cambia[clave]}")
                celda.setBackground(QColor("#fff59d"))
                celda.setForeground(QBrush(QColor("#000")))
                celda.setToolTip(f"Al aplicar cambiará:\n\nAntes:    {actuales[clave] or '(vacío)'}\n"
                                 f"Después: {cambia[clave]}\n\n{ruta}")
            self.tabla.setItem(fila, col, celda)
        titulo = actuales["title"] or os.path.basename(ruta)
        self.celda_audio(fila, COL_PLAY, ("archivo", ruta), ruta, f"Tu archivo: {titulo} — {actuales['artist']}",
                         fondo, "Escuchar tu archivo")

    def pintar_sin_coincidencias(self, fila, fondo):
        for col in range(COL_USAR, len(CABECERAS)):
            self.tabla.setItem(fila, col, self.item("", fondo))
        aviso = self.item("— sin coincidencias: doble clic aquí para buscar en la BD · E para editar a mano —", fondo,
                          tooltip="Doble clic para buscar esta canción en la base de datos")
        aviso.setForeground(QBrush(QColor("#888")))
        self.tabla.setItem(fila, COL_BD_TITULO, aviso)
        self.tabla.setSpan(fila, COL_BD_TITULO, 1, COL_BD_COMPOSITOR - COL_BD_TITULO + 1)

    def pintar_coincidencia(self, fila, archivo, pos, fondo):
        coincidencia = self.coincidencias(archivo).iloc[pos]
        colores = getattr(archivo, "colores_labels", None)
        indice = self.coincidencias(archivo).index[pos]

        usar = self.item("", fondo)
        usar.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
        usar.setCheckState(Qt.Checked if archivo.seleccion == pos else Qt.Unchecked)
        usar.setToolTip("Marcar para escribir estas tags en el archivo")
        disco = getattr(archivo, "disco", None)
        encaja = bool(disco) and pos in disco["encajan"]
        if encaja:
            usar.setText("💿")
            usar.setToolTip(f"Encaja con el resto del disco: {disco['texto']}")
        self.tabla.setItem(fila, COL_USAR, usar)

        for col, (campo, formatear) in COLUMNAS_BD.items():
            original = texto(coincidencia.get(campo, ""))
            valor = formatear(original)
            tip = valor if valor == original else f"{valor}\n(en la base de datos: {original!r})"
            color = fondo
            if colores is not None and indice in colores.index and COLORES_COLUMNA[col] in colores.columns:
                color = QColor(COLORES_SUAVES.get(colores.at[indice, COLORES_COLUMNA[col]], fondo))
            celda = self.item(valor, color, editable=True, tooltip=tip)
            if encaja and col == COL_BD_FECHA:
                celda.setFont(QFont("", -1, QFont.Bold))
                celda.setToolTip(f"{tip}\n💿 Encaja con el resto del disco ({disco['texto']})")
            self.tabla.setItem(fila, col, celda)

        for col, campo, duracion in ((COL_BD_PLAY30, "audio30", "30 s"), (COL_BD_PLAY10, "audio10", "10 s")):
            enlace = texto(coincidencia.get(campo, "")).strip()
            if enlace:
                descripcion = (f"BD {duracion}: {texto(coincidencia.get('titulo'))} — "
                               f"{texto(coincidencia.get('artista'))} ({texto(coincidencia.get('fecha')) or 'sin fecha'})")
                self.celda_audio(fila, col, ("bd", enlace), utils.link_to_music(enlace), descripcion, fondo,
                                 f"Escuchar el fragmento de {duracion} de la base de datos")
            else:
                self.tabla.setItem(fila, col, self.item("", fondo, tooltip="Sin fragmento en la base de datos"))

    def on_item_changed(self, item):
        if self._rellenando or item.row() not in self.fila_a_archivo:
            return
        archivo, pos = self.fila_a_archivo[item.row()]
        if pos is None:
            return
        if item.column() == COL_USAR:
            archivo.seleccion = pos if item.checkState() == Qt.Checked else (
                None if archivo.seleccion == pos else archivo.seleccion)
            # Solo una coincidencia marcada por canción
            self._rellenando = True
            for fila, (a, p) in self.fila_a_archivo.items():
                if a is archivo and p is not None and p != pos:
                    self.tabla.item(fila, COL_USAR).setCheckState(Qt.Unchecked)
            self._rellenando = False
            self.repintar_archivo(archivo)
        elif item.column() in COLUMNAS_BD:
            # Edición manual: se guarda en las coincidencias para que no se pierda al filtrar
            campo = COLUMNAS_BD[item.column()][0]
            columna = archivo.coincidencias.columns.get_loc(campo)
            archivo.coincidencias = archivo.coincidencias.copy()
            archivo.coincidencias.iat[pos, columna] = item.text()
            item.setToolTip(item.text())
            if archivo.seleccion == pos:
                self.repintar_archivo(archivo)

    def eventFilter(self, objeto, evento):
        """Clic en ▶/■: reproduce o para sin seleccionar la fila. Teclas de revisión en la tabla."""
        if objeto is self.tabla and evento.type() == QEvent.KeyPress and not self.tabla.state() == QAbstractItemView.EditingState:
            if self.tecla_revision(evento):
                return True
        if objeto is self.tabla.viewport() and evento.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick) \
                and evento.button() == Qt.LeftButton:
            indice = self.tabla.indexAt(evento.pos())
            celda = self.celdas_audio.get((indice.row(), indice.column()))
            if celda:
                if evento.type() == QEvent.MouseButtonPress:
                    clave, ruta, descripcion, _ = celda
                    self.reproductor.alternar(clave, ruta, descripcion)
                return True
        return super().eventFilter(objeto, evento)

    def tecla_revision(self, evento):
        """1-9 elige la opción, 0 ninguna, Espacio escucha el archivo, S siguiente por decidir, X no tocar."""
        fila = self.tabla.currentRow()
        if fila not in self.fila_a_archivo:
            return False
        archivo, _ = self.fila_a_archivo[fila]
        tecla, texto_tecla = evento.key(), evento.text().lower()
        if Qt.Key_1 <= tecla <= Qt.Key_9:
            n = tecla - Qt.Key_1
            if n < len(self.coincidencias(archivo)):
                archivo.seleccion = n
                self.refrescar_usar(archivo)
                self.ir_a(archivo, n)
            return True
        if tecla in (Qt.Key_0, Qt.Key_Backspace):
            archivo.seleccion = None
            self.refrescar_usar(archivo)
            return True
        if tecla == Qt.Key_Space:
            t = tags_actuales(archivo)
            self.reproductor.alternar(("archivo", archivo.ruta_archivo), archivo.ruta_archivo,
                                      f"Tu archivo: {t['title'] or os.path.basename(archivo.ruta_archivo)} — {t['artist']}")
            return True
        if texto_tecla == "s":
            self.siguiente_por_decidir()
            return True
        if texto_tecla == "x":
            self.marcar_no_tocar()
            return True
        if texto_tecla == "e":
            self.editar_a_mano(archivo)
            return True
        return False

    def refrescar_usar(self, archivo):
        """Actualiza las casillas 'Usar' de una canción sin repintar toda la tabla."""
        self._rellenando = True
        for fila, (a, pos) in self.fila_a_archivo.items():
            if a is archivo and pos is not None and self.tabla.item(fila, COL_USAR) is not None:
                self.tabla.item(fila, COL_USAR).setCheckState(Qt.Checked if archivo.seleccion == pos else Qt.Unchecked)
        self._rellenando = False
        self.repintar_archivo(archivo)

    def repintar_archivo(self, archivo):
        """Vuelve a pintar la parte del archivo (estado y lo que va a cambiar) de una canción."""
        if getattr(archivo, "_fila", None) is None or self.fila_a_archivo.get(archivo._fila, (None,))[0] is not archivo:
            return
        previo = self._rellenando
        self._rellenando = True
        self.pintar_archivo(archivo._fila, archivo, archivo._fondo)
        self._rellenando = previo

    def ir_a(self, archivo, pos=None):
        for fila, (a, p) in self.fila_a_archivo.items():
            if a is archivo and (pos is None or p == pos):
                self.tabla.setCurrentCell(fila, max(self.tabla.currentColumn(), 0))
                self.tabla.selectRow(fila)
                self.tabla.scrollToItem(self.tabla.item(fila, COL_USAR) or self.tabla.item(fila, COL_ESTADO))
                return

    def siguiente_por_decidir(self):
        """Va a la siguiente canción que no es perfecta y no tiene nada marcado."""
        visibles = list(dict.fromkeys(a for a, _ in (self.fila_a_archivo[f] for f in sorted(self.fila_a_archivo))))
        actual = self.archivo_seleccionado()
        inicio = visibles.index(actual) + 1 if actual in visibles else 0
        for a in visibles[inicio:] + visibles[:inicio]:
            if a.categoria != "perfecta" and a.seleccion is None and a.estado_guardado is None:
                self.ir_a(a)
                return
        self.statusBar().showMessage("No quedan canciones por decidir en la lista visible", 5000)

    def marcar_no_tocar(self):
        archivo = self.archivo_seleccionado()
        if archivo is None:
            QMessageBox.information(self, "No tocar", "Selecciona primero una canción en la tabla.")
            return
        visibles = list(dict.fromkeys(a for a, _ in (self.fila_a_archivo[f] for f in sorted(self.fila_a_archivo))))
        siguiente = visibles[visibles.index(archivo) + 1] if archivo in visibles and visibles.index(archivo) + 1 < len(visibles) else None
        t = tags_actuales(archivo)
        no_tocar.marcar([(archivo.ruta_archivo, t["title"])])
        self.archivos.remove(archivo)
        self.actualizar_contadores()
        self.rellenar_tabla()
        if siguiente is not None:
            self.ir_a(siguiente)
        self.statusBar().showMessage(f"«{t['title']}» marcada como No tocar (Archivo → Canciones «No tocar» para deshacerlo)", 8000)

    def editar_grafias(self):
        from src.ui.dialogo_grafias import DialogoGrafias
        from src.utils.buscar_artista import separar_orquesta_cantor
        db = self.data_store.get_db()
        col_art = "_artista_bd" if "_artista_bd" in db else "artista"
        col_can = "_cantor_bd" if "_cantor_bd" in db else "cantor"
        nombres_bd = set(db[col_art]) | {x.strip() for v in db[col_can] for x in re.split(r",|\sy\s", str(v)) if x.strip()}
        cargadas = {}       # nombres de toda tu colección (biblioteca), con cuántos archivos tiene cada grafía
        for artista in self.biblioteca.dataframe()["artist"]:
            orq, cant = separar_orquesta_cantor(artista)
            for nombre in [orq] + [c.strip() for c in re.split(r",|\sy\s", cant) if c.strip()]:
                if nombre:
                    cargadas[nombre] = cargadas.get(nombre, 0) + 1
        if DialogoGrafias(self, nombres_bd, cargadas).exec_() == QDialog.Accepted:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.recargar_bd()
            finally:
                QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Grafías guardadas",
                                    "Guardadas. Vuelve a cargar las canciones para ver las sugerencias con las grafías nuevas.")

    # ------------------------------------------------------------------ biblioteca
    @property
    def biblioteca(self):
        if self._biblioteca is None:
            from src.biblioteca.biblioteca import Biblioteca
            self._biblioteca = Biblioteca()
        return self._biblioteca

    def iniciar_biblioteca(self):
        """Al arrancar: apunta la sesión (para 'nuevas desde la última vez') y se pone al día en segundo plano."""
        self.actualizar_biblioteca(empezar_sesion=True)

    def actualizar_biblioteca(self, empezar_sesion=False):
        if self._hilo_biblioteca is not None and self._hilo_biblioteca.isRunning():
            self._repetir_biblioteca = True      # cuando termine, otra vuelta (p. ej. cambiaron las reglas)
            return
        self._repetir_biblioteca = False
        self.etiqueta_biblioteca.setText("📚 Biblioteca: buscando cambios…")
        self._hilo_biblioteca = ActualizarBiblioteca(self.biblioteca, empezar_sesion, self.opt_fecha.isChecked())
        self._hilo_biblioteca.progreso.connect(self._biblioteca_progreso)
        self._hilo_biblioteca.terminado.connect(self._biblioteca_terminada)
        self._hilo_biblioteca.start()

    def _biblioteca_progreso(self, fase, hechos, total):
        if fase == "leer" and total:
            self.etiqueta_biblioteca.setText(f"📚 Biblioteca: leyendo tags de lo nuevo… {hechos} de {total}")
        elif fase == "emparejar" and total:
            self.etiqueta_biblioteca.setText(f"📚 Biblioteca: comparando con la base de datos… {hechos} de {total}")

    def _biblioteca_terminada(self, informe):
        if isinstance(informe, Exception):
            self.etiqueta_biblioteca.setText("📚 Biblioteca: error al actualizar")
            self.etiqueta_biblioteca.setToolTip(str(informe))
            return
        total = self.biblioteca.cuantos()
        partes = [f"{informe[k]} {n}" for k, n in (("nuevas", "nuevas"), ("cambiadas", "cambiadas"),
                                                   ("movidas", "movidas"), ("borradas", "borradas")) if informe[k]]
        self.etiqueta_biblioteca.setText(f"📚 {total:,} canciones".replace(",", ".")
                                         + (" · " + ", ".join(partes) if partes else " · al día"))
        self.etiqueta_biblioteca.setToolTip(
            f"Biblioteca actualizada en {informe['segundos']} s: {informe['nuevas']} nuevas, "
            f"{informe['cambiadas']} cambiadas, {informe['movidas']} movidas, {informe['borradas']} borradas, "
            f"{informe['leidas']} tags leídas, {informe.get('emparejadas', 0)} comparadas con la base de datos, "
            f"{informe['errores']} con error, {informe['en_nube']} solo en la nube.\n"
            "Archivo → Actualizar la biblioteca ahora para volver a mirar.")
        # Lo que dependía de la colección se recalcula con los datos nuevos
        self._indice_coleccion = None
        self._indice_tengo = None
        if getattr(self, "buscador", None) is not None:
            self.buscador.tengo = None
        if getattr(self, "ventana_estado", None) is not None and self.ventana_estado.isVisible():
            self.ventana_estado.cargar()
        if getattr(self, "_repetir_biblioteca", False):
            self.actualizar_biblioteca()

    def editar_carpetas(self):
        from src.ui.dialogo_carpetas import DialogoCarpetas
        if DialogoCarpetas(self).exec_() == QDialog.Accepted:
            from src.biblioteca.biblioteca import leer_config
            self.biblioteca.config = leer_config()
            self.actualizar_biblioteca()

    def abrir_estado(self):
        from src.ui.ventana_estado import VentanaEstado
        if getattr(self, "ventana_estado", None) is None:
            self.ventana_estado = VentanaEstado(
                self, self.biblioteca, actualizar=self.actualizar_biblioteca, revisar_coleccion=self.revisar_coleccion,
                abrir_duplicados=self.abrir_duplicados, editar_carpetas=self.editar_carpetas)
        else:
            self.ventana_estado.cargar()
        self.ventana_estado.show()
        self.ventana_estado.raise_()
        self.ventana_estado.activateWindow()

    def abrir_reparar_playlists(self):
        from src.ui.ventana_playlists import VentanaPlaylists
        if getattr(self, "ventana_playlists", None) is None:
            self.ventana_playlists = VentanaPlaylists(self, self.reproductor, self.indice_coleccion)
        self.ventana_playlists.indice = None          # con los datos más recientes de la biblioteca
        self.ventana_playlists.show()
        self.ventana_playlists.raise_()
        self.ventana_playlists.analizar()

    def indice_coleccion(self):
        """Índice de tu colección para buscar canciones movidas (de la biblioteca)."""
        from src.utils import playlists
        if getattr(self, "_indice_coleccion", None) is None:
            self._indice_coleccion = playlists.IndiceColeccion(self.biblioteca.dataframe())
        return self._indice_coleccion

    def abrir_duplicados(self, colecciones):
        from src.ui.ventana_duplicados import VentanaDuplicados
        self.ventana_duplicados = VentanaDuplicados(self, self.reproductor, self.biblioteca, colecciones)
        self.ventana_duplicados.show()
        self.ventana_duplicados.raise_()

    def revisar_filas(self, df, origen):
        """Carga en la tabla canciones de la biblioteca usando las tags que ya tiene (sin volver a leerlas)."""
        filas = df.sort_values("ruta")
        rutas_y_tags = [(r["ruta"], [r["title"], r["artist"], r["year"], r["genre"], r["composer"], r["ruta"],
                                     r["album"]]) if r["tags_leidas"] and not r["error"] else (r["ruta"], None)
                        for r in filas.to_dict("records")]
        self.raise_()
        self.activateWindow()
        self.procesar_archivos(rutas_y_tags, origen=origen)

    def revisar_coleccion(self, nombre):
        self.revisar_filas(self.biblioteca.dataframe("coleccion=? AND en_nube=0", (nombre,)), origen=nombre)

    def ver_no_tocar(self):
        DialogoNoTocar(self).exec_()

    def celda_audio(self, fila, col, clave, ruta, descripcion, fondo, ayuda):
        """Pinta una celda ▶ (o ■ si es lo que está sonando) y la registra para el clic."""
        self.celdas_audio[(fila, col)] = (clave, ruta, descripcion, fondo)
        it = self.item("", fondo, tooltip=ayuda)
        it.setTextAlignment(Qt.AlignCenter)
        self.tabla.setItem(fila, col, it)
        self.pintar_celda_audio(fila, col)

    def pintar_celda_audio(self, fila, col):
        clave, _, descripcion, fondo = self.celdas_audio[(fila, col)]
        it = self.tabla.item(fila, col)
        if it is None:
            return
        suena = self.reproductor.sonando(clave)
        it.setText("■" if suena else "▶")
        it.setBackground(QColor("#66bb6a") if suena else fondo)
        it.setForeground(QBrush(QColor("white" if suena else "#333")))
        it.setFont(QFont("", -1, QFont.Bold if suena else QFont.Normal))
        it.setToolTip(f"Sonando: {descripcion}\nClic para parar" if suena else f"Escuchar: {descripcion}")

    def pintar_sonando(self, clave):
        previo = self._rellenando
        self._rellenando = True
        for fila, col in self.celdas_audio:
            self.pintar_celda_audio(fila, col)
        self._rellenando = previo

    def on_cell_double_clicked(self, fila, col):
        if fila not in self.fila_a_archivo:
            return
        archivo, pos = self.fila_a_archivo[fila]
        if col in COLUMNAS_ARCHIVO and col != COL_PLAY:
            self.editar_a_mano(archivo)
        elif pos is None and col >= COL_USAR:
            self.buscar_en_bd(archivo)

    def editar_a_mano(self, archivo=None):
        """Formulario para escribir las tags de una canción a mano (con copia y deshacer)."""
        from src.ui.dialogo_editar import DialogoEditar
        archivo = archivo if isinstance(archivo, Cancion) else self.archivo_seleccionado()
        if archivo is None:
            QMessageBox.information(self, "Editar a mano", "Selecciona primero una canción en la tabla.")
            return
        dialogo = DialogoEditar(self, archivo.ruta_archivo, tags_actuales(archivo), self.reproductor)
        if dialogo.exec_() != QDialog.Accepted:
            return
        cambios = dialogo.cambios()
        historial.guardar_backup([(archivo.ruta_archivo, tags_actuales(archivo), cambios)])
        if self.reproductor.sonando(("archivo", archivo.ruta_archivo)):
            self.reproductor.parar()
        ok = utils.update_tags(archivo.ruta_archivo, title=cambios.get("title"), artist=cambios.get("artist"),
                               year=cambios.get("year"), genre=cambios.get("genre"), composer=cambios.get("composer"))
        archivo.estado_guardado = ok
        if ok:
            try:
                archivo.tags = utils.leer_tags(archivo.ruta_archivo)
            except Exception:
                pass
            archivo.seleccion = None
            self.statusBar().showMessage("Tags guardadas a mano (Deshacer las devuelve).", 8000)
        else:
            QMessageBox.warning(self, "Editar a mano", "No se pudieron escribir las tags en el archivo.")
        self.rellenar_tabla()
        self.ir_a(archivo)

    def marcar_sugeridas(self):
        for a in self.archivos:
            if a.categoria == "preferida" and not self.coincidencias(a).empty:
                a.seleccion = a.coincidencia_preferida
        self.rellenar_tabla()

    def desmarcar_todo(self):
        for a in self.archivos:
            a.seleccion = None
        self.rellenar_tabla()

    def archivo_seleccionado(self):
        filas = self.tabla.selectionModel().selectedRows() if self.tabla.isVisible() else []
        if filas and filas[0].row() in self.fila_a_archivo:
            return self.fila_a_archivo[filas[0].row()][0]
        return None

    def mostrar_detalles(self, archivo):
        t = tags_actuales(archivo)
        caja = QMessageBox(self)
        caja.setWindowTitle("Detalles del archivo")
        caja.setText(f"<b>{t['title'] or os.path.basename(archivo.ruta_archivo)}</b>")
        caja.setInformativeText(
            f"Ruta: {archivo.ruta_archivo}\n\nArtista: {t['artist']}\nAño: {t['year']}\n"
            f"Género: {t['genre']}\nCompositor: {t['composer']}\n\n{CATEGORIAS[archivo.categoria][2]}")
        abrir = caja.addButton("Abrir carpeta", QMessageBox.ActionRole)
        caja.addButton("Cerrar", QMessageBox.RejectRole)
        caja.exec_()
        if caja.clickedButton() is abrir:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(archivo.ruta_archivo)])

    # ------------------------------------------------------------------ aplicar tags
    def cambios_de(self, archivo):
        """(tags actuales, tags nuevas, solo lo que cambia) si se aplica la opción marcada."""
        return cambios_de(archivo)

    def aplicar_tags(self):
        cambios, sin_cambios = [], 0
        for archivo in self.archivos:
            if archivo.seleccion is None:
                continue
            actuales, nuevas, diferencias = self.cambios_de(archivo)
            if diferencias:
                cambios.append((archivo, actuales, nuevas, diferencias))
            else:
                sin_cambios += 1

        if not cambios:
            QMessageBox.information(
                self, "Nada que aplicar",
                "No hay canciones marcadas en 'Usar' con tags distintas a las actuales."
                + (f"\n\n({sin_cambios} marcadas ya tienen las tags correctas.)" if sin_cambios else ""))
            return

        if DialogoConfirmar(self, cambios, sin_cambios).exec_() != QDialog.Accepted:
            return

        backup = historial.guardar_backup([(a.ruta_archivo, act, dif) for a, act, _, dif in cambios])
        errores = escritos = 0
        self.empezar_progreso(len(cambios))
        for i, (archivo, _, _, diferencias) in enumerate(cambios, 1):
            if self._cancelado:
                break
            self.progress_bar.setValue(i)
            self.statusBar().showMessage(f"Escribiendo tags… {i} de {len(cambios)}")
            QApplication.processEvents()
            ok = utils.update_tags(archivo.ruta_archivo, title=diferencias.get("title"),
                                   artist=diferencias.get("artist"), year=diferencias.get("year"),
                                   genre=diferencias.get("genre"), composer=diferencias.get("composer"))
            archivo.estado_guardado = ok
            escritos += ok
            if ok:
                try:
                    archivo.tags = utils.leer_tags(archivo.ruta_archivo)
                except Exception:
                    pass
            else:
                errores += 1
        self.terminar_progreso()
        self.rellenar_tabla()

        mensaje = f"Tags escritas en {escritos} archivo(s)."
        if escritos + errores < len(cambios):
            mensaje += f"\nCancelado: {len(cambios) - escritos - errores} archivo(s) sin tocar."
        mensaje += ("\n\nSe guardó una copia de las tags anteriores: 'Deshacer' las vuelve a poner."
                    f"\n({os.path.basename(backup)})")
        if errores:
            mensaje += f"\n{errores} archivo(s) dieron error (marcados en rojo en la columna Estado)."
        self.statusBar().showMessage(mensaje.replace("\n", " "))
        (QMessageBox.warning if errores else QMessageBox.information)(self, "Tags aplicadas", mensaje)

    # ------------------------------------------------------------------ deshacer
    def deshacer_ultimo(self):
        backups = historial.listar_backups()
        if not backups:
            QMessageBox.information(self, "Nada que deshacer", "No hay cambios de tags guardados para deshacer.")
            return
        self.deshacer_backup(backups[0])

    def historial_cambios(self):
        backups = historial.listar_backups(incluir_deshechos=True)
        if not backups:
            QMessageBox.information(self, "Historial vacío", "Todavía no se han aplicado tags con esta versión.")
            return
        textos = [historial.resumen_backup(b) for b in backups]
        elegido, ok = QInputDialog.getItem(self, "Historial de cambios",
                                           "Elige el cambio a deshacer (el más reciente arriba):", textos, 0, False)
        if ok:
            self.deshacer_backup(backups[textos.index(elegido)])

    def abrir_carpeta_backups(self):
        os.makedirs(historial.CARPETA_BACKUPS, exist_ok=True)
        os.startfile(historial.CARPETA_BACKUPS)

    def deshacer_backup(self, ruta_csv):
        if historial.esta_deshecho(ruta_csv):
            QMessageBox.information(self, "Ya deshecho", "Ese cambio ya se deshizo.")
            return
        df = historial.leer_backup(ruta_csv)
        n = df["archivo"].nunique()
        ejemplos = "\n".join(f"  • {os.path.basename(a)}" for a in df["archivo"].unique()[:10])
        if n > 10:
            ejemplos += "\n  …"
        if QMessageBox.question(
                self, "Deshacer cambios",
                f"Se van a restaurar las tags anteriores de {n} archivo(s) "
                f"({historial.resumen_backup(ruta_csv)}):\n\n{ejemplos}\n\n¿Continuar?") != QMessageBox.Yes:
            return
        restaurados, errores = historial.deshacer(ruta_csv, utils.escribir_tags)
        afectados = set(df["archivo"])
        for a in self.archivos:
            if a.ruta_archivo in afectados:
                try:
                    a.tags = utils.leer_tags(a.ruta_archivo)
                    a.estado_guardado = None
                except Exception:
                    pass
        self.rellenar_tabla()
        mensaje = f"Restauradas las tags de {restaurados} archivo(s)."
        if errores:
            mensaje += f"\n{len(errores)} no se pudieron restaurar:\n" + "\n".join(errores[:10])
        (QMessageBox.warning if errores else QMessageBox.information)(self, "Deshacer", mensaje)

    # ------------------------------------------------------------------ búsqueda en BD
    def buscar_en_bd(self, archivo=None):
        """Abre (o trae al frente) el buscador. Si se llama para una canción sin coincidencias, la busca ya."""
        from src.ui.buscador_bd import VentanaBuscador
        para_cancion = isinstance(archivo, Cancion)
        if not para_cancion:
            archivo = self.archivo_seleccionado()
        if getattr(self, "buscador", None) is None:
            self.buscador = VentanaBuscador(
                self, obtener_indice=self.data_store.get_indice_busqueda, obtener_bd=self.data_store.get_db,
                usar=self.asignar_desde_bd,
                reproductor=self.reproductor, recargar_bd=self.recargar_bd, obtener_tengo=self.indice_tengo)
        # Busca ya la canción si se abre para ella o si la caja está vacía
        self.buscador.set_destino(archivo, buscar_por_defecto=para_cancion or (
            archivo is not None and not self.buscador.caja.text().strip()))
        self.buscador.show()
        self.buscador.raise_()
        self.buscador.activateWindow()
        self.buscador.caja.setFocus()
        self.buscador.caja.selectAll()

    def recargar_bd(self):
        from src.config.config import DB_CSV_PATH
        self.data_store.load_data(DB_CSV_PATH)
        self.data_store.get_indice_busqueda()
        self.actualizar_biblioteca()       # las reglas cambiaron: la biblioteca se vuelve a comparar

    def indice_tengo(self):
        """Qué grabaciones tienes (de la biblioteca)."""
        from src.utils import coleccion
        if getattr(self, "_indice_tengo", None) is None:
            self._indice_tengo = coleccion.IndiceTengo(self.biblioteca.dataframe())
        return self._indice_tengo

    def seleccion_cambiada(self):
        if getattr(self, "buscador", None) is not None and self.buscador.isVisible():
            self.buscador.set_destino(self.archivo_seleccionado())

    def asignar_desde_bd(self, archivo, indice_bd):
        """Asigna a la canción una grabación elegida en el buscador y la marca en 'Usar'."""
        if archivo not in self.archivos:
            return
        fila = self.data_store.get_db().loc[indice_bd]
        actuales = self.coincidencias(archivo)
        if indice_bd in actuales.index:
            archivo.seleccion = actuales.index.get_loc(indice_bd)
        else:
            archivo.coincidencias = pd.concat([actuales, fila.to_frame().T])
            archivo.seleccion = len(archivo.coincidencias) - 1
        self.rellenar_tabla()
        for f, (a, pos) in self.fila_a_archivo.items():
            if a is archivo and pos == archivo.seleccion:
                self.tabla.selectRow(f)
                self.tabla.scrollToItem(self.tabla.item(f, COL_USAR))
                break
        self.statusBar().showMessage(f"Asignada «{fila['titulo']}» ({fila['artista']}). Pulsa Aplicar tags para escribirla.")

    # ------------------------------------------------------------------ audio y diapos
    def stop_music(self):
        self.reproductor.parar()

    def abrir_crear_diapos(self):
        from src.ui.ventana_diapos import VentanaDiapos
        if getattr(self, "ventana_diapos", None) is None:
            self.ventana_diapos = VentanaDiapos(self)
        self.ventana_diapos.show()
        self.ventana_diapos.raise_()
        self.ventana_diapos.activateWindow()

    def abrir_control_diapos(self):
        try:
            from control_slides import SlideControllerApp
        except Exception as e:
            QMessageBox.critical(self, "Control diapos", f"No se pudo abrir el control de diapos:\n{e}")
            return
        if getattr(self, "control_diapos", None) is None or not self.control_diapos.isVisible():
            self.control_diapos = SlideControllerApp(embebido=True)
        self.control_diapos.show()
        self.control_diapos.raise_()
        self.control_diapos.activateWindow()

    def regenerar_bd(self):
        from src.config.config import DB_ORIGINAL_CSV_PATH, DATA_FOLDER
        from src.utils import mejorar_bd
        if QMessageBox.question(
                self, "Regenerar base de datos",
                f"Se va a crear data/tangodb.csv a partir de {os.path.basename(DB_ORIGINAL_CSV_PATH)}: "
                "unificar nombres, rellenar compositores y fechas seguros.\n\n¿Continuar?") != QMessageBox.Yes:
            return
        destino = os.path.join(DATA_FOLDER, "tangodb.csv")
        self.statusBar().showMessage("Regenerando la base de datos…")
        self.progress_bar.setMaximum(0)
        self.progress_bar.show()
        hilo = EnSegundoPlano(lambda: mejorar_bd.main(DB_ORIGINAL_CSV_PATH, destino))
        hilo.start()
        while hilo.isRunning():
            QApplication.processEvents()
            hilo.wait(50)
        self.progress_bar.hide()
        if hilo.error is not None:
            QMessageBox.critical(self, "Error", f"No se pudo regenerar la base de datos:\n{hilo.error}")
            return
        self.data_store.load_data(destino)
        self.actualizar_biblioteca()
        resumen = "\n".join(f"  • {k}: {v}" for k, v in hilo.resultado.items())
        QMessageBox.information(self, "Base de datos regenerada",
                                f"Hecho. La app ya usa la base de datos nueva.\n\n{resumen}\n\n"
                                "Las fechas que no se pudieron arreglar están en output/informe_fechas_dudosas.csv")
        self.statusBar().showMessage("Base de datos regenerada")

    def mostrar_ayuda(self):
        caja = QMessageBox(self)
        caja.setWindowTitle("Ayuda — TangoTags")
        caja.setTextFormat(Qt.RichText)
        caja.setText(TEXTO_AYUDA)
        caja.exec_()

    def closeEvent(self, event):
        for clave in ("opt_fecha", "opt_guardar_coinc", "opt_guardar_resid", "opt_saltar", "opt_no_tocar"):
            self.settings.setValue(clave, getattr(self, clave).isChecked())
        if self._hilo_biblioteca is not None and self._hilo_biblioteca.isRunning():
            self._hilo_biblioteca.requestInterruption()
            self._hilo_biblioteca.wait(5000)
        event.accept()


class ActualizarBiblioteca(QThread):
    """Pone la biblioteca al día sin bloquear la ventana."""
    progreso = pyqtSignal(str, int, int)
    terminado = pyqtSignal(object)        # informe (dict) o la excepción

    def __init__(self, biblioteca, empezar_sesion=False, usar_fecha=True):
        super().__init__()
        self.biblioteca, self.empezar_sesion, self.usar_fecha = biblioteca, empezar_sesion, usar_fecha

    def run(self):
        from src.motor.emparejar import version_reglas
        try:
            if self.empezar_sesion:
                self.biblioteca.empezar_sesion()
            avisar = lambda f, h, t: self.progreso.emit(f, h, t)
            informe = self.biblioteca.actualizar(progreso=avisar, cancelado=self.isInterruptionRequested)
            # Nivel 3: estado de lo nuevo o cambiado (o de todo, si cambiaron las reglas), en procesos aparte
            if not self.isInterruptionRequested():
                emparejado = self.biblioteca.emparejar(version_reglas(self.usar_fecha), usar_fecha=self.usar_fecha,
                                                       progreso=avisar, cancelado=self.isInterruptionRequested)
                informe["emparejadas"] = emparejado["emparejadas"]
            self.terminado.emit(informe)
        except Exception as e:
            self.terminado.emit(e)


class EnSegundoPlano(QThread):
    """Ejecuta una función lenta sin bloquear la ventana."""

    def __init__(self, funcion):
        super().__init__()
        self.funcion = funcion
        self.resultado = None
        self.error = None

    def run(self):
        try:
            self.resultado = self.funcion()
        except Exception as e:
            self.error = e


class DialogoConfirmar(QDialog):
    """Muestra el antes/después de cada archivo y pide confirmación."""

    CAMPOS = (("title", "Título"), ("artist", "Artista"), ("year", "Fecha"),
              ("genre", "Género"), ("composer", "Compositor"))

    def __init__(self, parent, cambios, sin_cambios):
        super().__init__(parent)
        self.setWindowTitle("Confirmar cambios de tags")
        self.resize(1400, 650)
        lay = QVBoxLayout(self)
        info = f"Se van a escribir tags en <b>{len(cambios)}</b> archivo(s). " \
               f"En <span style='background:#fff59d'>amarillo</span> lo que cambia."
        if sin_cambios:
            info += f" ({sin_cambios} marcadas ya estaban bien y se omiten.)"
        lay.addWidget(QLabel(info))

        t = QTableWidget(len(cambios) * 2, 2 + len(self.CAMPOS))
        t.setHorizontalHeaderLabels(["Archivo", ""] + [n for _, n in self.CAMPOS])
        t.verticalHeader().hide()
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        t.setColumnWidth(1, 70)
        gris, amarillo = QColor("#777"), QColor("#fff59d")
        for i, (archivo, actuales, nuevas, diferencias) in enumerate(cambios):
            f = i * 2
            nombre = QTableWidgetItem(os.path.basename(archivo.ruta_archivo))
            nombre.setToolTip(archivo.ruta_archivo)
            t.setItem(f, 0, nombre)
            t.setSpan(f, 0, 2, 1)
            t.setItem(f, 1, QTableWidgetItem("antes"))
            t.setItem(f + 1, 1, QTableWidgetItem("después"))
            for c, (clave, _) in enumerate(self.CAMPOS, start=2):
                antes = QTableWidgetItem(actuales[clave])
                antes.setForeground(gris)
                antes.setToolTip(actuales[clave])
                t.setItem(f, c, antes)
                despues_txt = diferencias.get(clave, actuales[clave])
                despues = QTableWidgetItem(despues_txt)
                despues.setToolTip(despues_txt)
                if clave in diferencias:
                    despues.setBackground(amarillo)
                    despues.setFont(QFont("", -1, QFont.Bold))
                t.setItem(f + 1, c, despues)
        lay.addWidget(t)

        botones = QDialogButtonBox()
        ok = botones.addButton(f"Escribir tags en {len(cambios)} archivo(s)", QDialogButtonBox.AcceptRole)
        ok.setDefault(True)
        botones.addButton("Cancelar", QDialogButtonBox.RejectRole)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        lay.addWidget(botones)


class DialogoNoTocar(QDialog):
    """Lista de canciones marcadas «No tocar», con opción de quitar la marca."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Canciones marcadas «No tocar»")
        self.resize(1000, 550)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Estas canciones no aparecen al cargar (Opciones → Ocultar las canciones «No tocar»). "
                             "Selecciona y pulsa <b>Quitar marca</b> para que vuelvan a aparecer."))
        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["Título", "Archivo", "Marcada el"])
        self.tabla.verticalHeader().hide()
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        lay.addWidget(self.tabla)
        botones = QDialogButtonBox()
        quitar = botones.addButton("Quitar marca", QDialogButtonBox.ActionRole)
        quitar.clicked.connect(self.quitar)
        botones.addButton("Cerrar", QDialogButtonBox.RejectRole).clicked.connect(self.reject)
        lay.addWidget(botones)
        self.rellenar()

    def rellenar(self):
        self.df = no_tocar.leer()
        self.tabla.setRowCount(len(self.df))
        for i, (_, f) in enumerate(self.df.iterrows()):
            for c, v in enumerate([f["titulo"], f["ruta"], f["marcado_el"]]):
                self.tabla.setItem(i, c, QTableWidgetItem(v))
        self.tabla.resizeColumnToContents(0)

    def quitar(self):
        filas = sorted({i.row() for i in self.tabla.selectionModel().selectedRows()})
        if filas:
            no_tocar.desmarcar([self.df.iloc[f]["ruta"] for f in filas])
            self.rellenar()
