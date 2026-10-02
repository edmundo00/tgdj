import os
import tempfile
import unittest

import pandas as pd

from src.utils import correcciones


class CorreccionesTest(unittest.TestCase):
    def setUp(self):
        self.archivo = os.path.join(tempfile.mkdtemp(), "correcciones.csv")
        self.db = pd.DataFrame({
            "titulo": ["Adiós Bardi", "Adios, Bardi", "Recuerdo"],
            "artista": ["Osvaldo Pugliese", "Osvaldo Pugliese", "Osvaldo Pugliese"],
            "cantor": ["-", "", "-"],
            "fecha": ["1944-10-17", "17/10/1944", "1944-08-11"],
            "estilo": ["tango", "tango", "tango"],
            "compositor_autor": ["Musica: Osvaldo Pugliese", "", ""],
        })

    def test_misma_grabacion_aunque_cambie_el_formato(self):
        c = correcciones.claves(self.db)
        self.assertEqual(c[0], c[1])
        self.assertNotEqual(c[0], c[2])

    def test_guardar_y_aplicar(self):
        clave = correcciones.claves(self.db)[0]
        correcciones.guardar(clave, {"musica": "Alfredo Gobbi"}, self.archivo)
        r = correcciones.aplicar(self.db, self.archivo)
        self.assertEqual(list(r["compositor_autor"]),
                         ["Musica: Alfredo Gobbi - Letra: ?", "Musica: Alfredo Gobbi - Letra: ?", ""])
        self.assertEqual(list(r["corregida"]), [True, True, False])
        self.assertEqual(list(r["titulo"]), list(self.db["titulo"]))   # lo que no se corrige no cambia

    def test_volver_a_corregir_reemplaza(self):
        clave = correcciones.claves(self.db)[0]
        correcciones.guardar(clave, {"musica": "X"}, self.archivo)
        correcciones.guardar(clave, {"musica": "Alfredo Gobbi", "fecha": "1944-10-18"}, self.archivo)
        self.assertEqual(len(correcciones.leer(self.archivo)), 1)
        r = correcciones.aplicar(self.db, self.archivo)
        self.assertEqual(r.loc[0, "fecha"], "1944-10-18")
        # la clave original se mantiene para poder corregir otra vez
        self.assertEqual(r.loc[0, "_clave_original"], clave)

    def test_sin_archivo(self):
        r = correcciones.aplicar(self.db, self.archivo)
        self.assertFalse(r["corregida"].any())


if __name__ == "__main__":
    unittest.main()
