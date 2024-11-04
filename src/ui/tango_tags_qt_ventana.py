from PyQt5.QtCore import Qt, QSize, QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QFont, QColor, QIcon, QBrush, QPixmap, QLinearGradient
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QToolBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QHeaderView, QSpinBox, QDialog, QPushButton, QFileDialog, QComboBox, QLineEdit, QCheckBox, QFrame, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QIcon
import sys
import pandas as pd
from src.config.config import *
from src.config.database import Database
from src.utils.calcular_ancho_fuentes import FontWidthCalculator
from src.utils.MusicBeeLibraryTools import MusicBeeLibraryTools

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

        # Modo de pantalla completa y maximizada
        if self.full_screen:
            self.showFullScreen()
        elif self.maximized:
            self.showMaximized()

        # Crear menús, barra de iconos y barra de estado
        self.create_icon_bar()
        self.create_status_bar()

        # Configuración de layout principal
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Área principal de contenido
        self.main_content_area = QFrame()
        main_layout.addWidget(self.main_content_area)

    def create_icon_bar(self):
        # Barra de herramientas para iconos
        self.toolbar = QToolBar("Icon Bar")
        self.addToolBar(self.toolbar)
        self.toolbar.setIconSize(QSize(32, 32))

        # Botón para semana anterior
        music_bee_btn = QAction(QIcon('ressources/icons/musicbee.png'), "Load Musicbee", self)
        music_bee_btn.triggered.connect(self.load_music_bee)
        self.toolbar.addAction(music_bee_btn)

    def create_status_bar(self):
        self.statusBar().showMessage("Ready")

    def load_music_bee(self):
        """Abrir un cuadro de diálogo para seleccionar el archivo de biblioteca de MusicBee y procesarlo."""

        # Limpiar la lista de archivos existentes
        self.borrar_todo()
        numero_canciones = 0

        # Cuadro de diálogo para seleccionar el archivo de biblioteca
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
                QMessageBox.information(self, "Éxito", "¡Biblioteca cargada con éxito!")

            except Exception as e:
                # Mostrar mensaje de error si ocurre algún problema
                QMessageBox.critical(self, "Error", f"No se pudo cargar la biblioteca: {e}")

    def procesar_archivos(self, archivos, numero_canciones, from_playlist=False, from_musicbee=False,
                          show_progress=False, origen=None, tags=None):
        """Procesa una lista de archivos y actualiza la interfaz."""

        total_archivos = len(archivos)
        self.archivos_comparado = ReportManager()

        # Configurar la barra de progreso si es necesario
        if show_progress:
            self.setup_progress_bar()

        for index, archivo in enumerate(archivos):
            tags_aplicar = None

            # Actualizar progreso si es necesario
            if show_progress:
                self.update_progress_and_status(current=index + 1, total=total_archivos)

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