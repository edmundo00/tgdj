import unittest

from src.utils.buscar_artista import (
    IndiceArtistas, separar_orquesta_cantor, normalizar_nombre, EXACTA, NORMALIZADA, PARCIAL, NINGUNA,
)

CLAVES = ["Juan D'Arienzo", "Los Solistas de D'Arienzo", "Orquesta La Juan D'Arienzo", "Carlos Di Sarli",
          "Carlos di Sarli", "Osvaldo Pugliese", "Orquesta Típica Victor", "Francisco Canaro", "Rafael Canaro",
          "Ángel D'Agostino"]


class SepararTest(unittest.TestCase):
    def test_separadores(self):
        self.assertEqual(separar_orquesta_cantor("Juan D'Arienzo / Héctor Mauré"), ("Juan D'Arienzo", "Héctor Mauré"))
        self.assertEqual(separar_orquesta_cantor("Juan D'Arienzo; Alberto Echagüe"), ("Juan D'Arienzo", "Alberto Echagüe"))
        self.assertEqual(separar_orquesta_cantor("Juan D'Arienzo feat. Héctor Mauré"), ("Juan D'Arienzo", "Héctor Mauré"))
        self.assertEqual(separar_orquesta_cantor("Osvaldo Pugliese"), ("Osvaldo Pugliese", ""))
        self.assertEqual(separar_orquesta_cantor(None), ("", ""))

    def test_normalizar(self):
        self.assertEqual(normalizar_nombre("Orquesta Típica de Juan D'Arienzo"), "juan darienzo")
        self.assertEqual(normalizar_nombre("Ángel D´Agostino"), "angel dagostino")


class IndiceTest(unittest.TestCase):
    def setUp(self):
        self.indice = IndiceArtistas(CLAVES)

    def test_exacta_agrupa_variantes_de_mayusculas(self):
        claves, nivel = self.indice.buscar("Carlos Di Sarli")
        self.assertEqual(nivel, EXACTA)
        self.assertEqual(set(claves), {"Carlos Di Sarli", "Carlos di Sarli"})

    def test_normalizada(self):
        self.assertEqual(self.indice.buscar("juan d'arienzo")[1], NORMALIZADA)
        self.assertEqual(self.indice.buscar("Angel DAgostino / Angel Vargas"), (["Ángel D'Agostino"], NORMALIZADA))

    def test_apellido_nombre(self):
        claves, nivel = self.indice.buscar("D'Arienzo, Juan")
        self.assertEqual(nivel, NORMALIZADA)
        self.assertIn("Juan D'Arienzo", claves)
        self.assertNotIn("Los Solistas de D'Arienzo", claves)

    def test_punto_y_coma(self):
        claves, nivel = self.indice.buscar("Juan D'Arienzo; Alberto Echagüe")
        self.assertEqual(nivel, EXACTA)
        self.assertIn("Juan D'Arienzo", claves)

    def test_relleno(self):
        self.assertEqual(self.indice.buscar("Orquesta Típica de Osvaldo Pugliese"), (["Osvaldo Pugliese"], NORMALIZADA))

    def test_parcial(self):
        claves, nivel = self.indice.buscar("Pugliese")
        self.assertEqual((claves, nivel), (["Osvaldo Pugliese"], PARCIAL))
        claves, _ = self.indice.buscar("Canaro")
        self.assertEqual(set(claves), {"Francisco Canaro", "Rafael Canaro"})

    def test_no_encontrado(self):
        self.assertEqual(self.indice.buscar("Orquesta Inexistente"), (None, NINGUNA))
        self.assertEqual(self.indice.buscar(""), (None, NINGUNA))


if __name__ == "__main__":
    unittest.main()
