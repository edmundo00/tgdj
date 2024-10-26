import os
import time
import win32com.client
from PyQt5 import QtWidgets, QtGui, QtCore
from threading import Thread
from PyQt5.QtWidgets import QFileDialog

class SlideControllerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.tracklist_path = os.path.expandvars(r'%LocalAppData%\VirtualDJ\History\tracklist.txt')

        # Estado del Live Update
        self.live_update = False

        # Configura un QTimer para controlar las diapositivas automáticamente
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.auto_control_slides)
        self.timer.setInterval(5000)  # 5 segundos

    def initUI(self):
        # Configuración de la UI
        self.setWindowTitle("Slide Controller")
        self.setGeometry(100, 100, 400, 180)

        # Botón para abrir la presentación
        self.open_presentation_button = QtWidgets.QPushButton("Open Slide Show", self)
        self.open_presentation_button.setGeometry(10, 10, 380, 20)
        self.open_presentation_button.clicked.connect(self.open_presentation)

        # Label centrado en la parte superior para mostrar la canción y presentación actual
        self.song_label = QtWidgets.QLabel("Current Song: No Song Playing\nPresentation: No Presentation Loaded", self)
        self.song_label.setAlignment(QtCore.Qt.AlignCenter)
        self.song_label.setGeometry(10, 40, 380, 80)
        self.song_label.setStyleSheet("font-size: 14px; color: white; background-color: black;")

        # Botón central para activar/desactivar el modo LIVE, resaltado en rojo cuando está activo
        self.live_button = QtWidgets.QPushButton("Start Live Update", self)
        self.live_button.setGeometry(140, 130, 120, 40)
        self.live_button.setCheckable(True)
        self.live_button.clicked.connect(self.toggle_live_update)
        self.live_button.setStyleSheet("background-color: none; font-weight: bold;")

        # Botón para avanzar a la siguiente diapositiva
        self.next_button = QtWidgets.QPushButton("Next Slide", self)
        self.next_button.setGeometry(270, 130, 120, 40)
        self.next_button.clicked.connect(self.next_slide)

        # Botón para retroceder a la diapositiva anterior
        self.prev_button = QtWidgets.QPushButton("Previous Slide", self)
        self.prev_button.setGeometry(10, 130, 120, 40)
        self.prev_button.clicked.connect(self.prev_slide)

    def open_presentation(self):
        try:
            # Establece el directorio por defecto
            default_dir = r'D:\Dropbox\TDJ\Presentacion'

            # Muestra el cuadro de diálogo de selección de archivo
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Presentation", default_dir,
                                                       "PowerPoint Files (*.pptx *.ppt)")

            # Imprime la ruta del archivo para verificar
            print(f"Selected file path: {file_path}")

            # Verifica si se seleccionó un archivo y si existe
            if file_path and os.path.exists(file_path):
                # Formatea la ruta con barras invertidas dobles
                formatted_path = file_path.replace('/', '\\')
                print(f"Formatted file path: {formatted_path}")

                # Inicializa PowerPoint y espera que esté completamente cargado
                self.powerpoint = win32com.client.Dispatch("PowerPoint.Application")
                self.powerpoint.Visible = True

                # Espera un momento para que PowerPoint se inicie completamente
                time.sleep(1)

                # Abre la presentación en modo solo lectura
                self.presentation = self.powerpoint.Presentations.Open(formatted_path, ReadOnly=True)

                self.update_label("Presentation Loaded")
            else:
                print("No presentation selected or file does not exist.")
        except Exception as e:
            print(f"Error opening presentation: {e}")

    def toggle_live_update(self):
        # Alterna la actualización en vivo al hacer clic en el botón
        self.live_update = not self.live_update
        if self.live_update:
            self.live_button.setText("Stop Live Update")
            self.live_button.setStyleSheet("background-color: red; font-weight: bold; color: white;")
            self.timer.start()  # Inicia el temporizador para auto-control
        else:
            self.live_button.setText("Start Live Update")
            self.live_button.setStyleSheet("background-color: none; font-weight: bold; color: black;")
            self.timer.stop()  # Detiene el temporizador

    def update_label(self, text):
        self.song_label.setText(f"Current Song: {text}")

    def auto_control_slides(self):
        try:
            # Verifica si hay ventanas de presentación de diapositivas abiertas
            if self.powerpoint.SlideShowWindows.Count == 0:
                # Inicia la presentación de diapositivas si aún no ha comenzado
                self.presentation.SlideShowSettings.Run()
                print("Slideshow started automatically.")

            # Ahora verifica si la presentación está en modo de presentación de diapositivas
            if self.powerpoint.SlideShowWindows.Count > 0:
                slideshow = self.powerpoint.SlideShowWindows(1)
                last_line = self.read_last_line_of_tracklist(self.tracklist_path)
                if last_line:
                    slide_number = self.find_slide_by_notes(self.presentation, last_line)
                    if slide_number:
                        self.update_label(last_line)
                        self.goto_slide(slideshow, slide_number)
            else:
                print("Waiting for you to start the slideshow...")
        except Exception as e:
            print(f"Error in auto_control_slides: {e}")

    def next_slide(self):
        if self.powerpoint.SlideShowWindows.Count > 0:
            slideshow = self.powerpoint.SlideShowWindows(1)
            slideshow.View.Next()

    def prev_slide(self):
        if self.powerpoint.SlideShowWindows.Count > 0:
            slideshow = self.powerpoint.SlideShowWindows(1)
            slideshow.View.Previous()

    def read_last_line_of_tracklist(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                if lines:
                    # The last line should have the format "Time : Artist - Song"
                    last_line = lines[-1].strip()
                    # Split the line to extract "Artist - Song" (ignore time)
                    if " : " in last_line:
                        artist_song = last_line.split(" : ", 1)[1]
                        return artist_song  # Return the artist and song part only
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        return None

    # Function to search for a slide by the content stored in the notes
    def find_slide_by_notes(self, presentation, search_text):
        for slide in presentation.Slides:
            # Check the slide notes for the search_text
            notes = slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
            if search_text.lower() in notes.lower():
                return slide.SlideNumber
        return None

    # Function to control the PowerPoint slideshow
    def goto_slide(self, slideshow, slide_number):
        if slide_number:
            slideshow.View.GotoSlide(slide_number)
            print(f"Jumping to slide {slide_number}")
        else:
            print("Slide not found.")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = SlideControllerApp()
    window.show()
    sys.exit(app.exec_())