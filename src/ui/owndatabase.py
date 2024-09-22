from tkinter import filedialog, messagebox
from tinytag import TinyTag
from src.config.config import *
from src.utils.utils import *
import os
import pandas as pd

class owndatabase:
    def __init__(self, update_status=None):
        """Initialize the class and load or create the database."""
        self.update_status = update_status
        self.db_path = os.path.join(DATA_FOLDER, 'owndatabase.csv')
        self.db_report_path = os.path.join(DATA_FOLDER, 'owndatabase_report.csv')

        # Load or create the main database
        if os.path.exists(self.db_path):
            self.owndf = pd.read_csv(self.db_path).fillna("")
        else:
            columns = ['title', 'artist', 'year', 'genre', 'composer', 'file_path']
            self.owndf = pd.DataFrame(columns=columns)
            self.owndf.to_csv(self.db_path, index=False)


        # Load or create the report database
        if os.path.exists(self.db_report_path):
            self.owndf_rep = pd.read_csv(self.db_report_path).fillna("")
        else:
            self.owndf_rep = pd.DataFrame(columns=columns)
            self.owndf_rep.to_csv(self.db_report_path, index=False)

    # Columnas del DataFrame `self.owndf_rep`:
    #
    # 1. "Artista encontrado": Esta columna almacena el nombre del artista que ha sido encontrado durante el proceso de comparación.
    #    Ejemplo de acceso: self.owndf_rep["Artista encontrado"]
    #
    # 2. "Titulo encontrado": Esta columna almacena el título de la canción que ha sido encontrada durante el proceso de comparación.
    #    Ejemplo de acceso: self.owndf_rep["Titulo encontrado"]
    #
    # 3. "Coincidencia perfecta": Columna booleana que indica si hubo una coincidencia exacta entre la base de datos y la comparación realizada.
    #    Ejemplo de acceso: self.owndf_rep["Coincidencia perfecta"]
    #
    # 4. "Hay coincidencia preferida": Esta columna indica si se encontró una coincidencia marcada como preferida, es decir, aquella que tiene mayor relevancia.
    #    Ejemplo de acceso: self.owndf_rep["Hay coincidencia preferida"]
    #
    # 5. "No hay coincidencia preferida": Columna booleana que indica si no se encontró ninguna coincidencia marcada como preferida.
    #    Ejemplo de acceso: self.owndf_rep["No hay coincidencia preferida"]
    #
    # Ejemplo de uso: Puedes acceder a cualquiera de estas columnas directamente utilizando el formato self.owndf_rep["nombre de la columna"].

    # Filtrar donde 'Coincidencia perfecta' es True (no se necesita comparación explícita)
    # filtered_df_true = self.owndf[self.owndb.owndf_rep['Coincidencia perfecta']]
    # Filtrar donde 'Coincidencia perfecta' es False utilizando el operador ~ (negación)
    # filtered_df_false = self.owndf[~self.owndb.owndf_rep['Coincidencia perfecta']]

    def create_database(self, folder_selected=None, include_subfolders=False):
        """Create or update the database by scanning files in selected folders."""
        # If no folder is passed, use a dialog to select one (for GUI use)
        if not folder_selected:
            folder_selected = []
            while True:
                folder = filedialog.askdirectory(title="Select Folder to Scan (Cancel to stop)")
                if folder:
                    folder_selected.append(folder)
                    another_folder = messagebox.askyesno("Another Folder?", "Would you like to select another folder?")
                    if not another_folder:
                        break
                else:
                    break

        # If folders are selected or provided, process the files
        if folder_selected:
            if not include_subfolders:
                include_subfolders = messagebox.askyesno("Include Subfolders?", "Would you like to include subfolders?")
            file_list = []
            for folder in folder_selected:
                file_list.extend(self.scan_files(folder, include_subfolders))

            # Process each file and collect the tags
            data = []
            total_files = len(file_list)
            for index, file in enumerate(file_list):
                try:
                    tags = self.leer_tags(file)
                    data.append({
                        'title': tags.title,
                        'artist': tags.artist,
                        'year': tags.year,
                        'genre': tags.genre,
                        'composer': tags.composer,
                        'file_path': file
                    })
                except Exception as e:
                    print(f"Error reading {file}: {e}")

                # Update the status bar (only if update_status is provided)
                if self.update_status:
                    self.update_status(index + 1, total_files, len(data))

            # Save the collected data into the CSV
            self.owndf = pd.DataFrame(data)
            self.owndf.to_csv(self.db_path, index=False)
            if not folder_selected:  # Show message only in GUI context
                messagebox.showinfo("Database Created", "Database created and saved successfully.")

    def scan_files(self, folder, include_subfolders):
        """Scan files in the folder and optionally in subfolders."""
        file_list = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):
                    file_list.append(os.path.join(root, file))
            if not include_subfolders:
                break
        return file_list

    def leer_tags(self, ruta_archivo):
        """Read the tags from the file."""
        return TinyTag.get(ruta_archivo)
