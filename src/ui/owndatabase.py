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



        # Load or create the main database
        if os.path.exists(self.db_path):
            self.owndf = pd.read_csv(self.db_path).fillna("")
            self.owndf.set_index('file_path', inplace=True, drop=False)
        # else:
        #     columns = ['title', 'artist', 'year', 'genre', 'composer', 'file_path', "Titulo encontrado","Numero de coincidencias", "Hay coincidencia preferida","No hay coincidencia preferida","Coincidencia perfecta"  ]
        #     self.owndf = pd.DataFrame(columns=columns)

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

            # Añadir las nuevas columnas con valores por defecto
            self.owndf['Artista encontrado'] = False
            self.owndf['Titulo encontrado'] = False
            self.owndf['Numero de coincidencias'] = 0
            self.owndf['Hay coincidencia preferida'] = False
            self.owndf['No hay coincidencia preferida'] = False
            self.owndf['Coincidencia perfecta'] = False


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

    def get_artist_counts(self, output_folder):
        """Filtrar los artistas no encontrados y contar repeticiones"""
        filtered_df = self.owndf[
            (~self.owndf_rep['Coincidencia perfecta']) & (self.owndf_rep['Artista encontrado'])
        ]
        artist_counts = filtered_df['artist'].value_counts()

        archivo_artistas_no_encontrados = os.path.join(output_folder, 'artistas_no_encontrados.csv')
        artist_counts.to_csv(archivo_artistas_no_encontrados, index=True)

        print(f"Artistas no encontrados guardados en {archivo_artistas_no_encontrados}")

    def process_file_dates(self, output_folder):
        """Buscar fechas en los nombres de archivo, formatearlas y guardarlas en un CSV"""
        date_pattern = r"\((\d{2})-(\d{2})-(\d{4})\)"
        filtered_df = self.owndf[self.owndf['file_path'].str.contains(date_pattern, na=False)]
        filtered_df['formatted_date'] = None

        for index, row in filtered_df.iterrows():
            match = re.search(date_pattern, row['file_path'])
            if match and len(match.groups()) == 3:
                day, month, year = match.groups()
                formatted_date = f"{year}-{month}-{day}"
                filtered_df.at[index, 'formatted_date'] = formatted_date

                # (Opcional) Llamar a update_tags si es necesario
                # update_tags(row['file_path'], year=formatted_date)

        archivos_con_fechas = os.path.join(output_folder, 'archivos_con_fechas.csv')
        filtered_df.to_csv(archivos_con_fechas, index=True)

        print(f"Fechas procesadas guardadas en {archivos_con_fechas}")

