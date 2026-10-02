import os
import shutil
import subprocess
import tempfile
import unittest

from tinytag import TinyTag

from src.utils.historial import guardar_backup, listar_backups, deshacer, resumen_backup
from src.utils.utils import escribir_tags, update_tags


@unittest.skipIf(shutil.which("ffmpeg") is None, "hace falta ffmpeg para crear audio de prueba")
class HistorialTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.backups = os.path.join(self.dir, "backups")
        self.archivos = []
        for ext in ("mp3", "flac", "m4a", "wav"):
            ruta = os.path.join(self.dir, f"prueba.{ext}")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=d=1",
                            "-metadata", "title=Humillacion", "-metadata", "date=1941", ruta], check=True)
            self.archivos.append(ruta)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_aplicar_y_deshacer(self):
        nuevas = {"title": "Humillación", "year": "1941-07-14", "composer": "Musica: ? - Letra: ?"}
        cambios = []
        for ruta in self.archivos:
            t = TinyTag.get(ruta)
            antes = {"title": t.title or "", "year": t.year or "", "composer": t.composer or ""}
            cambios.append((ruta, antes, nuevas))
        backup = guardar_backup(cambios, carpeta=self.backups)
        for ruta in self.archivos:
            self.assertTrue(update_tags(ruta, **nuevas))
            self.assertEqual(TinyTag.get(ruta).composer, "Musica: ? - Letra: ?")

        self.assertEqual(listar_backups(self.backups), [backup])
        self.assertIn("4 archivo(s)", resumen_backup(backup))

        restaurados, errores = deshacer(backup, escribir_tags)
        self.assertEqual((restaurados, errores), (4, []))
        for ruta in self.archivos:
            t = TinyTag.get(ruta)
            self.assertEqual((t.title, t.year), ("Humillacion", "1941"), ruta)
            self.assertFalse(t.composer, ruta)  # antes no tenía compositor: se borra
        self.assertEqual(listar_backups(self.backups), [])


if __name__ == "__main__":
    unittest.main()
