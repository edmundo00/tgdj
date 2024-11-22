from PyQt5.QtCore import Qt, QSize, QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QFont, QColor, QIcon, QBrush, QPixmap, QLinearGradient
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QToolBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QHeaderView, QSpinBox, QDialog, QPushButton, QFileDialog, QComboBox, QLineEdit, QCheckBox, QFrame,
    QFileDialog, QMessageBox, QProgressBar, QStatusBar, QApplication
)
from PyQt5.QtGui import QIcon
import sys
import pandas as pd
from src.config.config import *
from src.config.database import Database
from src.utils.calcular_ancho_fuentes import FontWidthCalculator
from src.utils.MusicBeeLibraryTools import MusicBeeLibraryTools
from src.ui.ReportManager import ReportManager
from src.ui.file_to_find_qt import FILETOFINDQT
from src.utils.utils import *

class tango_tags_qt_ventana(QMainWindow):
    def __init__(self):
        super().__init__()

        self.data_store = Database()

        self.df_reporte = pd.DataFrame()
        self.df_reporte_coincidencia_favorita = None
        self.origen_archivos = None
        self.owndb = None

        # Configuración de pantalla completa y maximizada
        self.full_screen = False
        self.maximized = True
        self.init_ui()

    def init_ui(self):
        # Propiedades de la ventana
        self.setWindowTitle("PyQt Window with Menu, Icon, and Status Bar")
        self.setGeometry(100, 100, 1700, 800)

        # Configuración del layout principal
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Crear menús, barra de iconos y barra de estado
        self.create_icon_bar()
        self.create_checkboxes()  # Añadir los CheckBoxes debajo de la barra de iconos
        self.create_status_bar()

        # Área principal de contenido con un layout
        self.main_content_area = QFrame()
        self.main_content_area.setLayout(QVBoxLayout())
        main_layout.addWidget(self.main_content_area)

        # Ajustar estiramientos para que solo el área principal crezca
        main_layout.setStretch(0, 0)  # Barra de iconos (altura fija)
        main_layout.setStretch(1, 0)  # Checkboxes (altura fija)
        main_layout.setStretch(2, 1)  # Área principal (expandible)

    def create_icon_bar(self):
        # Barra de herramientas para iconos
        self.toolbar = QToolBar("Icon Bar")
        self.toolbar.setIconSize(QSize(32, 32))
        self.toolbar.setFixedHeight(50)  # Ajustar la altura fija de la barra de herramientas
        self.addToolBar(self.toolbar)

        # Botón para cargar biblioteca de MusicBee
        music_bee_btn = QAction(QIcon(icon_paths.get("musicbee")), "Load Musicbee", self)
        music_bee_btn.triggered.connect(self.load_music_bee)
        self.toolbar.addAction(music_bee_btn)

        # Botón para parar música
        stop_music_btn = QAction(QIcon(icon_paths.get("stop")), "Stop Music", self)
        stop_music_btn.triggered.connect(self.stop_music)
        self.toolbar.addAction(stop_music_btn)

        # Botón para abrir playlist
        open_playlist_btn = QAction(QIcon(icon_paths.get("playlist")), "Open Playlist", self)
        open_playlist_btn.triggered.connect(self.load_playlist)
        self.toolbar.addAction(open_playlist_btn)

    def create_checkboxes(self):
        # Crear un frame para contener los CheckBoxes
        checkbox_frame = QFrame()
        checkbox_layout = QHBoxLayout()

        # Establecer altura fija para el frame de checkboxes
        checkbox_frame.setFixedHeight(50)  # Ajusta la altura según lo que necesites

        # Definir los CheckBoxes con sus textos, estados predeterminados y nombres de atributo
        checkboxes_info = [
            ("Date Checked", False, "date_checked"),
            ("Perfect Matches", True, "perfect_matches"),
            ("Artist Not Found", True, "artist_not_found"),
            ("Title Not Found", True, "title_not_found"),
            ("Visualizar Resto", True, "view_remaining"),
            ("Guardar coincidencias", False, "guardar_coincidencias"),
            ("Guardar residuos", False, "guardar_residuos"),
            ("No mostrar comparativa", False, "direct_comparison"),
            ("Direct tagging", False, "direct_tagging_checkbox")
        ]

        # Crear y añadir los CheckBoxes al layout y asignarlos como atributos de clase
        for text, checked, attribute_name in checkboxes_info:
            checkbox = QCheckBox(text)
            checkbox.setChecked(checked)
            checkbox.stateChanged.connect(self.crear_tabla_coincidencias)  # Conectar al método para actualizar la tabla
            checkbox_layout.addWidget(checkbox)

            # Asignar el checkbox a un atributo de la clase con el nombre especificado
            setattr(self, attribute_name, checkbox)

        # Añadir el layout al frame y el frame al layout principal
        checkbox_frame.setLayout(checkbox_layout)
        self.centralWidget().layout().addWidget(checkbox_frame)
    def create_status_bar(self):
        self.statusBar().showMessage("Ready")

    def load_playlist(self):
        """Abrir un cuadro de diálogo para seleccionar una playlist y procesar los archivos."""
        # Limpiar la lista de archivos existentes
        self.borrar_todo()
        numero_canciones = 0

        # Cuadro de diálogo para seleccionar el archivo de playlist
        playlist_file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de Playlist",
            m3u_start_path,  # Directorio inicial para buscar playlists
            "Archivos de Playlist (*.m3u *.m3u8);;Todos los archivos (*.*)"
        )

        if playlist_file_path:
            try:
                # Limpiar datos previos si es necesario
                if hasattr(self, 'df'):
                    self.df = self.df.iloc[0:0]  # Limpiar el DataFrame pero mantener las columnas

                self.m3u_audio_files = []  # Reiniciar la lista de archivos de audio

                # Usar un helper para cargar los archivos de la playlist
                lines = load_m3u_file_helper(playlist_file_path)

                # Configurar el origen y procesar los archivos
                self.origen_archivos = 'playlist'
                self.procesar_archivos(
                    lines,
                    numero_canciones,
                    from_playlist=True,
                    show_progress=True,
                    origen=playlist_file_path
                )

                # Mostrar un mensaje de éxito
                self.statusBar().showMessage(f"Playlist cargada: {playlist_file_path}")
                self.crear_tabla_coincidencias()

            except Exception as e:
                # Mostrar mensaje de error si ocurre algún problema
                QMessageBox.critical(self, "Error", f"No se pudo cargar la playlist: {e}")

    def load_music_bee(self):
        """Abrir un cuadro de diálogo para seleccionar el archivo de biblioteca de MusicBee y procesarlo."""

        # Limpiar la lista de archivos existentes
        self.borrar_todo()
        numero_canciones = 0

        # Cuadro de diálogo para seleccionar el archivo de biblioteca
        test = True
        if test:
            file_path = "D:\\Dropbox\\TDJ\\MUSICBEE DATABASES\\test\\MusicBeeLibrary.mbl"
            #file_path = "D:\\Dropbox\\TDJ\\MUSICBEE DATABASES\\tango\\MusicBeeLibrary.mbl"
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar archivo de biblioteca de MusicBee",
                "",
                "Archivos de biblioteca de MusicBee (*.mbl);;Todos los archivos (*.*)"
            )

        if file_path:
            try:
                # Inicializar MusicBeeLibraryTools con el archivo seleccionado
                self.musicbee_tool = MusicBeeLibraryTools(self, file_path)
                self.musicbee_tool.parse_library()

                # Obtener la lista de rutas de archivos y los tags del DataFrame de la biblioteca
                lines = self.musicbee_tool.library_df['file_path'].tolist()
                tagsml_df = self.musicbee_tool.library_df[['title', 'artist', 'year', 'genre', 'composer', 'file_path']]

                # Configurar el origen y procesar los archivos
                self.origen_archivos = 'musicbee'
                self.procesar_archivos(
                    lines,
                    numero_canciones,
                    from_musicbee=True,
                    show_progress=True,
                    origen=file_path,
                    tags=tagsml_df
                )

                # Mostrar mensaje de éxito
                # QMessageBox.information(self, "Éxito", "¡Biblioteca cargada con éxito!")
                self.crear_tabla_coincidencias()

            except Exception as e:
                # Mostrar mensaje de error si ocurre algún problema
                QMessageBox.critical(self, "Error", f"No se pudo cargar la biblioteca: {e}")

    def crear_y_actualizar_filetofind(self, ruta_archivo, frame_number, tags):
        """
        Crea una instancia de FILETOFIND, la actualiza según los filtros seleccionados,
        y la añade a la lista global de filetofind_list.
        """
        # Crear instancia de FILETOFIND con los parámetros constantes
        lista_frames = [None, None, None, None]

        lista_checks = [
            self.date_checked.isChecked(),  # Corresponds to show_date_checked
            self.perfect_matches.isChecked(),  # Corresponds to show_perfect_matches
            self.artist_not_found.isChecked(),  # Corresponds to show_artist_not_found
            self.title_not_found.isChecked(),  # Corresponds to show_title_not_found
            self.view_remaining.isChecked(),  # Corresponds to show_remaining
            self.direct_comparison.isChecked()  # Corresponds to compare
        ]

        # Pass the list as a single argument along with other parameters
        new_filetofind = FILETOFINDQT(
            ruta_archivo=ruta_archivo,
            lista_frames=lista_frames,
            frame_number=frame_number,
            lista_checks=lista_checks,
            tags=tags
        )

        # Actualizar el número de canciones y añadir a la lista global
        frame_number = new_filetofind.nextframe
        reporte = new_filetofind.reporte()
        coinc_fav = new_filetofind.get_coincidencia_favorita()

        filetofind_list.append(new_filetofind)

        return frame_number, reporte, coinc_fav

    def crear_tabla_coincidencias(self):
        """Crea una tabla en la ventana con las coincidencias de filetofind_list."""
        if not filetofind_list:
            return

        # Limpiar el contenido previo
        for i in reversed(range(self.main_content_area.layout().count())):
            widget_to_remove = self.main_content_area.layout().itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.deleteLater()

        # Mapeo de columnas en colores a columnas de coincidencias
        color_mapping = {
            "ORQUESTA": "Artista DB",
            "TITULO": "Título DB",
            "CANTOR": "Cantor DB",
            "FECHA": "Fecha DB",
            "COMPOSITOR": "Compositor/Autor",
        }

        rows = []
        colores_rows = []  # Lista para almacenar los colores de cada fila
        merge_ranges = []
        current_row = 0

        # Obtener los estados de los CheckBoxes
        check_perfect_matches = self.perfect_matches.isChecked()
        check_artist_not_found = self.artist_not_found.isChecked()
        check_title_not_found = self.title_not_found.isChecked()
        check_view_remaining = self.view_remaining.isChecked()

        for archivo in filetofind_list:
            # Saltar si el archivo no cumple con ninguno de los filtros
            if (
                    (not check_perfect_matches and getattr(archivo, 'perfect_match', False)) or
                    (not check_artist_not_found and getattr(archivo, 'artist_not_found', False)) or
                    (not check_title_not_found and getattr(archivo, 'title_not_found', False)) or
                    (not check_view_remaining and not any([
                        getattr(archivo, 'perfect_match', False),
                        getattr(archivo, 'artist_not_found', False),
                        getattr(archivo, 'title_not_found', False)
                    ]))
            ):
                continue

            coincidencias = getattr(archivo, 'coincidencias', None)
            colores_fila = getattr(archivo, 'colores_labels', None)  # Obtener los colores desde el archivo
            start_row = current_row

            if coincidencias is None or coincidencias.empty:
                # Si no hay coincidencias, no añadimos colores
                rows.append({
                    "Info": "",
                    "Título": archivo.tags.title if hasattr(archivo.tags, 'title') else "",
                    "Artista": archivo.tags.artist if hasattr(archivo.tags, 'artist') else "",
                    "Año": archivo.tags.year if hasattr(archivo.tags, 'year') else "",
                    "Género": archivo.tags.genre if hasattr(archivo.tags, 'genre') else "",
                    "Compositor": archivo.tags.composer if hasattr(archivo.tags, 'composer') else "",
                    "Audio": archivo.ruta_archivo,
                    "Check": "",
                    "Audio30": "",
                    "Audio10": "",
                    "Título DB": "",
                    "Artista DB": "",
                    "Cantor DB": "",
                    "Fecha DB": "",
                    "Estilo DB": "",
                    "Compositor/Autor": "",
                    "InfoDB": ""
                })
                colores_rows.append([])  # Añadir fila vacía de colores
                current_row += 1
            else:
                for idx, (coincidencia_idx, coincidencia) in enumerate(coincidencias.iterrows()):
                    rows.append({

                        "Info": "",
                        "Título": archivo.tags.title if hasattr(archivo.tags, 'title') else "",
                        "Artista": archivo.tags.artist if hasattr(archivo.tags, 'artist') else "",
                        "Año": archivo.tags.year if hasattr(archivo.tags, 'year') else "",
                        "Género": archivo.tags.genre if hasattr(archivo.tags, 'genre') else "",
                        "Compositor": archivo.tags.composer if hasattr(archivo.tags, 'composer') else "",
                        "Audio": archivo.ruta_archivo,
                        "Check": "",
                        "Audio30": link_to_music(coincidencia.get("audio30", "")),
                        "Audio10": link_to_music(coincidencia.get("audio10", "")),
                        "Título DB": coincidencia.get("titulo", ""),
                        "Artista DB": coincidencia.get("artista", ""),
                        "Cantor DB": coincidencia.get("cantor", ""),
                        "Fecha DB": coincidencia.get("fecha", ""),
                        "Estilo DB": coincidencia.get("estilo", ""),
                        "Compositor/Autor": coincidencia.get("compositor_autor", ""),
                        "InfoDB": ""
                    })

                    # Agregar los colores correspondientes si el índice está presente
                    if colores_fila is not None and coincidencia_idx in colores_fila.index:
                        colores_rows.append(colores_fila.loc[coincidencia_idx])
                    else:
                        colores_rows.append([])  # Fila sin colores
                    current_row += 1

            merge_ranges.append((start_row, current_row - 1))

        if not rows:
            return

        # Crear el QTableWidget
        table_widget = QTableWidget()
        table_widget.setRowCount(len(rows))
        table_widget.setColumnCount(len(rows[0]))
        table_widget.setHorizontalHeaderLabels(rows[0].keys())

        # Llenar la tabla con los datos
        for row_idx, row_data in enumerate(rows):
            for col_idx, (key, value) in enumerate(row_data.items()):
                if key in ["Info", "InfoDB"]:
                    self.crear_boton_info(table_widget, row_idx, col_idx, icon_paths.get("info"))
                elif key == "Check":
                    self.crear_checkbox(table_widget, row_idx, col_idx)
                elif key in ["Audio", "Audio30", "Audio10"] and value:
                    self.crear_boton_reproduccion(table_widget, value, row_idx, col_idx, icon_paths.get("play"))
                else:
                    item = QTableWidgetItem(str(value))
                    # Aplicar colores si están definidos
                    if key in color_mapping.values() and len(colores_rows[row_idx]) > 0:
                        color_idx = list(color_mapping.values()).index(key)
                        if color_idx < len(colores_rows[row_idx]):
                            color = colores_rows[row_idx].iloc[color_idx]
                            item.setBackground(QColor(color))
                    table_widget.setItem(row_idx, col_idx, item)

        # Realizar merge de celdas
        for start, end in merge_ranges:
            if start != end:  # Fusionar solo si hay múltiples filas
                for col in range(7):  # Fusionar las columnas necesarias
                    table_widget.setSpan(start, col, end - start + 1, 1)

        # Configurar el modo de redimensionado para cada columna
        header = table_widget.horizontalHeader()
        for col_idx, key in enumerate(rows[0].keys()):
            if key in ["Info", "InfoDB", "Check", "Audio", "Audio30", "Audio10"]:
                header.setSectionResizeMode(col_idx, QHeaderView.Fixed)  # Fijar la columna
                table_widget.setColumnWidth(col_idx, 40)  # Ancho fijo de 40 píxeles
            else:
                header.setSectionResizeMode(col_idx, QHeaderView.Stretch)  # El resto se estira

        # Añadir la tabla al área principal
        self.main_content_area.layout().addWidget(table_widget)

    def crear_boton_info(self, parent, row, column, info_icon_path):
        """Crea un botón en la columna Info que abre una ventana emergente."""
        boton_info = QPushButton(parent)
        boton_info.setIcon(QIcon(info_icon_path))
        boton_info.clicked.connect(lambda: self.abrir_ventana_info(row))
        parent.setCellWidget(row, column, boton_info)

    def crear_checkbox(self, parent, row, column):
        """Crea un checkbox en la columna Check y lo centra."""
        checkbox = QCheckBox(parent)
        checkbox.setToolTip("Marcar/Desmarcar")

        # Crear un widget contenedor con un layout centrado
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)  # Sin márgenes

        # Añadir el contenedor al QTableWidget
        parent.setCellWidget(row, column, container)

    def abrir_ventana_info(self, row):
        """Abre una ventana emergente con información adicional."""
        QMessageBox.information(self, "Información", f"Detalles de la fila {row}")

    def setup_progress_bar(self):
        self.progress_bar = QProgressBar(self)
        self.statusBar().addWidget(self.progress_bar)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)

    def update_progress_and_status(self, current, total):
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.statusBar().showMessage(f"Procesando archivo {current} de {total}")

    def cleanup_progress_bar(self):
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Procesamiento completado")

    def procesar_archivos(self, archivos, numero_canciones, from_playlist=False, from_musicbee=False,
                          show_progress=True, origen=None, tags=None):
        """Procesa una lista de archivos y actualiza la interfaz."""

        total_archivos = len(archivos)
        self.archivos_comparado = ReportManager()

        # Configurar la barra de progreso si es necesario
        # Configurar la barra de progreso si es necesario
        if show_progress:
            self.setup_progress_bar()

        for index, archivo in enumerate(archivos):
            tags_aplicar = None

            # Actualizar progreso si es necesario
            if show_progress:
                self.update_progress_and_status(current=index + 1, total=total_archivos)
                QApplication.processEvents()

            # Procesar cada archivo
            if from_playlist and not os.path.exists(archivo):
                # Manejar caso especial de rutas modificadas en playlists
                modified_path = dropbox_path + archivo.split("Dropbox", 1)[1]
                if os.path.exists(modified_path):
                    archivo = modified_path

            if from_musicbee and os.path.exists(archivo):
                # Extraer tags correspondientes desde MusicBee
                tags_aplicar = tags.iloc[index].tolist()

            if os.path.exists(archivo):
                numero_canciones, report_archivo, coinc_fav = self.crear_y_actualizar_filetofind(
                    ruta_archivo=archivo,
                    frame_number=numero_canciones,
                    tags=tags_aplicar
                )

                self.archivos_comparado.add_row(report_archivo)

                # Actualizar DataFrame de coincidencias favoritas si está habilitado
                if self.guardar_coincidencias.isChecked():
                    self.df_reporte_coincidencia_favorita = pd.concat(
                        [self.df_reporte_coincidencia_favorita, coinc_fav], ignore_index=True)

            if show_progress:
                # Asegurarse de que la interfaz se actualice correctamente
                QApplication.processEvents()

        # Finalizar el reporte y establecer el índice
        self.archivos_comparado.finalize_report()

        # Mostrar popup informativo si es necesario
        if showpopupinfo:
            self.mostrar_popup_reporte(self.archivos_comparado.report_df)

        # Guardar coincidencias si está habilitado
        if self.guardar_coincidencias.isChecked():
            guardar_archivo_output(tipo='coincidencias', dataframe=self.df_reporte_coincidencia_favorita,
                                   encabezados=None)

        # Guardar residuos si está habilitado
        if self.guardar_residuos.isChecked():
            residuos_df = pd.DataFrame(residuos,
                                       columns=['Titulo Archivo', 'Titulo base de datos', 'Residuo', 'Ruta completa'])
            guardar_archivo_output(tipo='residuos', dataframe=residuos_df, encabezados=f"Origen: {origen}\n")

        # Limpiar la barra de progreso si fue utilizada
        if show_progress:
            self.cleanup_progress_bar()

    def borrar_todo(self):
        for archivos in filetofind_list:
            archivos.destroy()
        filetofind_list.clear()

    def closeEvent(self, event):
        """Gestiona el evento de cierre para limpieza si es necesario."""
        event.accept()

    def crear_boton_reproduccion(self, parent, audio_path, row, column, play_icon_path):
        """
        Crea un botón de reproducción en un layout específico.
        Args:
            parent: Tabla o layout donde añadir el botón.
            audio_path: Ruta del archivo de audio.
            row: Fila donde colocar el botón.
            column: Columna donde colocar el botón.
            play_icon_path: Ruta al icono de reproducción.
        """
        boton_play = QPushButton(parent)
        boton_play.setIcon(QIcon(play_icon_path))
        boton_play.setIconSize(QSize(25, 25))
        boton_play.setToolTip("Reproducir audio")
        boton_play.clicked.connect(lambda: self.reproducir_audio(audio_path))
        parent.setCellWidget(row, column, boton_play)

    def reproducir_audio(self, audio_path):
        """
        Reproduce el archivo de audio.
        Args:
            audio_path: Ruta del archivo de audio.
        """
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error reproduciendo el archivo {audio_path}: {e}")

    def stop_music(self):
        """
        Detiene la reproducción de música si Pygame está sonando.
        """
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                self.statusBar().showMessage("Música detenida")
            else:
                self.statusBar().showMessage("No hay música reproduciéndose")
        except Exception as e:
            self.statusBar().showMessage(f"Error deteniendo la música: {e}")