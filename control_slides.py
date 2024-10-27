import os
import time
import win32com.client
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from unidecode import unidecode
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt5.QtCore import QTimer


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
            # Ejecuta la función en el hilo principal para evitar errores de concurrencia
            QTimer.singleShot(0, self.slide_controller.process_tracklist_change)


# ---------------------
# Clase Principal de la Aplicación de Control de Diapositivas
# ---------------------
class SlideControllerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
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
        self.setWindowTitle("Slide Controller")
        self.setGeometry(100, 100, 600, 260)

        # Botón para abrir presentación
        self.open_presentation_button = QtWidgets.QPushButton("Open Slide Show", self)
        self.open_presentation_button.setGeometry(10, 10, 580, 20)
        self.open_presentation_button.clicked.connect(self.open_presentation)

        # Etiqueta para mostrar la canción y el estado de la presentación
        self.presentation_label = QtWidgets.QLabel("Presentation: No Presentation Loaded", self)
        self.presentation_label.setAlignment(QtCore.Qt.AlignCenter)
        self.presentation_label.setGeometry(10, 40, 580, 30)
        self.presentation_label.setStyleSheet("font-size: 14px; color: white; background-color: black;")

        # Etiqueta para mostrar la canción y el estado de la presentación
        self.song_label = QtWidgets.QLabel("Current Song: No Song Playing", self)
        self.song_label.setAlignment(QtCore.Qt.AlignCenter)
        self.song_label.setGeometry(10, 70, 580, 30)
        self.song_label.setStyleSheet("font-size: 14px; color: white; background-color: black;")

        # Etiqueta para mostrar la canción y el estado de la presentación
        self.slide_label = QtWidgets.QLabel("No slides Loaded", self)
        self.slide_label.setAlignment(QtCore.Qt.AlignCenter)
        self.slide_label.setGeometry(10, 100, 580, 100)
        self.slide_label.setStyleSheet("font-size: 14px; color: white; background-color: black;")


        # Botones para el control de la presentación
        self.live_button = self.create_button("Start Live Update", 210, 210, self.toggle_live_update)
        self.next_button = self.create_button("Next Slide", 410, 210, self.next_slide)
        self.prev_button = self.create_button("Previous Slide", 10, 210, self.prev_slide)

    # Crea botones personalizados con estilo
    def create_button(self, text, x, y, handler):
        button = QtWidgets.QPushButton(text, self)
        button.setGeometry(x, y, 180, 40)
        button.clicked.connect(handler)
        button.setStyleSheet("background-color: none; font-weight: bold;")
        return button

    # Abre la presentación seleccionada
    def open_presentation(self):
        try:
            default_dir = r'D:\Dropbox\TDJ\Presentacion'
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Presentation", default_dir, "PowerPoint Files (*.pptx *.ppt)")
            if file_path and os.path.exists(file_path):
                formatted_path = file_path.replace('/', '\\')
                filename_only = os.path.basename(formatted_path)
                self.powerpoint = win32com.client.Dispatch("PowerPoint.Application")
                self.powerpoint.Visible = True
                time.sleep(1)
                self.presentation = self.powerpoint.Presentations.Open(formatted_path, ReadOnly=True)

                # Verifica que la presentación tenga diapositivas
                if hasattr(self.presentation, 'Slides') and self.presentation.Slides.Count > 0:
                    self.update_label("Presentation Loaded")
                    print(f"Presentación cargada correctamente con {self.presentation.Slides.Count} diapositivas.")
                    self.presentation_label.setText(f"Presentation: {filename_only}")

                else:
                    print("Error: La presentación no contiene diapositivas o no se cargó correctamente.")
                    self.presentation = None
            else:
                print("No se seleccionó ninguna presentación o el archivo no existe.")
        except Exception as e:
            print(f"Error al abrir la presentación: {e}")

    def update_label(self, text):
        self.song_label.setText(f"Current Song: {text}")

    # Alterna el estado de actualización en vivo
    def toggle_live_update(self):
        self.live_update = not self.live_update
        if self.live_update:
            self.live_button.setText("Stop Live Update")
            self.live_button.setStyleSheet("background-color: red; font-weight: bold; color: white;")
            print("Live Update activado.")
        else:
            self.live_button.setText("Start Live Update")
            self.live_button.setStyleSheet("background-color: none; font-weight: bold; color: black;")
            print("Live Update desactivado.")

    # Procesa el cambio en el archivo tracklist
    def process_tracklist_change(self):
        print("Procesando cambio en tracklist...")
        if not self.presentation:
            print("La presentación no está cargada.")
            return

        try:
            last_line = self.read_last_line_of_tracklist(self.tracklist_path)
            if last_line:
                print(f"Última línea leída: {last_line}")
                slide_number = self.find_slide_by_notes(self.presentation, last_line)
                if slide_number:
                    self.update_label(last_line)
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
                self.presentation_label.setText(f"Presentation: <br>{notes_html}")
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