import unittest

import pandas as pd

from src.utils.coleccion import IndiceTengo


class TengoTest(unittest.TestCase):
    def setUp(self):
        self.indice = IndiceTengo(pd.DataFrame({
            "ruta": ["a.flac", "b.mp3", "MUSICA/_duplicados/c.mp3"],
            "title": ["Adiós, Bardi", "Rosa de otoño", "Rosa de otoño"],
            "artist": ["Osvaldo Pugliese", "Osvaldo Pugliese / Roberto Chanel", "Osvaldo Pugliese"],
            "year": ["1944-10-17", "2014", "1944"]}))

    def test_misma_grabacion(self):
        self.assertEqual(self.indice.buscar("Adiós Bardi", "Osvaldo Pugliese", "1944-10-17"), ("si", ["a.flac"]))

    def test_mismo_tema_otra_fecha(self):
        estado, rutas = self.indice.buscar("Rosa de otoño", "Orquesta Típica Osvaldo Pugliese", "1944-05-02")
        self.assertEqual((estado, rutas), ("otra", ["b.mp3"]))      # _duplicados no cuenta

    def test_no_la_tengo(self):
        self.assertEqual(self.indice.buscar("Recuerdo", "Osvaldo Pugliese", "1944"), ("", []))


if __name__ == "__main__":
    unittest.main()
