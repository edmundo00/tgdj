import pandas as pd
import os
from src.utils.utils import *
from dateutil import parser
import re
import threading

_cerrojo_indice = threading.Lock()


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

        self.db = pd.read_csv(dbpath, encoding="utf-8", sep=";", na_filter=False, dtype=str)
        if os.path.basename(dbpath) != "tangodb.csv":
            # Base de datos sin limpiar: normalizar en memoria (python -m src.utils.mejorar_bd lo deja hecho)
            from src.utils.mejorar_bd import mejorar
            self.db = mejorar(self.db)[0]
        # Correcciones hechas a mano desde el buscador (data/correcciones.csv)
        from src.utils import correcciones
        self.db = correcciones.aplicar(self.db)
        self.dic_art = {artista: group for artista, group in self.db.groupby('artista_min')}
        print("Data loaded successfully")

    def get_indice_busqueda(self):
        """Índice para el buscador (se construye la primera vez; tarda unos segundos)."""
        from src.utils.buscador import IndiceBusqueda
        with _cerrojo_indice:   # puede llamarse a la vez desde el hilo que lo prepara al arrancar
            if getattr(self, "_indice", None) is None or self._indice_de is not self.db:
                self._indice = IndiceBusqueda(self.db)
                self._indice_de = self.db
        return self._indice

    def get_db(self):
        return self.db

    def get_dic_art(self):
        return self.dic_art


    def merge(self, dbpath1, origen1, dbpath2, origen2, output_path=None):
        print(f"Attempting to merge data from: '{dbpath1}' and '{dbpath2}'")

        if not os.path.exists(dbpath1):
            print(f"Error: The database file at path '{dbpath1}' does not exist.")
            return

        if not os.path.exists(dbpath2):
            print(f"Error: The database file at path '{dbpath2}' does not exist.")
            return

        # Load the two databases
        db1 = pd.read_csv(dbpath1, encoding="utf-8", sep=";", na_filter=False)
        db2 = pd.read_csv(dbpath2, encoding="utf-8", sep=";", na_filter=False)

        # Add 'origen' column to each database
        db1['origen'] = origen1
        db2['origen'] = origen2

        # Merge the databases
        merged_db = pd.concat([db1, db2]).drop_duplicates().reset_index(drop=True)

        # Reorder columns
        desired_columns = [
            "titulo", "artista", "cantor", "fecha",
            "estilo", "compositor_autor", "audio30", "audio10", "origen"
        ]
        merged_db = merged_db[desired_columns]

        # Additional columns for processing
        merged_db['fecha_ano'] = merged_db['fecha'].apply(extract_year)
        merged_db['titulo_min'] = merged_db['titulo'].apply(lambda x: convert_numbers_to_words(x) if pd.notna(x) else x)
        merged_db['artista_min'] = merged_db['artista'].apply(lambda x: convert_numbers_to_words(x) if pd.notna(x) else x)
        merged_db['cantor_min'] = merged_db['cantor'].apply(lambda x: convert_numbers_to_words(x) if pd.notna(x) else x)

        # Keep only one row per unique combination of titulo, artista, cantor, fecha
        merged_db = (
            merged_db.sort_values(by="origen", key=lambda x: x != 'tangoinfo')  # Prefer rows where origen != tangoinfo
            .drop_duplicates(subset=["titulo", "artista", "cantor", "fecha"], keep="first")  # Keep the first after sorting
        )

        # Save the merged database back to the main database
        self.db = merged_db
        self.dic_art = {artista: group for artista, group in self.db.groupby('artista')}

        # Optionally, save to an output file
        if output_path:
            merged_db.to_csv(output_path, index=False, sep=";", encoding="utf-8")
            print(f"Merged database saved to: {output_path}")
        else:
            print("Merged database loaded into memory only.")


