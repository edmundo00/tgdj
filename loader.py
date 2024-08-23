import os
import pandas as pd
import pygame
from config import dbpath

def load_data():
    dic_art={}
    print(f"Attempting to load data from: {dbpath}")
    if not os.path.exists(dbpath):  # Check if the dbpath exists
        print(f"Error: The database file at path '{dbpath}' does not exist.")
        return
    else:
        db = pd.read_csv(dbpath, encoding="utf-8", sep=";")
        print("Data loaded successfully")
        # Initialize dic_art based on db
        if db is not None:
            lista_artistas = db['artista_min'].unique()
            for artista in lista_artistas:
                filtered_df = db[db['artista_min'] == artista]
                dic_art[artista] = filtered_df
    return dic_art, db

def init_pygame():
    pygame.mixer.init()
