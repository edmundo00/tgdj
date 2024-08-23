import pandas as pd
import os

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls.db = None
            cls.dic_art = {}
        return cls._instance

    def load_data(self, dbpath):
        print(f"Attempting to load data from: {dbpath}")
        if not os.path.exists(dbpath):
            print(f"Error: The database file at path '{dbpath}' does not exist.")
            return
        else:
            self.db = pd.read_csv(dbpath, encoding="utf-8", sep=";")
            print("Data loaded successfully")
            if self.db is not None:
                lista_artistas = self.db['artista_min'].unique()
                for artista in lista_artistas:
                    filtered_df = self.db[self.db['artista_min'] == artista]
                    self.dic_art[artista] = filtered_df

    def get_db(self):
        return self.db

    def get_dic_art(self):
        return self.dic_art


