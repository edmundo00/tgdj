import unittest
from types import SimpleNamespace

import pandas as pd

from src.constants.enums import TagLabels
from src.utils.utils import compare_tags


def tag(**kw):
    datos = dict(title="", artist="", year="", genre="", composer="", _filename="x.flac")
    datos.update(kw)
    return SimpleNamespace(**datos)


class CompareTagsTest(unittest.TestCase):
    def setUp(self):
        self.db = pd.DataFrame({
            'titulo': ['Humillación', 'Humillación'],
            'artista': ["Juan D'Arienzo", "Juan D'Arienzo"],
            'cantor': ["Héctor Mauré", "-"],
            'fecha': ["1941-07-14", "1950"],
            'estilo': ["tango", "tango"],
            'compositor_autor': ["Musica: Rodolfo Biagi - Letra: Carlos Bahr", ""],
        })

    def test_perfecta_si_no_cambiaria_nada(self):
        t = tag(title="Humillación", artist="Juan D'Arienzo / Héctor Mauré", year="1941-07-14", genre="tango",
                composer="Musica: Rodolfo Biagi - Letra: Carlos Bahr")
        c, perfecta, indice = compare_tags(3, 6, self.db, t)
        self.assertTrue(perfecta)
        self.assertEqual(indice, 0)

    def test_mayusculas_y_formato_de_fecha_no_cuentan_como_distinto(self):
        t = tag(title="Humillacion", artist="Juan D'Arienzo / Héctor Mauré", year="14/07/1941", genre="Tango")
        c, perfecta, _ = compare_tags(3, 5, self.db, t)
        self.assertFalse(perfecta)                           # falta el compositor
        self.assertTrue(c[TagLabels.FECHA_EXACTA].iloc[0])
        self.assertTrue(c[TagLabels.ESTILO_EXACTO].iloc[0])
        self.assertTrue(c[TagLabels.CANTOR_EXACTO].iloc[0])
        self.assertTrue(c[TagLabels.CANTOR_NEGATIVO].iloc[1])  # la otra grabación es instrumental

    def test_solo_el_ano_es_parecido(self):
        t = tag(title="Humillación", artist="Juan D'Arienzo", year="1941")
        c, _, _ = compare_tags(3, 6, self.db, t)
        self.assertTrue(c[TagLabels.FECHA].iloc[0])           # amarillo: mismo año
        self.assertTrue(c[TagLabels.FECHA_NEGATIVA].iloc[1])  # rojo: 1950

    def test_un_solo_grupo_activo_por_campo(self):
        t = tag(title="Humillación", artist="Juan D'Arienzo / Héctor Mauré", year="1941")
        c, _, _ = compare_tags(3, 6, self.db, t)
        grupos = [(TagLabels.FECHA_EXACTA, TagLabels.FECHA, TagLabels.FECHA_PARCIAL, TagLabels.FECHA_NEGATIVA),
                  (TagLabels.CANTOR_EXACTO, TagLabels.CANTOR, TagLabels.CANTOR_PARCIAL, TagLabels.CANTOR_NEGATIVO)]
        for grupo in grupos:
            for i in range(len(self.db)):
                self.assertEqual(sum(bool(c[e].iloc[i]) for e in grupo), 1)


if __name__ == '__main__':
    unittest.main()
