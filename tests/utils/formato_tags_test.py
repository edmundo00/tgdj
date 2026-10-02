import unittest

from src.utils.formato_tags import (
    formatear_artista, formatear_fecha, formatear_estilo, formatear_compositor,
    normalizar_compositor_autor, separar_compositor_autor, tags_desde_coincidencia, combinar_compositor,
)


class FormatoFechaTest(unittest.TestCase):
    def test_formatos_completos(self):
        self.assertEqual(formatear_fecha("1941-03-12"), "1941-03-12")
        self.assertEqual(formatear_fecha("12/03/1941"), "1941-03-12")
        self.assertEqual(formatear_fecha("12-03-1941"), "1941-03-12")
        self.assertEqual(formatear_fecha("19410312"), "1941-03-12")

    def test_fechas_parciales(self):
        self.assertEqual(formatear_fecha("1941"), "1941")
        self.assertEqual(formatear_fecha("1953-10"), "1953-10")
        self.assertEqual(formatear_fecha("1941-00-00"), "1941")
        self.assertEqual(formatear_fecha("1941-03-00"), "1941-03")

    def test_desconocidas(self):
        for valor in ["", None, "?", "1930--1941", "2001-10--11", "sin fecha"]:
            self.assertEqual(formatear_fecha(valor), "", valor)


class FormatoArtistaTest(unittest.TestCase):
    def test_orquesta_y_cantor(self):
        self.assertEqual(formatear_artista("Juan D'Arienzo", "Héctor Mauré"), "Juan D'Arienzo / Héctor Mauré")

    def test_instrumental(self):
        self.assertEqual(formatear_artista("Juan D'Arienzo", "-"), "Juan D'Arienzo")
        self.assertEqual(formatear_artista("Juan D'Arienzo", ""), "Juan D'Arienzo")
        self.assertEqual(formatear_artista(" Juan  D'Arienzo ", None), "Juan D'Arienzo")

    def test_varios_cantores(self):
        self.assertEqual(formatear_artista("Francisco Canaro", "Carlos Gardel,José Razzano"),
                         "Francisco Canaro / Carlos Gardel y José Razzano")
        self.assertEqual(formatear_artista("X", "A, B,C"), "X / A, B y C")


class FormatoCompositorTest(unittest.TestCase):
    def test_formatear(self):
        self.assertEqual(formatear_compositor("Mariano Mores", "Enrique Santos Discépolo"),
                         "Musica: Mariano Mores - Letra: Enrique Santos Discépolo")
        self.assertEqual(formatear_compositor("Mariano Mores", "?"), "Musica: Mariano Mores - Letra: ?")
        self.assertEqual(formatear_compositor("?", "Homero Manzi"), "Musica: ? - Letra: Homero Manzi")
        self.assertEqual(formatear_compositor("", ""), "Musica: ? - Letra: ?")

    def test_normalizar_desde_bd(self):
        self.assertEqual(normalizar_compositor_autor("Musica: ? - Letra: ?"), "Musica: ? - Letra: ?")
        self.assertEqual(normalizar_compositor_autor(""), "Musica: ? - Letra: ?")
        self.assertEqual(normalizar_compositor_autor("Desconocido"), "Musica: ? - Letra: ?")
        self.assertEqual(normalizar_compositor_autor("Musica: Horacio Pettorossi - Letra: Horacio Pettorossi"),
                         "Musica: Horacio Pettorossi - Letra: Horacio Pettorossi")
        self.assertEqual(normalizar_compositor_autor("Letra: Homero Manzi"), "Musica: ? - Letra: Homero Manzi")
        self.assertEqual(normalizar_compositor_autor("Musica:  A  -  Letra:  B "), "Musica: A - Letra: B")

    def test_combinar_no_pierde_lo_que_sabe_el_archivo(self):
        self.assertEqual(combinar_compositor("Richard Russo", "Musica: ? - Letra: ?"),
                         "Musica: Richard Russo - Letra: ?")
        self.assertEqual(combinar_compositor("Musica: ? - Letra: Homero Manzi", "Musica: Sebastián Piana - Letra: ?"),
                         "Musica: Sebastián Piana - Letra: Homero Manzi")
        # si la BD lo sabe, manda la BD
        self.assertEqual(combinar_compositor("Musica: X", "Musica: Rosita Melo - Letra: ?"),
                         "Musica: Rosita Melo - Letra: ?")

    def test_separar(self):
        self.assertEqual(separar_compositor_autor("Musica: A - Letra: B"), ("A", "B"))
        self.assertEqual(separar_compositor_autor("Ángel Villoldo"), ("Ángel Villoldo", ""))


class FormatoEstiloTest(unittest.TestCase):
    def test_estilos(self):
        self.assertEqual(formatear_estilo("Tango"), "tango")
        self.assertEqual(formatear_estilo("tango vals"), "tango vals")
        self.assertEqual(formatear_estilo("Vals"), "tango vals")
        self.assertEqual(formatear_estilo("?"), "")


class TagsDesdeCoincidenciaTest(unittest.TestCase):
    def test_fila_completa(self):
        fila = {"titulo": "El olivo ", "artista": "Juan D'Arienzo", "cantor": "Héctor Mauré",
                "fecha": "1941-03-12", "estilo": "tango", "compositor_autor": "Musica: ? - Letra: ?"}
        self.assertEqual(tags_desde_coincidencia(fila), {
            "title": "El olivo",
            "artist": "Juan D'Arienzo / Héctor Mauré",
            "year": "1941-03-12",
            "genre": "tango",
            "composer": "Musica: ? - Letra: ?",
        })


if __name__ == "__main__":
    unittest.main()
