import os
import tempfile
import unittest

from src.utils import coleccion, duplicados


def escribir(ruta, contenido):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(contenido)


class DuplicadosTest(unittest.TestCase):
    def setUp(self):
        self.raiz = tempfile.mkdtemp()
        self.registros = os.path.join(self.raiz, "registros")
        audio = os.urandom(300_000)
        otro = os.urandom(300_000)                       # mismo tamaño, distinto contenido
        escribir(os.path.join(self.raiz, "Eduardo", "1", "La Taba - 1_1.mp3"), audio)
        escribir(os.path.join(self.raiz, "Eduardo", "1", "La Taba.mp3"), audio)
        escribir(os.path.join(self.raiz, "Eduardo", "2", "Otra.mp3"), otro)
        escribir(os.path.join(self.raiz, "Dan", "La Taba.mp3"), audio)   # otra colección: no cuenta

    def archivos(self):
        return [(r, c, t) for r, c, t, _ in coleccion.listar(self.raiz)]

    def test_solo_identicas_y_dentro_de_la_misma_coleccion(self):
        grupos = duplicados.buscar(self.archivos())
        self.assertEqual(len(grupos), 1)
        self.assertEqual({os.path.basename(r) for r in grupos[0]}, {"La Taba - 1_1.mp3", "La Taba.mp3"})

    def test_sugerir_conservar_el_nombre_limpio(self):
        grupo = duplicados.buscar(self.archivos())[0]
        self.assertEqual(os.path.basename(duplicados.sugerir_conservar(grupo)), "La Taba.mp3")

    def test_mover_y_deshacer(self):
        grupo = duplicados.buscar(self.archivos())[0]
        copia = [r for r in grupo if r != duplicados.sugerir_conservar(grupo)]
        movidos, errores, registro = duplicados.mover(copia, self.raiz, self.registros)
        self.assertEqual((movidos, errores), (1, []))
        self.assertFalse(os.path.exists(copia[0]))
        destino = os.path.join(self.raiz, "_duplicados", "Eduardo", "1", "La Taba - 1_1.mp3")
        self.assertTrue(os.path.exists(destino))
        # _duplicados no se vuelve a recorrer
        self.assertEqual(duplicados.buscar(self.archivos()), [])
        self.assertEqual(duplicados.ultimo_registro(self.registros), registro)
        self.assertEqual(duplicados.deshacer(registro), (1, []))
        self.assertTrue(os.path.exists(copia[0]))


class ResumenTest(unittest.TestCase):
    def test_resumen_por_coleccion(self):
        import pandas as pd
        df = pd.DataFrame({
            "ruta": ["a", "b", "c"], "coleccion": ["Eduardo", "Eduardo", "Dan"], "bytes": ["1", "1", "1"],
            "mtime": ["0"] * 3, "title": ["x"] * 3, "artist": ["A / B", "A; B", "A"], "album": [""] * 3,
            "year": ["1941-07-14", "2014", ""], "genre": ["tango", "", "tango"],
            "composer": ["Musica: X - Letra: ?", "", ""]})
        r = coleccion.resumen(df)
        self.assertEqual(r.loc["Eduardo", "archivos"], 2)
        self.assertEqual(r.loc["Eduardo", "revisadas"], 1)
        self.assertEqual(r.loc["Eduardo", "fecha_cd"], 1)
        self.assertEqual(r.loc["Eduardo", "artista_raro"], 1)
        self.assertEqual(r.loc["Dan", "sin_fecha"], 1)
        self.assertEqual(r.loc["TOTAL", "archivos"], 3)


if __name__ == "__main__":
    unittest.main()
