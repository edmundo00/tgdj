import pandas as pd
import os
from src.utils.utils import *
from dateutil import parser
import re


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls.db = None
            cls.dic_art = {}
        return cls._instance


    def load_data(self, dbpath):

        #self.merge_data()

        print(f"Attempting to load data from: {dbpath}")
        if not os.path.exists(dbpath):
            print(f"Error: The database file at path '{dbpath}' does not exist.")
            return
        
        self.db = pd.read_csv(dbpath, encoding="utf-8", sep=";", na_filter=False)
        if self.db is not None:
            self.dic_art = {artista: group for artista, group in self.db.groupby('artista_min')}
            print("Data loaded successfully")

    def get_db(self):
        return self.db

    def get_dic_art(self):
        return self.dic_art


    def convertdates(self):
        # Usage example:
        file_path = "D:\\Dropbox\\TDJ\\PYTHON\\tgdj\\data\\tangoinfo_genregood_dategood.csv"  # Cambia esto por la ruta de tu archivo
        column_name = "fecha"  # Nombre de la columna a procesar
        output_file = "D:\\Dropbox\\TDJ\\PYTHON\\tgdj\\data\\tangoinfo_updated.csv"  # Ruta para guardar el archivo procesado

        self.convert_dates_replace(file_path, column_name, output_file)

    def merge_data(self):
        dbpath1 = "D:\\Dropbox\\TDJ\\PYTHON\\tgdj\\data\\db.csv"
        origin1 = "recodo"
        dbpath2 = "D:\\Dropbox\\TDJ\\PYTHON\\tgdj\\data\\tangoinfo_genregood_dategood.csv"
        origin2 = "tangoinfo"

        # Optional: Specify where to save the merged database
        output_path = "D:\\Dropbox\\TDJ\\PYTHON\\tgdj\\data\\mergeddb.csv"

        # Create a single instance of the Database class
        db_instance = Database()

        # Run the merge method
        db_instance.merge(dbpath1, origin1, dbpath2, origin2, output_path=output_path)

        # Print the merged data to verify it worked
        merged_data = db_instance.get_db()
        print(merged_data.head())  # Show the first few rows

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

    def filter_duplicates_and_prioritize(self, output_csv_path):
        if self.db is None:
            print("Error: No data loaded in the database.")
            return

        # Check that required columns exist
        required_columns = ['titulo', 'fecha', 'origen']
        for column in required_columns:
            if column not in self.db.columns:
                print(f"Error: The column '{column}' does not exist in the database.")
                return

        # Filter rows with valid 'fecha' format (YYYY-MM-DD)
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        valid_dates = self.db['fecha'].str.match(date_pattern, na=False)
        db_with_valid_dates = self.db[valid_dates]

        # Identify duplicates based on 'titulo' and 'fecha'
        duplicates = db_with_valid_dates[db_with_valid_dates.duplicated(subset=['titulo', 'fecha'], keep=False)]

        if duplicates.empty:
            print("No duplicates found.")
            # Save the entire database if there are no duplicates
            self.db.to_csv(output_csv_path, index=False, sep=";", encoding="utf-8")
            print(f"Entire database exported to: {output_csv_path}")
            return

        # Create a list for filtered rows
        filtered_rows = []

        # Group duplicates by 'titulo' and 'fecha'
        grouped_duplicates = duplicates.groupby(['titulo', 'fecha'])

        for (titulo, fecha), group in grouped_duplicates:
            # Filter records with 'recodo' as priority
            recodo_rows = group[group['origen'] == 'recodo']
            if not recodo_rows.empty:
                # If there are rows with 'recodo', keep only those
                filtered_rows.append(recodo_rows)
            else:
                # If no rows with 'recodo', keep all with 'tangoinfo'
                tangoinfo_rows = group[group['origen'] == 'tangoinfo']
                if not tangoinfo_rows.empty:
                    filtered_rows.append(tangoinfo_rows)

        # Concatenate all filtered rows
        filtered_duplicates = pd.concat(filtered_rows)

        # Combine filtered duplicates (recodo prioritized) with the rest of the database
        corrected_db = pd.concat([filtered_duplicates, self.db[~self.db.index.isin(filtered_duplicates.index)]])
        corrected_db = corrected_db.drop_duplicates()  # Remove potential duplicates after combination

        # Save the corrected database to a CSV file
        corrected_db.to_csv(output_csv_path, index=False, sep=";", encoding="utf-8")
        print(f"Corrected database exported to: {output_csv_path}")

    def convert_dates_replace(self, file_path, column_name, output_file):
        try:
            # Load the data
            data = pd.read_csv(file_path, encoding="utf-8", sep=";", na_filter=False)

            # Check if the column exists
            if column_name not in data.columns:
                print(f"Error: Column '{column_name}' not found in the file.")
                return

            # Process each date in the column
            for index, value in data[column_name].items():
                try:
                    # Force DD/MM/YYYY interpretation
                    parsed_date = parser.parse(value, dayfirst=True)
                    # Replace the value with the formatted date
                    if len(value) >= 10:  # Only replace if it's a full date
                        data.at[index, column_name] = parsed_date.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    # Leave the original value if parsing fails
                    pass

            # Save the updated data to a new CSV file
            data.to_csv(output_file, index=False, encoding="utf-8", sep=";")
            print(f"Updated file saved to: {output_file}")

        except Exception as e:
            print(f"An error occurred: {e}")