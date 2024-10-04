import tkinter as tk
from tkinter import ttk

class MiAplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ejemplo de Agrupación de Columnas con Frames")

        # Configurar la ventana principal para que se expanda
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Crear el frame principal y configurarlo para que se expanda
        self.frame_principal = ttk.Frame(self)
        self.frame_principal.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Definir la configuración de las columnas
        columnas_config = {
            "archivo_info": {
                "titulo": "", "columna": 0, "ancho": 15, "expandir": False, "fondo": "#f0f0f0", "borde": 1,
                "sticky": "ns", "rowconfigure": {"index": 1, "weight": 0, "minsize": 10},
                "columnconfigure": {"index": 0, "weight": 0, "minsize": 15}
            },
            "archivo_titulo": {
                "titulo": "Titulo", "columna": 1, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "archivo_orquesta": {
                "titulo": "Orquesta", "columna": 2, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "archivo_cantor": {
                "titulo": "Cantor", "columna": 3, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "archivo_fecha": {
                "titulo": "Fecha", "columna": 4, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "archivo_play": {
                "titulo": "", "columna": 5, "ancho": 15, "expandir": False, "fondo": "#f0f0f0", "borde": 1,
                "sticky": "ns", "rowconfigure": {"index": 1, "weight": 0, "minsize": 10},
                "columnconfigure": {"index": 0, "weight": 0, "minsize": 15}
            },
            "archivo_pausa": {
                "titulo": "", "columna": 6, "ancho": 15, "expandir": False, "fondo": "#f0f0f0", "borde": 1,
                "sticky": "ns", "rowconfigure": {"index": 1, "weight": 0, "minsize": 10},
                "columnconfigure": {"index": 0, "weight": 0, "minsize": 15}
            },
            "database_checkbox": {
                "titulo": "", "columna": 7, "ancho": 15, "expandir": False, "fondo": "#f0f0f0", "borde": 1,
                "sticky": "ns", "rowconfigure": {"index": 1, "weight": 0, "minsize": 10},
                "columnconfigure": {"index": 0, "weight": 0, "minsize": 15}
            },
            "database_titulo": {
                "titulo": "Titulo", "columna": 8, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "database_orquesta": {
                "titulo": "Orquesta", "columna": 9, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "database_cantor": {
                "titulo": "Cantor", "columna": 10, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "database_estilo": {
                "titulo": "Genero", "columna": 11, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "database_fecha": {
                "titulo": "Fecha", "columna": 12, "ancho": None, "expandir": True, "fondo": "#ffffff", "borde": 1,
                "sticky": "nsew", "rowconfigure": {"index": 1, "weight": 1, "minsize": 20},
                "columnconfigure": {"index": 0, "weight": 1, "minsize": 50}
            },
            "database_info": {
                "titulo": "", "columna": 13, "ancho": 15, "expandir": False, "fondo": "#f0f0f0", "borde": 1,
                "sticky": "ns", "rowconfigure": {"index": 1, "weight": 0, "minsize": 10},
                "columnconfigure": {"index": 0, "weight": 0, "minsize": 15}
            },
            "database_play30": {
                "titulo": "", "columna": 14, "ancho": 15, "expandir": False, "fondo": "#f0f0f0", "borde": 1,
                "sticky": "ns", "rowconfigure": {"index": 1, "weight": 0, "minsize": 10},
                "columnconfigure": {"index": 0, "weight": 0, "minsize": 15}
            },
            "database_play10": {
                "titulo": "", "columna": 15, "ancho": 15, "expandir": False, "fondo": "#f0f0f0", "borde": 1,
                "sticky": "ns", "rowconfigure": {"index": 1, "weight": 0, "minsize": 10},
                "columnconfigure": {"index": 0, "weight": 0, "minsize": 15}
            },
            "database_pausa": {
                "titulo": "", "columna": 16, "ancho": 15, "expandir": False, "fondo": "#f0f0f0", "borde": 1,
                "sticky": "ns", "rowconfigure": {"index": 1, "weight": 0, "minsize": 10},
                "columnconfigure": {"index": 0, "weight": 0, "minsize": 15}
            }
        }

        # Configurar las columnas de acuerdo a su propiedad 'expandir'
        for nombre_interno, config in columnas_config.items():
            # Configura el peso solo para las columnas que deben expandirse
            if config["expandir"]:
                self.frame_principal.grid_columnconfigure(config["columna"], weight=1)  # Expande
            else:
                self.frame_principal.grid_columnconfigure(config["columna"], weight=0)  # No expande

        # Configurar la expansión de la fila de contenido
        self.frame_principal.grid_rowconfigure(1, weight=1)

        # Crear encabezados para las agrupaciones con bordes
        archivo_label = tk.Label(
            self.frame_principal, text="Archivo", font=("Consolas", 12, "bold"),
            borderwidth=2, relief="solid"
        )
        archivo_label.grid(row=0, column=0, columnspan=7, sticky="nsew", padx=2, pady=2)

        base_datos_label = tk.Label(
            self.frame_principal, text="Base de datos", font=("Consolas", 12, "bold"),
            borderwidth=2, relief="solid"
        )
        base_datos_label.grid(row=0, column=7, columnspan=10, sticky="nsew", padx=2, pady=2)

        # Crear frames para las columnas usando la configuración detallada
        self.frames_columnas = {}
        for nombre_interno, config in columnas_config.items():
            frame_columna = ttk.Frame(self.frame_principal, borderwidth=config["borde"], relief="solid")
            frame_columna.grid(row=1, column=config["columna"], padx=2, pady=2, sticky=config["sticky"])

            # Configurar el frame de la columna con rowconfigure, columnconfigure y minsize
            frame_columna.grid_rowconfigure(config["rowconfigure"]["index"],
                                            weight=config["rowconfigure"]["weight"],
                                            minsize=config["rowconfigure"]["minsize"])
            frame_columna.grid_columnconfigure(config["columnconfigure"]["index"],
                                               weight=config["columnconfigure"]["weight"],
                                               minsize=config["columnconfigure"]["minsize"])

            # Configurar para que el frame de la columna tenga ancho fijo si no se expande
            if not config["expandir"]:
                frame_columna.grid_propagate(False)
                frame_columna.config(width=config["ancho"])

            # Título de la columna
            label = tk.Label(frame_columna, text=config["titulo"], font=("Consolas", 10), background=config["fondo"])
            label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

            # Guardar el frame en el diccionario con el nombre interno de la columna
            self.frames_columnas[nombre_interno] = frame_columna

        # Altura deseada para las columnas
        altura_columna = 10  # Puedes ajustar esta variable según tus necesidades

        # Crear una lista para almacenar las filas de frames
        self.frames_por_filas = []

        # Crear frames para las columnas usando la función personalizada y almacenarlos en filas
        self.crear_fila_de_frames(columnas_config, altura_columna, fila=1)
        self.crear_fila_de_frames(columnas_config, altura_columna, fila=1)

        # Ejemplo de lista con números que se mostrarán en cada columna
        numeros = [1, 2, 3, 4, 5]

        # Introducir la lista de números en los frames de la primera fila
        self.introducir_numeros_en_fila(0, numeros)

        # Introducir la lista de números en los frames de la primera fila
        self.introducir_numeros_en_fila(1, numeros)

    def crear_frame_columna(self, config, altura, fila):
        """
        Crea un frame para una columna con la configuración dada y una altura específica.

        :param config: Configuración de la columna (diccionario).
        :param altura: Altura deseada para el frame.
        :param fila: Número de fila en la que se debe colocar el frame.
        :return: El frame creado.
        """
        frame_columna = ttk.Frame(self.frame_principal, borderwidth=config["borde"], relief="solid")
        frame_columna.grid(row=fila, column=config["columna"], padx=2, pady=2, sticky=config["sticky"])

        # Configurar el frame de la columna con rowconfigure, columnconfigure y minsize
        frame_columna.grid_rowconfigure(config["rowconfigure"]["index"],
                                        weight=config["rowconfigure"]["weight"],
                                        minsize=config["rowconfigure"]["minsize"])
        frame_columna.grid_columnconfigure(config["columnconfigure"]["index"],
                                           weight=config["columnconfigure"]["weight"],
                                           minsize=config["columnconfigure"]["minsize"])

        # Configurar el frame para que tenga una altura fija
        frame_columna.config(height=altura)
        frame_columna.grid_propagate(False)  # Evitar que el frame cambie de tamaño con su contenido

        # Título de la columna
        label = tk.Label(frame_columna, text=config["titulo"], font=("Consolas", 10), background=config["fondo"])
        label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        return frame_columna

    def crear_fila_de_frames(self, columnas_config, altura, fila):
        """
        Crea una fila de frames y los guarda en una lista.

        :param columnas_config: Configuraciones de todas las columnas.
        :param altura: Altura deseada para los frames.
        :param fila: Número de fila en la que colocar los frames.
        """
        fila_frames = []  # Lista para almacenar los frames de esta fila

        for nombre_interno, config in columnas_config.items():
            frame_columna = self.crear_frame_columna(config, altura, fila)
            fila_frames.append(frame_columna)

        # Guardar la fila de frames en la lista de filas
        self.frames_por_filas.append(fila_frames)

    def introducir_numeros_en_fila(self, fila_index, numeros):
        """
        Introduce una lista de números en los frames de una fila específica.

        :param fila_index: Índice de la fila donde se introducirán los números.
        :param numeros: Lista de números a introducir en los frames.
        """
        if 0 <= fila_index < len(self.frames_por_filas):
            fila = self.frames_por_filas[fila_index]
            for index, frame in enumerate(fila):
                if index < len(numeros):
                    numero = numeros[index]
                    # Crear un label con el número y agregarlo al frame
                    label_numero = tk.Label(frame, text=str(numero), font=("Consolas", 10))
                    label_numero.grid(row=1, column=0, padx=5, pady=5, sticky="new")
        else:
            print("Índice de fila fuera de rango.")

if __name__ == "__main__":
    app = MiAplicacion()
    app.mainloop()