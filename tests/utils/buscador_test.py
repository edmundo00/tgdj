import unittest

import pandas as pd

from src.utils.buscador import IndiceBusqueda, interpretar_consulta


def fila(titulo, artista, cantor, fecha, estilo="tango", compositor="", origen="recodo", audio30=""):
    return dict(titulo=titulo, artista=artista, cantor=cantor, fecha=fecha, estilo=estilo,
                compositor_autor=compositor, audio30=audio30, audio10="", origen=origen)


DB = pd.DataFrame([
    fila("Noche calurosa", "Roberto Firpo", "-", "1944-09-11", "tango vals", "", "tangoinfo"),
    fila("Noche calurosa", "Roberto Firpo", "", "1944-09-11", "tango vals", "Musica: Roberto Firpo - Letra: ?",
         "recodo", "a/b.mp3"),
    fila("Rosas de abril", "Roberto Firpo", "Teófilo Ibáñez", "1928-04-25", "tango vals"),
    fila("La rosarina", "Roberto Firpo", "-", "1949-10-21"),
    fila("Rosa", "Roberto Firpo", "-", "1930"),
    fila("Rosa de otoño", "Osvaldo Pugliese", "Roberto Chanel", "1944-05-02"),
    fila("Recuerdo", "Osvaldo Pugliese", "-", "1944-08-11", "tango", "Musica: Osvaldo Pugliese - Letra: Eduardo Moreno"),
    fila("Gallo ciego", "Osvaldo Pugliese", "-", "1959-06-01", "tango", "", "tangoinfo"),
])


class InterpretarTest(unittest.TestCase):
    def test_anos(self):
        self.assertEqual(interpretar_consulta("Pugliese 1944"), (["pugliese"], 1944, 1944))
        self.assertEqual(interpretar_consulta("firpo 1930-1920"), (["firpo"], 1920, 1930))
        self.assertEqual(interpretar_consulta("1940s Caló"), (["calo"], 1940, 1949))
        self.assertEqual(interpretar_consulta("  "), ([], None, None))


class BuscadorTest(unittest.TestCase):
    def setUp(self):
        self.indice = IndiceBusqueda(DB)

    def test_agrupa_duplicados_con_todas_las_fuentes(self):
        r = self.indice.buscar("noche calurosa")
        self.assertEqual(len(r), 1)
        g = r.iloc[0]
        self.assertEqual(g["fuentes"], ("recodo", "tangoinfo"))
        self.assertEqual(g["repeticiones"], 2)
        self.assertEqual(g["musica"], "Roberto Firpo")   # se queda con la fila más completa
        self.assertEqual(g["audio30"], "a/b.mp3")

    def test_palabras_en_cualquier_orden_y_campo(self):
        self.assertEqual(list(self.indice.buscar("firpo rosa")["titulo"])[:1], ["Rosa"])
        self.assertEqual(list(self.indice.buscar("chanel pugliese")["titulo"]), ["Rosa de otoño"])
        self.assertEqual(list(self.indice.buscar("moreno")["titulo"]), ["Recuerdo"])  # letrista

    def test_sin_acentos(self):
        self.assertEqual(list(self.indice.buscar("teofilo ibanez")["titulo"]), ["Rosas de abril"])

    def test_relevancia_titulo_exacto_y_luego_empieza_por(self):
        titulos = list(self.indice.buscar("rosa")["titulo"])
        self.assertEqual(titulos[0], "Rosa")
        self.assertEqual(titulos[1:3], ["Rosa de otoño", "Rosas de abril"])
        self.assertEqual(titulos[-1], "La rosarina")
        self.assertNotIn("Noche calurosa", titulos)   # "rosa" no es comienzo de palabra en "calurosa"

    def test_anos_en_la_consulta(self):
        self.assertEqual(set(self.indice.buscar("pugliese 1944")["titulo"]), {"Rosa de otoño", "Recuerdo"})
        self.assertEqual(list(self.indice.buscar("pugliese 1950s")["titulo"]), ["Gallo ciego"])

    def test_filtros(self):
        self.assertEqual(set(self.indice.buscar("firpo", estilos={"vals"})["titulo"]),
                         {"Noche calurosa", "Rosas de abril"})
        self.assertEqual(list(self.indice.buscar("pugliese", fuentes={"tangoinfo"})["titulo"]), ["Gallo ciego"])


if __name__ == "__main__":
    unittest.main()
