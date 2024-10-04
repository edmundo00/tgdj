import tkinter as tk
import pygame
from src.config.config import DB_CSV_PATH
from src.config.database import Database
from src.ui.ventana import Ventana
from src.utils.calcular_ancho_fuentes import FontWidthCalculator


if __name__ == "__main__":
    # Load data from CSV Database
    data_store = Database()
    data_store.load_data(DB_CSV_PATH)

  
    pygame.mixer.init()
    root = tk.Tk()
    app = Ventana(root)
    root.mainloop()
