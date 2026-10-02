import os
import tempfile
import unittest

from src.utils import no_tocar
from src.config.config import dropbox_path


class NoTocarTest(unittest.TestCase):
    def setUp(self):
        self.archivo = os.path.join(tempfile.mkdtemp(), "no_tocar.csv")

    def test_marcar_y_desmarcar(self):
        ruta = os.path.join(dropbox_path, "TDJ", "MUSICA", "Firpo", "Ojos negros.flac")
        no_tocar.marcar([(ruta, "Ojos negros")], self.archivo)
        no_tocar.marcar([(ruta, "Ojos negros")], self.archivo)        # no se duplica
        conjunto = no_tocar.claves(self.archivo)
        self.assertEqual(len(conjunto), 1)
        self.assertTrue(no_tocar.esta(ruta, conjunto))
        self.assertTrue(no_tocar.esta(ruta.upper(), conjunto))       # Windows: mayúsculas da igual
        no_tocar.desmarcar([ruta], self.archivo)
        self.assertFalse(no_tocar.esta(ruta, no_tocar.claves(self.archivo)))

    def test_clave_relativa_a_dropbox(self):
        ruta = os.path.join(dropbox_path, "TDJ", "MUSICA", "x.mp3")
        self.assertEqual(no_tocar._clave(ruta), "tdj/musica/x.mp3")


if __name__ == "__main__":
    unittest.main()
