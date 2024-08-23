import tkinter as tk
from ventana import Ventana
import pygame
from config import dbpath
from database import Database

if __name__ == "__main__":
    # Create an instance of the Database
    data_store = Database()

    # Load the data at the very start
    data_store.load_data(dbpath)

    pygame.mixer.init()
    root = tk.Tk()
    app = Ventana(root)
    root.mainloop()


