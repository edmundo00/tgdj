import os
import unittest
from datetime import date

import pandas as pd

from src.diapos import catalogo, historial
from src.diapos.generador import agrupar_tandas
from tests.utils.caracter_test import tabla_temporal
from tests.utils.revision_test import Base


class CatalogoTest(Base):
    """Las propuestas salen del catálogo (aquí uno inventado con archivos de verdad en una carpeta temporal)."""

    def setUp(self):
        super().setUp()
        self.tabla = tabla_temporal()
        self.otra = os.path.join(self.dir, "MUSICA", "Dan")
        self.filas_cat = []

    def en_catalogo(self, artista, titulo, ano, genero="tango", estrellas=5, carpeta=None):
        c = self.cancion(artista, titulo, ano, genero, carpeta=carpeta)
        c["estrellas"] = estrellas
        self.filas_cat.append(c)
        return c

    def cat(self):
        df = pd.DataFrame(self.filas_cat)
        # como catalogo.catalogo(): solo lo que está en la carpeta del portátil
        return df[df["ruta"].str.startswith(self.edmundo)].reset_index(drop=True)

    def noche(self):
        filas = (self.tanda("Francisco Canaro / Ernesto Famá", anos=(1934, 1939, 1933),
                            titulos=["Todo te nombra", "Yo no sé porque te quiero", "Ventarrón"])
                 + [self.cortina("Careless Whisper")]
                 + self.tanda("Juan D'Arienzo", anos=(1936, 1936, 1935), genero="tango vals")
                 + [self.cortina("We Can't Stop")]
                 + self.tanda("Enrique Rodríguez / Armando Moreno", anos=(1942, 1943, 1943)))
        return agrupar_tandas(pd.DataFrame(filas))

    def test_proponer_tema(self):
        self.en_catalogo("Francisco Canaro / Ernesto Famá", "Qué importa", 1939)
        self.en_catalogo("Francisco Canaro / Roberto Maida", "Ciego", 1935)
        self.en_catalogo("Francisco Canaro / Ernesto Famá", "Todo te nombra", 1939)             # ya suena
        self.en_catalogo("Francisco Canaro / Ernesto Famá", "Sufro", 1950)                      # otra época
        self.en_catalogo("Francisco Canaro / Ernesto Famá", "Pocas estrellas", 1938, estrellas=3)
        self.en_catalogo("Francisco Canaro / Ernesto Famá", "De Dan", 1938, carpeta=self.otra)  # no en el portátil
        self.en_catalogo("Francisco Canaro", "Milonga criolla", 1936, "tango milonga")          # otro género
        p = catalogo.proponer_temas(self.cat(), self.noche(), 0, 1)
        self.assertEqual(list(p["title"]), ["Qué importa", "Ciego"])
        self.assertEqual(list(p["motivo"]), ["mismo cantor", "otro cantor"])
        todas = catalogo.proponer_temas(self.cat(), self.noche(), 0, 1, solo_5=False)
        self.assertIn("Pocas estrellas", list(todas["title"]))
        self.assertNotIn("De Dan", list(todas["title"]))

    def test_proponer_tanda_sin_orquestas_cerca_ni_temas_usados(self):
        for t, a in (("Alma", 1932), ("El trece", 1932), ("Inspiración", 1932)):
            self.en_catalogo("Adolfo Carabelli / Alberto Gómez", t, a)
        for t, a in (("a", 1940), ("b", 1941), ("c", 1941)):
            self.en_catalogo("Juan D'Arienzo", t, a)                                 # D'Arienzo suena cerca
        for t, a in (("Uno", 1930), ("Dos", 1945), ("Tres", 1955)):
            self.en_catalogo("Edgardo Donato", t, a)                                 # años demasiado separados
        p = catalogo.proponer_tandas(self.cat(), self.noche(), 4, archivo_caracter=self.tabla)
        self.assertEqual([(x.orquesta, x.cantor) for x in p], [("Adolfo Carabelli", "Alberto Gómez")])
        self.assertEqual(list(p[0].canciones["title"]), ["Alma", "El trece", "Inspiración"])

    def test_proponer_cortina_sin_repetir_aqui(self):
        nueva = self.en_catalogo("Chuck Berry", "School Day", 1957, "cortina entera")
        vieja = self.en_catalogo("Rosalía", "Despechá", 2022, "cortina entera")
        self.en_catalogo("Pop", "Careless Whisper", 2014, "cortina entera")              # mismo título, otro archivo
        antes = historial.Milonga(date(2026, 1, 1), "260101_Milonga_Mia", {historial.clave(vieja["ruta"])})
        tandas = self.noche()
        p = catalogo.proponer_cortinas(self.cat(), tandas, 1, [antes])
        self.assertIn("School Day", list(p["title"]))
        self.assertNotIn("Despechá", list(p["title"]))
        self.assertNotIn(nueva["ruta"], [c for t in tandas for c in t.canciones["ruta"]])


if __name__ == "__main__":
    unittest.main()
