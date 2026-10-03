import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import src.config.config as cfg


class RutasOtroOrdenadorTest(unittest.TestCase):
    """El portátil tiene Dropbox en C:\Dropbox y el fijo en D:\Dropbox (config.ini es el mismo)."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.dropbox = os.path.join(self.dir, "Dropbox")
        os.makedirs(os.path.join(self.dropbox, "TDJ", "MUSICA"))
        self.cancion = os.path.join(self.dropbox, "TDJ", "MUSICA", "Ojos negros.mp3")
        open(self.cancion, "wb").close()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_ruta_de_otro_ordenador(self):
        with mock.patch.object(cfg, "dropbox_path", self.dropbox):
            self.assertEqual(cfg.ruta_local(r"Z:\Dropbox\TDJ\MUSICA\Ojos negros.mp3"), self.cancion)
            self.assertEqual(cfg.ruta_local("Z:/Dropbox/TDJ/MUSICA/Ojos negros.mp3"), self.cancion)
            # aunque aún no exista (p. ej. deshacer un movimiento: se vuelve a ese sitio)
            self.assertEqual(cfg.ruta_local(r"Z:\Dropbox\TDJ\MUSICA\Nueva.mp3"),
                             os.path.join(self.dropbox, "TDJ", "MUSICA", "Nueva.mp3"))
            self.assertEqual(cfg.ruta_local(self.cancion), self.cancion)          # ya es de aquí
            self.assertEqual(cfg.ruta_local(r"E:\Musica\x.mp3"), r"E:\Musica\x.mp3")  # no es de Dropbox

    def test_dropbox_se_detecta_si_config_ini_no_vale(self):
        local = os.path.join(self.dir, "local")
        os.makedirs(os.path.join(local, "Dropbox"))
        with open(os.path.join(local, "Dropbox", "info.json"), "w", encoding="utf-8") as f:
            json.dump({"personal": {"path": self.dropbox}}, f)
        config = cfg.configparser.ConfigParser()
        config.read_dict({"Paths": {"music_path": os.path.join("Q:" + os.sep, "no_existe", "Dropbox")}})
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": local, "APPDATA": local}), \
                mock.patch.object(cfg, "config", config):
            self.assertEqual(cfg.get_music_path(), self.dropbox)
        config.read_dict({"Paths": {"music_path": self.dir}})             # si config.ini vale, manda él
        with mock.patch.object(cfg, "config", config):
            self.assertEqual(cfg.get_music_path(), self.dir)


if __name__ == "__main__":
    unittest.main()
