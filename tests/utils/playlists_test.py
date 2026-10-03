import os
import tempfile
import unittest

import pandas as pd

from src.utils import playlists
from src.utils.utils import load_m3u_file_helper


class PlaylistsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.musica = os.path.join(self.dir, "MUSICA")
        os.makedirs(os.path.join(self.musica, "Nueva"))
        self.movida = os.path.join(self.musica, "Nueva", "Juan Maglio - Tango Argentino.flac")
        with open(self.movida, "wb") as f:
            f.write(b"x" * 1234)
        self.existe = os.path.join(self.musica, "Nueva", "Otra.flac")
        with open(self.existe, "wb") as f:
            f.write(b"y" * 10)
        self.m3u = os.path.join(self.dir, "milonga.m3u")
        vieja = os.path.join(self.musica, "Vieja", "Juan Maglio - Tango Argentino.flac")
        contenido = ("﻿#EXTVDJ:<filesize>1234</filesize><artist>Juan Maglio</artist><title>Tango Argentino</title>\r\n"
                     "\r\n" + vieja + "\r\n" + self.existe + "\r\n")
        with open(self.m3u, "w", encoding="utf-8", newline="") as f:
            f.write(contenido)
        self.cache = pd.DataFrame({
            "ruta": [self.movida, self.existe], "bytes": ["1234", "10"],
            "artist": ["Juan Maglio", ""], "title": ["Tango argentino", "Otra"]})

    def test_bom_de_virtualdj_no_es_una_cancion(self):
        rutas = load_m3u_file_helper(self.m3u)
        self.assertEqual(len(rutas), 2)
        self.assertFalse(any("EXTVDJ" in r for r in rutas))

    def test_encuentra_la_cancion_movida_y_repara(self):
        indice = playlists.IndiceColeccion(self.cache)
        entradas = playlists.analizar(self.m3u, indice)
        rotas = [e for e in entradas if not e.existe]
        self.assertEqual(len(rotas), 1)
        e = rotas[0]
        self.assertEqual((e.artista, e.titulo, e.tamano), ("Juan Maglio", "Tango Argentino", 1234))
        self.assertEqual(playlists.propuesta_segura(e), self.movida)
        self.assertIn("mismo tamaño", e.candidatos[0][1])

        copia = playlists.reparar(self.m3u, {e.linea: self.movida}, os.path.join(self.dir, "copias"))
        self.assertTrue(os.path.exists(copia))
        self.assertTrue(all(x.existe for x in playlists.analizar(self.m3u, indice)))
        with open(self.m3u, "rb") as f:
            crudo = f.read()
        self.assertIn(b"#EXTVDJ:", crudo)          # se conserva el resto
        self.assertIn(b"\r\n", crudo)              # y los saltos de línea de Windows

        playlists.restaurar(copia, self.m3u)
        self.assertEqual(len([x for x in playlists.analizar(self.m3u, indice) if not x.existe]), 1)


class PropuestaSeguraTest(unittest.TestCase):
    def test_sin_tamano_un_nombre_parecido_no_es_seguro(self):
        e = playlists.Entrada(0, r"D:\x\Cortinas Cortadas\Ava Max - Salt.mp3", False)
        e.candidatos = [(r"D:\x\Cortinas Enteras\Ava Max - Salt.flac", "nombre de archivo parecido", False)]
        self.assertIsNone(playlists.propuesta_segura(e))

    def test_sin_tamano_mismo_nombre_exacto_si(self):
        e = playlists.Entrada(0, r"D:\x\Vieja\Ava Max - Salt.mp3", False)
        e.candidatos = [(r"D:\x\Nueva\Ava Max - Salt.mp3", "mismo nombre de archivo", False)]
        self.assertEqual(playlists.propuesta_segura(e), r"D:\x\Nueva\Ava Max - Salt.mp3")


if __name__ == "__main__":
    unittest.main()
