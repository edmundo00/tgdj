from src.config.config import DATA_FOLDER
from PIL import ImageFont, ImageDraw, Image
from matplotlib import font_manager
import os
import csv
import pandas as pd
import numpy as np

class FontWidthCalculator():
    def __init__(self):
        self.anchos_df = None

    def obtener_ruta_fuente(self, nombre_fuente):
        rutas_fuentes = font_manager.findSystemFonts(fontpaths=None, fontext='ttf')

        for ruta in rutas_fuentes:
            if nombre_fuente.lower() in font_manager.FontProperties(fname=ruta).get_name().lower():
                return ruta
        raise ValueError(f"No se encontró la fuente '{nombre_fuente}' en el sistema.")

    def medir_anchos(self, nombre_fuente, tamaños_base):
        anchos_base = {}
        factores = []

        try:
            ruta_fuente = self.obtener_ruta_fuente(nombre_fuente)

            for tamaño in tamaños_base:
                fuente = ImageFont.truetype(ruta_fuente, tamaño)

                # Caracteres comunes que podrían aparecer en textos
                caracteres = (
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "abcdefghijklmnopqrstuvwxyz"
                    "0123456789"
                    "!@#$%^&*()_+-=[]{}|;:',.<>/?`~\"\\ "
                )

                # Crear imagen dummy para dibujar los caracteres
                imagen = Image.new('RGB', (1, 1))
                dibujo = ImageDraw.Draw(imagen)

                # Medir y guardar el ancho de cada carácter para el tamaño actual
                anchos = {caracter: dibujo.textbbox((0, 0), caracter, font=fuente)[2] for caracter in caracteres}
                anchos_base[(nombre_fuente, tamaño)] = anchos

            # Calcular factores de escala entre tamaños consecutivos
            for i in range(len(tamaños_base) - 1):
                tamaño1, tamaño2 = tamaños_base[i], tamaños_base[i + 1]
                factor = tamaño2 / tamaño1
                factores.append(factor)

            # Calcular el factor de escala promedio
            factor_promedio = sum(factores) / len(factores)

            return anchos_base, factor_promedio

        except ValueError as e:
            print(e)
            return {}, 1.0

    def guardar_csv(self, anchos_dict, caracteres):
        csv_path = os.path.join(DATA_FOLDER, "anchos_fuentes.csv")

        with open(csv_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            header = ['Font+Size'] + list(caracteres)
            writer.writerow(header)

            for (fuente, tamaño), anchos in anchos_dict.items():
                row = [f"{fuente} {tamaño}"] + [anchos.get(c, '') for c in caracteres]
                writer.writerow(row)

        print(f"Archivo CSV guardado en {csv_path}")

    def cargar_anchos_en_memoria(self):
        if self.anchos_df is None:
            csv_path = os.path.join(DATA_FOLDER, "anchos_fuentes.csv")
            self.anchos_df = pd.read_csv(csv_path)

    def calcular_ancho_texto(self, texto, nombre_fuente, tamaño_fuente, DPI, unidad='pixeles'):
        """
        Calcula el ancho exacto de un texto basado en la fuente, tamaño de fuente y la unidad de medida deseada.
        Interpola o extrapola los valores si el tamaño de fuente solicitado no está disponible.

        Parámetros:
            texto (str): El texto cuyo ancho se va a calcular.
            nombre_fuente (str): El nombre de la fuente.
            tamaño_fuente (int): El tamaño de la fuente.
            unidad (str): La unidad de medida de la salida ('pixeles', 'emus', 'dpi').
            DPI (int): La resolución en puntos por pulgada (DPI) a usar para la conversión.

        Retorna:
            float: El ancho del texto en la unidad especificada.
        """
        self.cargar_anchos_en_memoria()

        # Filtrar las filas correspondientes a la fuente especificada
        fuente_df = self.anchos_df[self.anchos_df['Font+Size'].str.contains(nombre_fuente)]

        # Extraer los tamaños disponibles para la fuente
        available_sizes = fuente_df['Font+Size'].apply(lambda x: int(x.split()[-1])).values

        if tamaño_fuente in available_sizes:
            # Si el tamaño exacto está disponible, usarlo directamente
            font_size_key = f"{nombre_fuente} {tamaño_fuente}"
            fila = fuente_df[fuente_df['Font+Size'] == font_size_key]
            anchos_caracteres = fila.iloc[0].to_dict()
            anchos_caracteres.pop('Font+Size', None)
        else:
            # Ordenar los tamaños disponibles y encontrar los más cercanos
            available_sizes = np.sort(available_sizes)
            if tamaño_fuente < available_sizes[0]:
                # Extrapolar hacia abajo si el tamaño es menor que el mínimo disponible
                size_low = available_sizes[0]
                size_high = available_sizes[1]
            elif tamaño_fuente > available_sizes[-1]:
                # Extrapolar hacia arriba si el tamaño es mayor que el máximo disponible
                size_low = available_sizes[-2]
                size_high = available_sizes[-1]
            else:
                # Interpolar entre los tamaños disponibles más cercanos
                size_low = available_sizes[available_sizes < tamaño_fuente].max()
                size_high = available_sizes[available_sizes > tamaño_fuente].min()

            # Obtener los anchos correspondientes a los tamaños más cercanos
            fila_low = fuente_df[fuente_df['Font+Size'] == f"{nombre_fuente} {size_low}"]
            fila_high = fuente_df[fuente_df['Font+Size'] == f"{nombre_fuente} {size_high}"]
            anchos_low = fila_low.iloc[0].to_dict()
            anchos_high = fila_high.iloc[0].to_dict()
            anchos_low.pop('Font+Size', None)
            anchos_high.pop('Font+Size', None)

            # Interpolar o extrapolar los anchos de caracteres
            factor = (tamaño_fuente - size_low) / (size_high - size_low)
            anchos_caracteres = {
                char: anchos_low[char] + factor * (anchos_high[char] - anchos_low[char])
                for char in anchos_low
            }

        # Calcular el ancho del texto
        ancho_total = sum(float(anchos_caracteres.get(char, 0)) for char in texto)

        # Convertir el ancho según la unidad solicitada
        if unidad == 'emus':
            ancho_total *= 914400 / DPI  # Conversión de pixeles a EMUs (pulgadas)
        elif unidad == 'dpi':
            ancho_total *= 72 / DPI  # Conversión de pixeles a puntos (DPI)

        return ancho_total

    def crear_base_de_datos(self):
        """
        Crea una base de datos de anchos de caracteres para una lista de fuentes y tamaños,
        y guarda los resultados en un archivo CSV.
        """
        # Lista de fuentes comunes a medir
        fuentes_comunes = [
            "Cooper Black", "Bernard MT Condensed", "Arial", "Consolas",
            "Courier New", "Broadway"
        ]

        # Tamaños base para medir los anchos
        tamaños_base = [5, 10, 20, 40, 100, 200]  # Tamaños base

        # Caracteres comunes que podrían aparecer en textos
        caracteres = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789"
            "!@#$%^&*()_+-=[]{}|;:',.<>/?`~\"\\ "
        )

        # Crear la base de datos de anchos para cada fuente
        anchos_totales = {}
        for fuente in fuentes_comunes:
            anchos, _ = self.medir_anchos(fuente, tamaños_base)
            anchos_totales.update(anchos)

        # Guardar los anchos en un archivo CSV
        self.guardar_csv(anchos_totales, caracteres)



