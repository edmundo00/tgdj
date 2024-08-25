import pandas as pd
from tinytag import TinyTag
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image as PilImage, ImageTk
from pptx.util import Cm, Pt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR
import os
from os.path import join
import re
from unidecode import unidecode
import num2words as nw
import pygame
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3
from datetime import datetime
from collections import Counter
from src.constants.enums import TagLabels
from src.config.config import DB_CSV_PATH
from src.config.database import Database
from src.ui.ventana import Ventana



if __name__ == "__main__":
    # Load data from CSV Database
    data_store = Database()
    data_store.load_data(DB_CSV_PATH)
  
    pygame.mixer.init()
    root = tk.Tk()
    app = Ventana(root)
    root.mainloop()
