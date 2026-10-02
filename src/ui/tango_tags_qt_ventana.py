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
import sys

import pandas as pd
import pygame
from PyQt5.QtCore import Qt, QSize, QSettings
from PyQt5.QtGui import QIcon, QColor, QBrush, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QToolBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QHeaderView, QDialog, QPushButton, QFileDialog, QLineEdit, QCheckBox,
    QFrame, QMessageBox, QProgressBar, QApplication, QStyle, QToolButton, QDialogButtonBox,
    QAbstractItemView, QGridLayout,
)
from unidecode import unidecode

import src.utils.utils as utils
from src.config.config import (
    PROJECT_ROOT, icon_paths, m3u_start_path, musicbee_start_folder, dropbox_path, residuos,
    DEFAULT_DATE_CHECKED,
)
from src.config.database import Database
from src.ui.file_to_find_qt import FILETOFINDQT
from src.utils.MusicBeeLibraryTools import MusicBeeLibraryTools
from src.utils.formato_tags import (
    tags_desde_coincidencia, formatear_cantores, formatear_fecha, formatear_estilo,
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
    "perfecta": ("✔ Perfecta", "Perfectas", "Las tags ya coinciden con la base de datos"),
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
<li>Si no hay coincidencias, haz <b>doble clic</b> en la parte BD para buscar a mano.</li>
<li>Doble clic en la parte del archivo muestra la ruta y permite abrir la carpeta.</li>
<li>Clic en ▶ para escuchar; <i>Parar</i> detiene el audio.</li>
</ul></li>
<li><b>Aplicar tags</b>: muestra el antes/después de cada archivo y pide confirmación.
Si cargaste desde MusicBee, después haz en MusicBee <i>Herramientas → Volver a leer tags</i>.</li>
<li><b>Diapos</b>: <i>Crear diapos</i> genera la presentación de las tandas a partir de una playlist;
<i>Control diapos</i> va pasando las diapos durante la milonga.</li>
</ol>
<h4>Formato de las tags</h4>
<table cellpadding=3>
<tr><td><b>Artista</b></td><td>Orquesta / Cantor &nbsp; (varios: A y B)</td></tr>
<tr><td><b>Fecha</b></td><td>AAAA-MM-DD &nbsp; (o AAAA si solo se sabe el año)</td></tr>
<tr><td><b>Género</b></td><td>tango, tango vals, tango milonga…</td></tr>
<tr><td><b>Compositor</b></td><td>Musica: X - Letra: Y &nbsp; (siempre; ? si no se sabe)</td></tr>
</table>
<p>Si un dato no se conoce en la base de datos, esa tag del archivo no se toca. El compositor se escribe siempre: <i>Musica: ? - Letra: ?</i> indica que la canción ya pasó por la base de datos.</p>
"""


def categoria_de(archivo):
    if getattr(archivo, "perfect_match", False):
        return "perfecta"
    if getattr(archivo, "artist_not_found", False):
        return "sin_artista"
    if getattr(archivo, "title_not_found", False):
        return "sin_titulo"
    if getattr(archivo, "hay_coincidencia_preferida", False):
        return "preferida"
    return "dudosa"


def texto(valor):
    return "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor)


def tags_actuales(archivo):
    t = archivo.tags
    return {k: texto(getattr(t, k, "")) for k in ("title", "artist", "year", "genre", "composer")}


class tango_tags_qt_ventana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_store = Database()
        self.settings = QSettings("TangoTags", "TangoTags")
        self.archivos = []          # objetos FILETOFINDQT cargados
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
        self.mensaje_inicial = QLabel(
            "<p style='font-size:15px; color:#555'>Empieza cargando canciones con los botones de "
            "<b>① Cargar</b> (arriba a la izquierda).<br>Menú <b>Ayuda</b> para ver cómo funciona.</p>")
        self.mensaje_inicial.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mensaje_inicial, 1)
        self.tabla.hide()
        self.setCentralWidget(central)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)
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
        tb.addAction(self.accion("Desmarcar\ntodo", self.icono(estandar=QStyle.SP_DialogResetButton),
                                 self.desmarcar_todo, "Quitar todas las marcas de 'Usar'"))
        tb.addAction(self.accion("Buscar\nen BD", self.icono("searchdb"), self.buscar_en_bd,
                                 "Buscar en la base de datos. Si hay una canción seleccionada, "
                                 "puedes asignarle el resultado", "Ctrl+F"))
        tb.addAction(self.accion("Parar\nmúsica", self.icono("stop"), self.stop_music,
                                 "Detener la reproducción", "Esc"))
        tb.addSeparator()

        titulo_seccion("③ Aplicar")
        aplicar = self.accion("Aplicar\ntags", self.icono("transfer"), self.aplicar_tags,
                              "Escribir en los archivos las tags marcadas en 'Usar' "
                              "(antes se muestra un resumen para confirmar)", "Ctrl+S")
        tb.addAction(aplicar)
        tb.widgetForAction(aplicar).setStyleSheet("QToolButton{font-weight:bold; color:#1b5e20;}")
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
        m_archivo.addAction("Salir", self.close)

        m_opciones = mb.addMenu("&Opciones")
        self.opt_fecha = m_opciones.addAction("Usar la fecha del archivo para elegir la sugerida")
        self.opt_fecha.setCheckable(True)
        self.opt_fecha.setChecked(self.settings.value("opt_fecha", DEFAULT_DATE_CHECKED, type=bool))
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
            cb.setChecked(self.settings.value(f"mostrar_{clave}", True, type=bool))
            cb.setToolTip(explicacion)
            cb.stateChanged.connect(self.rellenar_tabla)
            self.filtros[clave] = cb
            lay.addWidget(cb)
        lay.addStretch(1)
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
        h = t.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)
        for col, ancho in ((COL_ESTADO, 105), (COL_ANO, 85), (COL_GENERO, 90), (COL_PLAY, 32),
                           (COL_USAR, 42), (COL_BD_FECHA, 90), (COL_BD_ESTILO, 95),
                           (COL_BD_PLAY30, 42), (COL_BD_PLAY10, 42)):
            h.setSectionResizeMode(col, QHeaderView.Fixed)
            t.setColumnWidth(col, ancho)
        for col in (COL_TITULO, COL_ARTISTA, COL_COMPOSITOR, COL_BD_TITULO, COL_BD_ORQUESTA,
                    COL_BD_CANTOR, COL_BD_COMPOSITOR):
            h.setSectionResizeMode(col, QHeaderView.Stretch)
        cabecera_bd = QColor("#e3f2fd")
        for col in range(COL_USAR, len(CABECERAS)):
            t.horizontalHeaderItem(col).setBackground(cabecera_bd)
            t.horizontalHeaderItem(col).setToolTip("Datos de la base de datos (con el formato final)")
        t.itemChanged.connect(self.on_item_changed)
        t.cellClicked.connect(self.on_cell_clicked)
        t.cellDoubleClicked.connect(self.on_cell_double_clicked)
        return t

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
        QApplication.processEvents()
        try:
            biblioteca = MusicBeeLibraryTools(None, ruta).library_df
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer la biblioteca:\n{e}")
            return
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

        self.progress_bar.setMaximum(len(rutas_y_tags))
        self.progress_bar.show()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for i, (ruta, tags) in enumerate(rutas_y_tags, 1):
                self.progress_bar.setValue(i)
                self.statusBar().showMessage(f"Buscando en la base de datos… {i} de {len(rutas_y_tags)}")
                QApplication.processEvents()
                if not os.path.exists(ruta):
                    no_encontrados.append(ruta)
                    continue
                try:
                    archivo = FILETOFINDQT(ruta, [None] * 4, 0,
                                           [self.opt_fecha.isChecked(), True, True, True, True, False],
                                           tags=tags)
                except Exception as e:
                    print(f"Error procesando {ruta}: {e}")
                    no_encontrados.append(ruta)
                    continue
                archivo.categoria = categoria_de(archivo)
                archivo.estado_guardado = None
                coincidencias = getattr(archivo, "coincidencias", None)
                hay = coincidencias is not None and not coincidencias.empty
                archivo.seleccion = (archivo.coincidencia_preferida
                                     if hay and archivo.categoria in ("perfecta", "preferida") else None)
                self.archivos.append(archivo)
                if self.opt_guardar_coinc.isChecked():
                    fav = archivo.get_coincidencia_favorita()
                    if fav is not None:
                        favoritas.append(fav)
        finally:
            QApplication.restoreOverrideCursor()
            self.progress_bar.hide()

        if favoritas:
            utils.guardar_archivo_output(tipo='coincidencias', dataframe=pd.concat(favoritas, ignore_index=True))
        if self.opt_guardar_resid.isChecked() and residuos:
            utils.guardar_archivo_output(
                tipo='residuos', encabezados=f"Origen: {origen}\n",
                dataframe=pd.DataFrame(residuos, columns=['Titulo Archivo', 'Titulo base de datos',
                                                          'Residuo', 'Ruta completa']))

        self.actualizar_contadores()
        self.rellenar_tabla()
        resumen = self.resumen()
        self.statusBar().showMessage(f"{os.path.basename(origen) or origen}: {resumen}")
        if no_encontrados:
            QMessageBox.warning(
                self, "Archivos no encontrados",
                f"{len(no_encontrados)} archivo(s) no existen o no se pudieron leer:\n\n"
                + "\n".join(no_encontrados[:15]) + ("\n…" if len(no_encontrados) > 15 else ""))

    def resumen(self):
        cuenta = pd.Series([a.categoria for a in self.archivos]).value_counts()
        partes = [f"{cuenta.get(k, 0)} {CATEGORIAS[k][1].lower()}" for k in CATEGORIAS if cuenta.get(k, 0)]
        return f"{len(self.archivos)} canciones — " + ", ".join(partes)

    def actualizar_contadores(self):
        cuenta = pd.Series([a.categoria for a in self.archivos], dtype=object).value_counts()
        for clave, cb in self.filtros.items():
            cb.setText(f"{CATEGORIAS[clave][1]} ({cuenta.get(clave, 0)})")

    def borrar_todo(self):
        self.archivos = []
        self.fila_a_archivo = {}
        self.tabla.setRowCount(0)
        self.tabla.hide()
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
            self.mensaje_inicial.setText(
                f"<p style='font-size:15px; color:#555'>Las {len(self.archivos)} canciones cargadas están "
                f"ocultas por los filtros de <b>Mostrar</b>.<br>Marca las casillas de arriba para verlas.</p>")
            self.mensaje_inicial.show()
            return
        self.mensaje_inicial.hide()
        self.tabla.show()
        filas = sum(max(1, len(self.coincidencias(a))) for a in visibles)

        self._rellenando = True
        self.tabla.setUpdatesEnabled(False)
        self.tabla.clearSpans()
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(filas)
        self.fila_a_archivo = {}
        fila = 0
        for n, archivo in enumerate(visibles):
            fondo = QColor("#ffffff") if n % 2 == 0 else QColor("#f5f5f5")
            inicio = fila
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
        it = self.item(estado, color, tooltip=CATEGORIAS[archivo.categoria][2])
        it.setFont(QFont("", -1, QFont.Bold))
        self.tabla.setItem(fila, COL_ESTADO, it)
        ruta = archivo.ruta_archivo
        for col, clave in ((COL_TITULO, "title"), (COL_ARTISTA, "artist"), (COL_ANO, "year"),
                           (COL_GENERO, "genre"), (COL_COMPOSITOR, "composer")):
            self.tabla.setItem(fila, col, self.item(actuales[clave], fondo,
                                                    tooltip=f"{actuales[clave]}\n\n{ruta}"))
        play = self.item("▶", fondo, tooltip="Escuchar el archivo")
        play.setTextAlignment(Qt.AlignCenter)
        self.tabla.setItem(fila, COL_PLAY, play)

    def pintar_sin_coincidencias(self, fila, fondo):
        for col in range(COL_USAR, len(CABECERAS)):
            self.tabla.setItem(fila, col, self.item("", fondo))
        aviso = self.item("— sin coincidencias: doble clic aquí para buscar en la BD —", fondo,
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
        self.tabla.setItem(fila, COL_USAR, usar)

        for col, (campo, formatear) in COLUMNAS_BD.items():
            original = texto(coincidencia.get(campo, ""))
            valor = formatear(original)
            tip = valor if valor == original else f"{valor}\n(en la base de datos: {original!r})"
            color = fondo
            if colores is not None and indice in colores.index and COLORES_COLUMNA[col] in colores.columns:
                color = QColor(COLORES_SUAVES.get(colores.at[indice, COLORES_COLUMNA[col]], fondo))
            self.tabla.setItem(fila, col, self.item(valor, color, editable=True, tooltip=tip))

        for col, campo in ((COL_BD_PLAY30, "audio30"), (COL_BD_PLAY10, "audio10")):
            hay_audio = bool(texto(coincidencia.get(campo, "")).strip())
            it = self.item("▶" if hay_audio else "", fondo,
                           tooltip="Escuchar el fragmento de la base de datos" if hay_audio else "")
            it.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(fila, col, it)

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
        elif item.column() in COLUMNAS_BD:
            # Edición manual: se guarda en las coincidencias para que no se pierda al filtrar
            campo = COLUMNAS_BD[item.column()][0]
            columna = archivo.coincidencias.columns.get_loc(campo)
            archivo.coincidencias = archivo.coincidencias.copy()
            archivo.coincidencias.iat[pos, columna] = item.text()
            item.setToolTip(item.text())

    def on_cell_clicked(self, fila, col):
        if fila not in self.fila_a_archivo:
            return
        archivo, pos = self.fila_a_archivo[fila]
        if col == COL_PLAY:
            self.reproducir_audio(archivo.ruta_archivo)
        elif col in (COL_BD_PLAY30, COL_BD_PLAY10) and pos is not None:
            enlace = texto(self.coincidencias(archivo).iloc[pos].get(
                "audio30" if col == COL_BD_PLAY30 else "audio10", "")).strip()
            if enlace:
                self.reproducir_audio(utils.link_to_music(enlace))

    def on_cell_double_clicked(self, fila, col):
        if fila not in self.fila_a_archivo:
            return
        archivo, pos = self.fila_a_archivo[fila]
        if col in COLUMNAS_ARCHIVO and col != COL_PLAY:
            self.mostrar_detalles(archivo)
        elif pos is None and col >= COL_USAR:
            self.buscar_en_bd(archivo)

    def marcar_sugeridas(self):
        for a in self.archivos:
            if a.categoria in ("perfecta", "preferida") and not self.coincidencias(a).empty:
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
    def aplicar_tags(self):
        cambios, sin_cambios = [], 0
        for archivo in self.archivos:
            if archivo.seleccion is None:
                continue
            nuevas = tags_desde_coincidencia(self.coincidencias(archivo).iloc[archivo.seleccion])
            actuales = tags_actuales(archivo)
            # Solo se escriben los campos con valor nuevo y distinto
            diferencias = {k: v for k, v in nuevas.items() if v and v != actuales[k]}
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

        errores = 0
        self.progress_bar.setMaximum(len(cambios))
        self.progress_bar.show()
        for i, (archivo, _, _, diferencias) in enumerate(cambios, 1):
            self.progress_bar.setValue(i)
            self.statusBar().showMessage(f"Escribiendo tags… {i} de {len(cambios)}")
            QApplication.processEvents()
            ok = utils.update_tags(archivo.ruta_archivo, title=diferencias.get("title"),
                                   artist=diferencias.get("artist"), year=diferencias.get("year"),
                                   genre=diferencias.get("genre"), composer=diferencias.get("composer"))
            archivo.estado_guardado = ok
            if ok:
                try:
                    archivo.tags = utils.leer_tags(archivo.ruta_archivo)
                except Exception:
                    pass
            else:
                errores += 1
        self.progress_bar.hide()
        self.rellenar_tabla()

        mensaje = f"Tags escritas en {len(cambios) - errores} archivo(s)."
        if errores:
            mensaje += f"\n{errores} archivo(s) dieron error (marcados en rojo en la columna Estado)."
        self.statusBar().showMessage(mensaje.replace("\n", " "))
        (QMessageBox.warning if errores else QMessageBox.information)(self, "Tags aplicadas", mensaje)

    # ------------------------------------------------------------------ búsqueda en BD
    def buscar_en_bd(self, archivo=None):
        if not isinstance(archivo, FILETOFINDQT):
            archivo = self.archivo_seleccionado()
        dialogo = DialogoBuscarBD(self, self.data_store.get_db(), archivo)
        if dialogo.exec_() == QDialog.Accepted and archivo is not None and dialogo.fila_elegida is not None:
            fila = dialogo.fila_elegida
            actuales = self.coincidencias(archivo)
            if fila.name in actuales.index:
                archivo.seleccion = actuales.index.get_loc(fila.name)
            else:
                archivo.coincidencias = pd.concat([actuales, fila.to_frame().T])
                archivo.seleccion = len(archivo.coincidencias) - 1
            self.rellenar_tabla()

    # ------------------------------------------------------------------ audio y diapos
    def reproducir_audio(self, ruta):
        try:
            pygame.mixer.music.load(ruta)
            pygame.mixer.music.play()
            self.statusBar().showMessage(f"Reproduciendo: {os.path.basename(ruta)}  (Esc para parar)")
        except Exception as e:
            self.statusBar().showMessage(f"No se puede reproducir {os.path.basename(ruta)}: {e}")

    def stop_music(self):
        try:
            pygame.mixer.music.stop()
            self.statusBar().showMessage("Música detenida")
        except Exception as e:
            self.statusBar().showMessage(f"Error deteniendo la música: {e}")

    def lanzar_script(self, script):
        python = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(python):
            python = sys.executable
        subprocess.Popen([python, os.path.join(PROJECT_ROOT, script)], cwd=PROJECT_ROOT)
        self.statusBar().showMessage(f"Abriendo {script}…")

    def abrir_crear_diapos(self):
        self.lanzar_script("crear_diapos.py")

    def abrir_control_diapos(self):
        self.lanzar_script("control_slides.py")

    def mostrar_ayuda(self):
        caja = QMessageBox(self)
        caja.setWindowTitle("Ayuda — TangoTags")
        caja.setTextFormat(Qt.RichText)
        caja.setText(TEXTO_AYUDA)
        caja.exec_()

    def closeEvent(self, event):
        for clave in ("opt_fecha", "opt_guardar_coinc", "opt_guardar_resid"):
            self.settings.setValue(clave, getattr(self, clave).isChecked())
        event.accept()


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


class DialogoBuscarBD(QDialog):
    """Búsqueda libre en la base de datos; opcionalmente asigna el resultado a una canción."""

    MAX_RESULTADOS = 500
    COLUMNAS = (("titulo", "Título"), ("artista", "Orquesta"), ("cantor", "Cantor"),
                ("fecha", "Fecha"), ("estilo", "Estilo"), ("compositor_autor", "Compositor"))

    def __init__(self, parent, db, archivo=None):
        super().__init__(parent)
        self.db = db
        self.archivo = archivo
        self.fila_elegida = None
        self.resultados = db.iloc[0:0]
        self.setWindowTitle("Buscar en la base de datos")
        self.resize(1200, 650)
        lay = QVBoxLayout(self)

        if archivo is not None:
            t = tags_actuales(archivo)
            lay.addWidget(QLabel(f"Buscando para: <b>{t['title'] or os.path.basename(archivo.ruta_archivo)}</b>"
                                 f" — {t['artist']} ({t['year']})"))

        form = QGridLayout()
        self.campos = {}
        for i, (clave, nombre) in enumerate((("titulo", "Título"), ("artista", "Orquesta"),
                                             ("cantor", "Cantor"))):
            form.addWidget(QLabel(nombre + ":"), 0, i * 2)
            e = QLineEdit()
            e.returnPressed.connect(self.buscar)
            form.addWidget(e, 0, i * 2 + 1)
            self.campos[clave] = e
        form.addWidget(QLabel("Año desde:"), 1, 0)
        self.desde = QLineEdit()
        self.desde.setMaximumWidth(80)
        form.addWidget(self.desde, 1, 1, Qt.AlignLeft)
        form.addWidget(QLabel("hasta:"), 1, 2)
        self.hasta = QLineEdit()
        self.hasta.setMaximumWidth(80)
        form.addWidget(self.hasta, 1, 3, Qt.AlignLeft)
        for e in (self.desde, self.hasta):
            e.returnPressed.connect(self.buscar)
        boton = QPushButton("Buscar")
        boton.clicked.connect(self.buscar)
        form.addWidget(boton, 1, 5)
        lay.addLayout(form)

        self.tabla = QTableWidget(0, len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels([n for _, n in self.COLUMNAS])
        self.tabla.verticalHeader().hide()
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setSortingEnabled(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.cellDoubleClicked.connect(lambda *_: self.usar())
        lay.addWidget(self.tabla)
        self.info = QLabel("")
        lay.addWidget(self.info)

        botones = QDialogButtonBox()
        if archivo is not None:
            usar = botones.addButton("Usar para esta canción", QDialogButtonBox.AcceptRole)
            usar.clicked.connect(self.usar)
        botones.addButton("Cerrar", QDialogButtonBox.RejectRole).clicked.connect(self.reject)
        lay.addWidget(botones)

        if archivo is not None:
            from src.utils.utils import separar_artistas
            t = tags_actuales(archivo)
            orquesta, _ = separar_artistas(t["artist"])
            self.campos["titulo"].setText(t["title"])
            self.campos["artista"].setText(orquesta)
            self.buscar()

    @staticmethod
    def normalizar(serie):
        return serie.astype(str).map(lambda s: unidecode(s).lower())

    def buscar(self):
        r = self.db
        for clave, e in self.campos.items():
            q = unidecode(e.text().strip()).lower()
            if q:
                r = r[self.normalizar(r[clave]).str.contains(q, regex=False)]
        anos = pd.to_numeric(r["fecha"].astype(str).str[:4], errors="coerce")
        if self.desde.text().strip().isdigit():
            r = r[anos >= int(self.desde.text())]
            anos = anos.loc[r.index]
        if self.hasta.text().strip().isdigit():
            r = r[anos <= int(self.hasta.text())]
        total = len(r)
        self.resultados = r.head(self.MAX_RESULTADOS)

        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(len(self.resultados))
        for i, (indice, fila) in enumerate(self.resultados.iterrows()):
            for c, (clave, _) in enumerate(self.COLUMNAS):
                it = QTableWidgetItem(texto(fila[clave]))
                it.setData(Qt.UserRole, indice)
                it.setToolTip(texto(fila[clave]))
                self.tabla.setItem(i, c, it)
        self.tabla.setSortingEnabled(True)
        self.info.setText(f"{total} resultado(s)" +
                          (f", se muestran los primeros {self.MAX_RESULTADOS}" if total > self.MAX_RESULTADOS else "")
                          + (" — doble clic para usarlo" if self.archivo is not None else ""))

    def usar(self):
        if self.archivo is None:
            return
        filas = self.tabla.selectionModel().selectedRows()
        if not filas:
            QMessageBox.information(self, "Elige una fila", "Selecciona primero un resultado de la lista.")
            return
        indice = self.tabla.item(filas[0].row(), 0).data(Qt.UserRole)
        self.fila_elegida = self.db.loc[indice]
        self.accept()
