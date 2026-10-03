import unittest

import pandas as pd

from src.ui.vista_biblioteca import normalizar_serie
from src.utils.buscador import normalizar


class NormalizarSerieTest(unittest.TestCase):
    def test_igual_que_normalizar(self):
        textos = ["Adiós, Bardi", "Miguel Caló / Raúl Berón", "Pa' que bailen los muchachos", "Ñaña  Ü",
                  "D'Arienzo | 1944-03-31", "Musica: ? - Letra: ?", ""]
        self.assertEqual(normalizar_serie(pd.Series(textos)).tolist(), [normalizar(t) for t in textos])


if __name__ == "__main__":
    unittest.main()
