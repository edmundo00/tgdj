import os
import tempfile
import unittest

import pandas as pd

from src.diapos import caracter
from src.diapos.generador import agrupar_tandas
from src.diapos.revision import revisar, AVISO, INFO
from tests.utils.revision_test import Base

TABLA = """orquesta;desde;hasta;cantor;caracter;energia;dificultad;notas
Juan D'Arienzo;1935;1939;;ritmico;5;1;
Juan D'Arienzo;1940;1949;Mauré;melodico;4;1;
Juan D'Arienzo;1940;1949;;ritmico;5;1;
Ricardo Tanturi;1941;1943;Castillo;ritmico;4;1;
Ricardo Tanturi;1943;1956;Campos;melodico;3;1;
Osvaldo Pugliese;1943;1995;;dramatico;4;3;Para el final
Osvaldo Fresedo;1933;1939;;melodico;2;1;
Lucio Demare;1938;1968;;lirico;2;2;
Miguel Caló;1941;1945;;melodico;2;1;
Orquesta Típica Victor;1925;1944;;ritmico;3;1;
Sexteto Cristal;;;;ritmico;4;1;Actual
Edgardo Donato;1930;1945;;ritmico;4;1;
Donato Racciatti;1951;1969;;ritmico;3;1;
"""


def tabla_temporal():
    ruta = os.path.join(tempfile.mkdtemp(), "caracter.csv")
    with open(ruta, "w", encoding="utf-8-sig") as f:
        f.write(TABLA)
    return ruta


class CaracterTest(unittest.TestCase):
    def setUp(self):
        self.tabla = tabla_temporal()

    def buscar(self, *args):
        return caracter.buscar(*args, archivo=self.tabla)

    def test_por_epoca(self):
        self.assertEqual(self.buscar("Juan D'Arienzo", 1937).energia, 5)
        self.assertEqual(self.buscar("Juan D'arienzo", 1945, "Alberto Echagüe").caracter, "ritmico")

    def test_por_cantor(self):
        self.assertEqual(self.buscar("Juan D'Arienzo", 1941, "Héctor Mauré").caracter, "melodico")
        self.assertEqual(self.buscar("Ricardo Tanturi", 1943, "Enrique Campos").caracter, "melodico")
        self.assertEqual(self.buscar("Ricardo Tanturi", 1943, "Alberto Castillo").caracter, "ritmico")
        self.assertIsNone(self.buscar("Ricardo Tanturi", 1943, ""))     # solo hay filas con cantor

    def test_sin_anos_y_epoca_mas_cercana(self):
        self.assertEqual(self.buscar("Sexteto Cristal", 2019).notas, "Actual")
        self.assertEqual(self.buscar("Juan D'Arienzo", 2013).caracter, "ritmico")    # fecha de CD -> la más cercana
        self.assertEqual(self.buscar("Orquesta Tipica Victor", None).energia, 3)

    def test_no_confunde_orquestas(self):
        self.assertEqual(self.buscar("Donato Racciatti", 1953).energia, 3)
        self.assertEqual(self.buscar("Edgardo Donato", 1938).energia, 4)
        self.assertIsNone(self.buscar("Héctor Varela", 1955))


class RevisionCaracterTest(Base):
    def setUp(self):
        super().setUp()
        self.tabla = tabla_temporal()

    def noche(self, *tandas):
        filas = []
        for n, (artista, anos) in enumerate(tandas):
            if filas:
                filas.append(self.cortina(f"c{n}"))
            filas += self.tanda(artista, anos=anos)
        return filas

    def revisar_con_tabla(self, filas):
        tandas = agrupar_tandas(pd.DataFrame(filas))
        return revisar(tandas, carpeta=self.edmundo, minutos_sin_milonga=0, archivo_caracter=self.tabla)

    def test_mezcla_de_caracter_dentro_de_la_tanda(self):
        filas = [self.cancion("Juan D'Arienzo / Héctor Mauré", "Tierrita", 1941),
                 self.cancion("Juan D'Arienzo / Héctor Mauré", "Amarras", 1944),
                 self.cancion("Juan D'Arienzo", "Pensalo bien", 1937)]
        avisos = self.revisar_con_tabla(filas)
        self.assertTrue(any("mezcla carácter" in a.texto and "Pensalo bien" in a.texto
                            for a in avisos if a.nivel == AVISO))

    def test_tandas_tranquilas_seguidas(self):
        filas = self.noche(("Osvaldo Fresedo", (1935,) * 3), ("Lucio Demare", (1943,) * 3),
                           ("Miguel Caló", (1942,) * 3), ("Juan D'Arienzo", (1937,) * 3))
        avisos = self.revisar_con_tabla(filas)
        self.assertTrue(any("3 tandas tranquilas seguidas" in a.texto for a in avisos if a.nivel == INFO))

    def test_abrir_con_dificil_segun_la_tabla(self):
        filas = self.noche(("Osvaldo Pugliese", (1945,) * 3), ("Juan D'Arienzo", (1937,) * 3))
        avisos = self.revisar_con_tabla(filas)
        self.assertTrue(any("Abrir con Osvaldo Pugliese" in a.texto for a in avisos))

    def test_orquestas_sin_tabla(self):
        filas = self.noche(("Héctor Varela", (1955,) * 3), ("Juan D'Arienzo", (1937,) * 3))
        avisos = self.revisar_con_tabla(filas)
        self.assertTrue(any("Sin carácter en la tabla" in a.texto and "Héctor Varela" in a.texto for a in avisos))


if __name__ == "__main__":
    unittest.main()
