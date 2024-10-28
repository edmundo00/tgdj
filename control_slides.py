import os
import time
import win32com.client
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from unidecode import unidecode
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt5.QtCore import QTimer
import win32gui


#
#
# CREAR .EXE
# pip install pyinstaller
# pyinstaller --onefile --noconsole --clean --distpath . .\control_slides.py
#
# ---------------------
# Clase EventHandler para Monitoreo de Cambios en el Tracklist
# ---------------------
class TracklistEventHandler(FileSystemEventHandler):
    def __init__(self, slide_controller):
        self.slide_controller = slide_controller

    def on_modified(self, event):
        # Solo actúa si el archivo modificado es el tracklist especificado
        if event.src_path == self.slide_controller.tracklist_path:
            print(f"{event.src_path} ha sido modificado.")
            # Usa QTimer.singleShot para llamar a process_tracklist_change en el hilo principal
            QTimer.singleShot(0, self.slide_controller.process_tracklist_change)



# ---------------------
# Clase Principal de la Aplicación de Control de Diapositivas
# ---------------------
class SlideControllerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.current_screen_index = 0
        self.screens = QtWidgets.QApplication.screens()  # Obtener la lista inicial de pantallas
        self.tracklist_path = os.path.expandvars(r'%LocalAppData%\VirtualDJ\History\tracklist.txt')
        self.live_update = False
        self.current_slide = 1  # Inicializar con la primera diapositiva
        self.initUI()

        # Configura el observador para monitorear cambios en el archivo de tracklist
        self.event_handler = TracklistEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, os.path.dirname(self.tracklist_path), recursive=False)
        self.observer.start()

    # Configuración de la interfaz de usuario
    def initUI(self):

        # Diccionario de configuraciones de posición y tamaño
        layout_settings = {
            "window": {"x": 100, "y": 100, "width": 600, "height": 280},
            "open_presentation_button": {"x": 10, "y": 10, "width": 180, "height": 40},
            "button2": {"x": 210, "y": 10, "width": 180, "height": 40},
            "button3": {"x": 410, "y": 10, "width": 180, "height": 40},
            "presentation_label": {"x": 10, "y": 60, "width": 580, "height": 30},
            "song_label": {"x": 10, "y": 90, "width": 580, "height": 30},
            "slide_label": {"x": 10, "y": 120, "width": 580, "height": 100},
            "prev_button": {"x": 10, "y": 230, "width": 180, "height": 40},
            "live_button": {"x": 210, "y": 230, "width": 180, "height": 40},
            "next_button": {"x": 410, "y": 230, "width": 180, "height": 40}
        }

        # Configuración de ventana
        self.setWindowTitle("Slide Controller")
        self.setGeometry(
            layout_settings["window"]["x"],
            layout_settings["window"]["y"],
            layout_settings["window"]["width"],
            layout_settings["window"]["height"]
        )

        # Botón para abrir presentación
        self.open_presentation_button = QtWidgets.QPushButton("Open Slide Show", self)
        self.open_presentation_button.setGeometry(
            layout_settings["open_presentation_button"]["x"],
            layout_settings["open_presentation_button"]["y"],
            layout_settings["open_presentation_button"]["width"],
            layout_settings["open_presentation_button"]["height"]
        )
        self.open_presentation_button.setStyleSheet("background-color: lightgray; color: black; font-weight: bold;")
        self.open_presentation_button.clicked.connect(self.open_presentation)

        # Estilo de botones deshabilitados
        disabled_style = """
            QPushButton {
                background-color: #aaaaaa; 
                color: #555555; 
                font-weight: bold;
            }
        """
        enabled_style = """
            QPushButton {
                background-color: #007acc; 
                color: white; 
                font-weight: bold;
            }
        """

        # Configuración de los botones
        self.button2 = QtWidgets.QPushButton("Select Screen", self)
        self.button2.setGeometry(layout_settings["button2"]["x"], layout_settings["button2"]["y"],
                                 layout_settings["button2"]["width"], layout_settings["button2"]["height"])
        self.button2.setDisabled(True)
        self.button2.setStyleSheet(disabled_style)
        self.button2.clicked.connect(self.select_screen)

        self.button3 = QtWidgets.QPushButton("GO SLIDE SHOW", self)
        self.button3.setGeometry(layout_settings["button3"]["x"], layout_settings["button3"]["y"],
                                 layout_settings["button3"]["width"], layout_settings["button3"]["height"])
        self.button3.setDisabled(True)
        self.button3.setStyleSheet(disabled_style)
        self.button3.clicked.connect(self.go_slide_show)

        # Botones de navegación de diapositivas
        self.prev_button = QtWidgets.QPushButton("Previous Slide", self)
        self.prev_button.setGeometry(layout_settings["prev_button"]["x"], layout_settings["prev_button"]["y"],
                                     layout_settings["prev_button"]["width"], layout_settings["prev_button"]["height"])
        self.prev_button.setDisabled(True)
        self.prev_button.setStyleSheet(disabled_style)
        self.prev_button.clicked.connect(self.prev_slide)

        self.live_button = QtWidgets.QPushButton("Start Live Update", self)
        self.live_button.setGeometry(layout_settings["live_button"]["x"], layout_settings["live_button"]["y"],
                                     layout_settings["live_button"]["width"], layout_settings["live_button"]["height"])
        self.live_button.setDisabled(True)
        self.live_button.setStyleSheet(disabled_style)
        self.live_button.clicked.connect(self.toggle_live_update)

        self.next_button = QtWidgets.QPushButton("Next Slide", self)
        self.next_button.setGeometry(layout_settings["next_button"]["x"], layout_settings["next_button"]["y"],
                                     layout_settings["next_button"]["width"], layout_settings["next_button"]["height"])
        self.next_button.setDisabled(True)
        self.next_button.setStyleSheet(disabled_style)
        self.next_button.clicked.connect(self.next_slide)

        # Configuración de etiquetas deshabilitadas al inicio
        label_style_disabled = """
            QLabel {
                color: #555555;
                background-color: #333333;
                font-size: 14px;
                padding: 5px;
                border: 1px solid #aaaaaa;
            }
        """
        label_style_enabled = """
            QLabel {
                color: white;
                background-color: black;
                font-size: 14px;
                padding: 5px;
                border: 1px solid #FFFFFF;
            }
        """
        # Etiqueta para mostrar la presentación
        self.presentation_label = QtWidgets.QLabel("Presentation: No Presentation Loaded", self)
        self.presentation_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.presentation_label.setGeometry(layout_settings["presentation_label"]["x"],
                                            layout_settings["presentation_label"]["y"],
                                            layout_settings["presentation_label"]["width"],
                                            layout_settings["presentation_label"]["height"])
        self.presentation_label.setStyleSheet(label_style_disabled)

        # Etiqueta para mostrar la canción
        self.song_label = QtWidgets.QLabel("Current Song: No Song Playing", self)
        self.song_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.song_label.setGeometry(layout_settings["song_label"]["x"], layout_settings["song_label"]["y"],
                                    layout_settings["song_label"]["width"], layout_settings["song_label"]["height"])
        self.song_label.setStyleSheet(label_style_disabled)

        # Etiqueta para mostrar el estado de la diapositiva
        self.slide_label = QtWidgets.QLabel("No slides Loaded", self)
        self.slide_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.slide_label.setGeometry(layout_settings["slide_label"]["x"], layout_settings["slide_label"]["y"],
                                     layout_settings["slide_label"]["width"], layout_settings["slide_label"]["height"])
        self.slide_label.setStyleSheet(label_style_disabled)

        # Configuración del botón de selección de pantalla con la pantalla inicial
        if self.screens:
            self.button2.setText(f"Selected: Screen {self.current_screen_index + 1}")
        else:
            self.button2.setText("No Screens Available")
    # Acciones de ejemplo para los nuevos botones superiores
    def select_screen(self):
        # Verifica si hay una presentación cargada y pantallas disponibles
        if hasattr(self, 'presentation') and self.presentation and self.screens:
            # Bloquea el cambio de pantalla si el slideshow está activo
            if self.powerpoint.SlideShowWindows.Count > 0:
                QtWidgets.QMessageBox.warning(self, "Advertencia",
                                              "No se puede cambiar de pantalla mientras el slideshow está activo.")
            else:
                self.current_screen_index = (self.current_screen_index + 1) % len(self.screens)
                self.change_screen(self.current_screen_index)
                self.button2.setText(f"Selected: Screen {self.current_screen_index + 1}")
                print(f"Presentación cambiada a Screen {self.current_screen_index + 1}")
        else:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "Abre una presentación primero.")

    def change_screen(self, index):
        if self.presentation:
            # Usa la geometría de PyQt para obtener el tamaño y posición de la pantalla seleccionada
            screen_rect = self.screens[index].geometry()
            screen_width = screen_rect.width()
            screen_height = screen_rect.height()
            screen_top = screen_rect.top()
            screen_left = screen_rect.left()

            # Asegúrate de que PowerPoint esté en modo de presentación
            if self.powerpoint.SlideShowWindows.Count > 0:
                slideshow = self.powerpoint.SlideShowWindows(1)

                # Ajusta la posición y tamaño en la pantalla seleccionada
                slideshow.Top = screen_top
                slideshow.Left = screen_left
                slideshow.Height = screen_height
                slideshow.Width = screen_width
                print(f"Presentación proyectada correctamente en Screen {index + 1}")

                # Trae la ventana de PowerPoint al frente
                hwnd = win32gui.FindWindow(None, self.powerpoint.Caption)
                if hwnd:
                    win32gui.ShowWindow(hwnd, 9)  # Restaura y maximiza la ventana si estaba minimizada
                    win32gui.SetForegroundWindow(hwnd)
                    print("PowerPoint traído al frente después de cambiar de pantalla.")
            else:
                print("La presentación no está en modo Slideshow.")

    def go_slide_show(self):
        if hasattr(self, 'presentation') and self.presentation:
            try:
                if self.powerpoint.SlideShowWindows.Count > 0:
                    # Si ya está en modo de presentación, vuelve al modo de edición
                    self.presentation.SlideShowWindow.View.Exit()
                    self.button3.setText("GO SLIDE SHOW")
                    print("Cambiado a modo de edición.")
                else:
                    # Obtiene las coordenadas de la pantalla seleccionada
                    screen_rect = self.screens[self.current_screen_index].geometry()

                    # Configura el slideshow y lo inicia
                    self.presentation.SlideShowSettings.StartingSlide = 1
                    self.presentation.SlideShowSettings.EndingSlide = self.presentation.Slides.Count
                    self.presentation.SlideShowSettings.ShowWithNarration = True
                    self.presentation.SlideShowSettings.AdvanceMode = 1
                    self.presentation.SlideShowSettings.LoopUntilStopped = False
                    self.presentation.SlideShowSettings.Run()

                    # Espera un momento y ajusta la posición en la pantalla seleccionada
                    time.sleep(1)  # Asegura que el slideshow se inicie
                    slideshow = self.powerpoint.SlideShowWindows(1)
                    correction_factor = 0.75
                    slideshow.Top = screen_rect.top() * correction_factor
                    slideshow.Left = screen_rect.left() * correction_factor
                    slideshow.Height = screen_rect.height() * correction_factor
                    slideshow.Width = screen_rect.width() * correction_factor

                    # Trae PowerPoint al frente en el modo de presentación
                    hwnd = win32gui.FindWindow(None, self.powerpoint.Caption)
                    if hwnd:
                        win32gui.ShowWindow(hwnd, 9)  # Restaura y maximiza la ventana si estaba minimizada
                        win32gui.SetForegroundWindow(hwnd)
                        print("PowerPoint traído al frente en modo Slideshow.")

                    self.button3.setText("GO EDIT MODE")
                    print("Presentación iniciada en modo Slideshow en la pantalla seleccionada.")
            except Exception as e:
                print(f"Error al alternar entre modos de presentación: {e}")

    def enable_controls(self):
        enabled_style = """
            QPushButton {
                background-color: #007acc; 
                color: white; 
                font-weight: bold;
            }
        """
        label_style_enabled = """
            QLabel {
                color: white;
                background-color: black;
                font-size: 14px;
                padding: 5px;
                border: 1px solid #FFFFFF;
            }
        """
        # Activa cada botón y etiqueta y cambia su estilo
        for button in [self.button2, self.button3, self.prev_button, self.live_button, self.next_button]:
            button.setDisabled(False)
            button.setStyleSheet(enabled_style)

        self.live_button.setStyleSheet("background-color: lightgray; font-weight: bold; color: black;")

        for label in [self.presentation_label, self.song_label, self.slide_label]:
            label.setStyleSheet(label_style_enabled)

    # Abre la presentación seleccionada
    def open_presentation(self):
        try:
            default_dir = r'D:\Dropbox\TDJ\Presentacion'
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Presentation", default_dir,
                                                       "PowerPoint Files (*.pptx *.ppt)")
            if file_path and os.path.exists(file_path):
                formatted_path = file_path.replace('/', '\\')
                filename_only = os.path.basename(formatted_path)
                self.powerpoint = win32com.client.Dispatch("PowerPoint.Application")
                self.powerpoint.Visible = True
                time.sleep(1)  # Espera un momento para que PowerPoint inicie
                self.presentation = self.powerpoint.Presentations.Open(formatted_path, ReadOnly=True)

                if hasattr(self.presentation, 'Slides') and self.presentation.Slides.Count > 0:
                    print(f"Presentación cargada correctamente con {self.presentation.Slides.Count} diapositivas.")
                    self.presentation_label.setText(f"Presentation: {filename_only}")
                    self.enable_controls()  # Habilita los botones y etiquetas
                    self.button2.setText(f"Selected: Screen {self.current_screen_index + 1}")
                    self.live_update = True  # Activa Live Update por defecto
                    self.live_button.setText("Stop Live Update")
                    self.live_button.setDisabled(False)  # Activa el botón
                    self.live_button.setStyleSheet("background-color: red; font-weight: bold; color: white;")
                    print("Live Update activado automáticamente.")

                    # Trae la ventana de PowerPoint al frente al cargar la presentación
                    hwnd = win32gui.FindWindow(None, self.powerpoint.Caption)
                    if hwnd:
                        win32gui.ShowWindow(hwnd, 9)  # Restaura y maximiza la ventana si estaba minimizada
                        win32gui.SetForegroundWindow(hwnd)
                        print("PowerPoint traído al frente después de cargar la presentación.")
                else:
                    print("Error: La presentación no contiene diapositivas o no se cargó correctamente.")
                    self.presentation = None
            else:
                print("No se seleccionó ninguna presentación o el archivo no existe.")
        except Exception as e:
            print(f"Error al abrir la presentación: {e}")

    # Alterna el estado de actualización en vivo
    def toggle_live_update(self):
        self.live_update = not self.live_update
        if self.live_update:
            self.live_button.setText("Stop Live Update")
            self.live_button.setStyleSheet("background-color: red; font-weight: bold; color: white;")
            print("Live Update activado.")
        else:
            self.live_button.setText("Start Live Update")
            self.live_button.setStyleSheet("background-color: lightgray; font-weight: bold; color: black;")
            print("Live Update desactivado.")

    # Procesa el cambio en el archivo tracklist
    def process_tracklist_change(self):
        print("Procesando cambio en tracklist...")
        if not self.presentation:
            print("La presentación no está cargada.")
            return

        # Verifica si el Live Update está activado
        if not self.live_update:
            print("Live Update está desactivado; no se actualizarán las diapositivas automáticamente.")
            return

        try:
            last_line = self.read_last_line_of_tracklist(self.tracklist_path)
            if last_line:
                print(f"Última línea leída: {last_line}")
                slide_number = self.find_slide_by_notes(self.presentation, last_line)
                if slide_number:
                    self.song_label.setText(f"Current Song: {last_line}")
                    # Usa goto_slide para manejar ambos modos (edición y Slideshow)
                    self.goto_slide(slide_number)
                else:
                    print("No se encontró una diapositiva para la canción.")
        except Exception as e:
            print(f"Error en process_tracklist_change: {e}")

    # Lee la última línea de tracklist.txt y devuelve el título de la canción
    def read_last_line_of_tracklist(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    if " : " in last_line:
                        return last_line.split(" : ", 1)[1]
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        return None

    # Busca una diapositiva por el contenido en sus notas
    def find_slide_by_notes(self, presentation, search_text):
        try:
            for slide in presentation.Slides:
                notes = slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
                if unidecode(search_text.lower()) in unidecode(notes.lower()):
                    return slide.SlideNumber

        except Exception as e:
            print(f"Error al acceder a las diapositivas: {e}")
        return None

    # Cambia a una diapositiva específica
    def goto_slide(self, slide_number):
        try:
            if self.powerpoint.SlideShowWindows.Count > 0:
                # En modo Slideshow, usa la ventana de presentación
                slideshow = self.powerpoint.SlideShowWindows(1)
                slideshow.View.GotoSlide(slide_number)
                print(f"Saltando a la diapositiva {slide_number} en modo Slideshow.")
                notes = self.presentation.Slides(slide_number).NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
                # Replace all line break formats with <br> for QLabel compatibility
                notes_html = notes.replace('\r\n', '<br>').replace('\r', '<br>').replace('\n', '<br>')
                self.slide_label.setText(f"Presentation: <br>{notes_html}")
            else:
                # En modo de edición, selecciona la diapositiva
                self.presentation.Slides(slide_number).Select()
                self.current_slide = slide_number  # Actualiza el número de la diapositiva actual
                print(f"Saltando a la diapositiva {slide_number} en modo edición.")
                notes = self.presentation.Slides(slide_number).NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
                # Replace all line break formats with <br> for QLabel compatibility
                notes_html = notes.replace('\r\n', '<br>').replace('\r', '<br>').replace('\n', '<br>')
                self.slide_label.setText(f"Presentation: <br>{notes_html}")
        except Exception as e:
            print(f"Error al intentar cambiar a la diapositiva {slide_number}: {e}")

    # Avanza a la siguiente diapositiva
    def next_slide(self):
        try:
            if self.powerpoint.SlideShowWindows.Count > 0:
                slideshow = self.powerpoint.SlideShowWindows(1)
                slideshow.View.Next()
                print("Avanzando a la siguiente diapositiva en modo Slideshow.")
            else:
                # Avanza a la siguiente diapositiva en modo de edición
                next_slide_number = self.current_slide + 1 if self.current_slide < self.presentation.Slides.Count else 1
                self.goto_slide(next_slide_number)
                print(f"Avanzando a la siguiente diapositiva en modo edición, ahora en diapositiva {self.current_slide}.")
        except Exception as e:
            print(f"Error al intentar avanzar a la siguiente diapositiva: {e}")

    # Retrocede a la diapositiva anterior
    def prev_slide(self):
        try:
            if self.powerpoint.SlideShowWindows.Count > 0:
                slideshow = self.powerpoint.SlideShowWindows(1)
                slideshow.View.Previous()
                print("Retrocediendo a la diapositiva anterior en modo Slideshow.")
            else:
                # Retrocede a la diapositiva anterior en modo de edición
                prev_slide_number = self.current_slide - 1 if self.current_slide > 1 else self.presentation.Slides.Count
                self.goto_slide(prev_slide_number)
                print(f"Retrocediendo a la diapositiva anterior en modo edición, ahora en diapositiva {self.current_slide}.")
        except Exception as e:
            print(f"Error al intentar retroceder a la diapositiva anterior: {e}")


# ---------------------
# Ejecución Principal de la Aplicación
# ---------------------
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = SlideControllerApp()
    window.show()
    sys.exit(app.exec_())