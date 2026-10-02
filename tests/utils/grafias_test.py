import os
import tempfile
import unittest

import pandas as pd

from src.utils import grafias


class GrafiasTest(unittest.TestCase):
    def setUp(self):
        self.archivo = os.path.join(tempfile.mkdtemp(), "grafias.csv")

    def test_guardar_leer_y_aplicar(self):
        grafias.guardar(["Carlos di Sarli", "Floreal Ruiz", "Alfredo de Angelis"], self.archivo)
        pref = grafias.leer(self.archivo)
        db = pd.DataFrame({"artista": ["Carlos Di Sarli", "Alfredo De Angelis", "Juan D'Arienzo"],
                           "cantor": ["Floreal Ruíz,Alberto Podestá", "Floreal Ruíz y Carlos Dante", "-"]})
        r = grafias.aplicar(db, pref)
        self.assertEqual(list(r["artista"]), ["Carlos di Sarli", "Alfredo de Angelis", "Juan D'Arienzo"])
        self.assertEqual(list(r["cantor"]), ["Floreal Ruiz,Alberto Podestá", "Floreal Ruiz y Carlos Dante", "-"])

    def test_diferencias_propone_la_de_la_coleccion(self):
        d = grafias.diferencias({"Carlos di Sarli": 2467, "Carlos Di Sarli": 2, "Osvaldo Pugliese": 900},
                                ["Carlos Di Sarli", "Osvaldo Pugliese"], preferidas={})
        self.assertEqual(len(d), 1)                       # Pugliese se escribe igual: no aparece
        fila = d.iloc[0]
        self.assertEqual(fila["grafia_bd"], "Carlos Di Sarli")
        self.assertEqual(fila["elegida"], "Carlos di Sarli")
        self.assertEqual(fila["archivos"], 2469)

    def test_la_eleccion_guardada_manda(self):
        d = grafias.diferencias({"Raul Iriarte": 382}, ["Raúl Iriarte"], preferidas={"raul iriarte": "Raúl Iriarte"})
        self.assertEqual(d.iloc[0]["elegida"], "Raúl Iriarte")


if __name__ == "__main__":
    unittest.main()
