import unittest

import pandas as pd

from src.utils.utils import contain_most_words


class TestContainMostWords(unittest.TestCase):
    def setUp(self):
        self.database = pd.DataFrame({
            'titulo_min': [
                "adiós nonino (live)",  # 2 palabras en común
                "adios nonino",         # 2
                "goodbye nonino",       # 1
                "nonino adiós (vivo)",  # 3: mismas palabras, otro orden
                "vivo adiós nonino",    # 3
                "something else",       # 0
            ]
        })

    def test_contain_most_words(self):
        coincidencias = contain_most_words(self.database, "Adiós nonino (vivo)", 'titulo_min')
        self.assertEqual(list(coincidencias[coincidencias].index), [3, 4])


if __name__ == '__main__':
    unittest.main()
