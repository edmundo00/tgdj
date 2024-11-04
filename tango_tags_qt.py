from PyQt5.QtWidgets import QApplication, QMainWindow
import pygame
from src.config.config import DB_CSV_PATH
from src.config.database import Database
from src.ui.tango_tags_qt_ventana import tango_tags_qt_ventana
import sys


if __name__ == "__main__":

    # Load data from CSV Database
    data_store = Database()
    data_store.load_data(DB_CSV_PATH)

    # Initialize pygame mixer
    pygame.mixer.init()

    # Create the PyQt application
    app = QApplication(sys.argv)

    # Create the main window
    tango_tags = tango_tags_qt_ventana()

    # Show the main window
    tango_tags.show()

    # Run the application event loop
    sys.exit(app.exec_())