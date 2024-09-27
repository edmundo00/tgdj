from tkinter import filedialog, messagebox
from tinytag import TinyTag
from src.config.config import *
from src.utils.utils import *
import os
import pandas as pd
import threading



class owndatabase:
    def __init__(self, update_status=None):
        """Initialize the class and load or create the database."""
        self.update_status = update_status
        self.db_name = None
        self.db_path = None
        self.owndf = pd.DataFrame()



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

    def create_database(self, db_name, folder_selected=None, include_subfolders=False):
        """Crear la base de datos con el nombre proporcionado y escanear archivos."""
        self.db_name = db_name

        # Crear el path usando el nombre de la base de datos proporcionado
        self.db_path = os.path.join(DATABASE_FOLDER, f'{self.db_name}.csv')

        # Escoger carpetas para escanear si no se han pasado
        if not folder_selected:
            folder_selected = []
            while True:
                folder = filedialog.askdirectory(title="Selecciona la carpeta para escanear (Cancelar para detener)")
                if folder:
                    folder_selected.append(folder)
                    another_folder = messagebox.askyesno("Otra Carpeta?", "¿Quieres seleccionar otra carpeta?")
                    if not another_folder:
                        break
                else:
                    break

        # Procesar los archivos de las carpetas seleccionadas
        if folder_selected:
            if not include_subfolders:
                include_subfolders = messagebox.askyesno("¿Incluir subcarpetas?", "¿Quieres incluir subcarpetas?")

            file_list = []
            for folder in folder_selected:
                file_list.extend(self.scan_files(folder, include_subfolders))

            # Procesar los archivos y recolectar las etiquetas
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
                    print(f"Error leyendo {file}: {e}")

                # Actualizar la barra de progreso si se provee `update_status`
                if self.update_status:
                    self.update_status(current=index + 1, total=total_files)
            print('todo cargado')
            # Crear el DataFrame con los datos recolectados y añadir columnas adicionales
            self.owndf = pd.DataFrame(data)
            self.owndf['Artista encontrado'] = False
            self.owndf['Titulo encontrado'] = False
            self.owndf['Numero de coincidencias'] = 0
            self.owndf['Hay coincidencia preferida'] = False
            self.owndf['No hay coincidencia preferida'] = False
            self.owndf['Coincidencia perfecta'] = False
            print('columnas extras echas')

            self.owndf.set_index('file_path', inplace=True, drop=False)

            print('indice hecho')

            self.guardar_base_de_datos()
            print('salvado a csv')
            messagebox.showinfo("Base de Datos Creada",
                                f"La base de datos '{self.db_name}' ha sido creada exitosamente.")






    def guardar_base_de_datos(self):
        # Guardar la base de datos en el archivo CSV con el nombre proporcionado
        self.owndf.to_csv(self.db_path, index=False)

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

