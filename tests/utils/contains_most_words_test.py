import unittest
import pandas as pd
from src.utils.utils import contain_most_words

class TestContainMostWords(unittest.TestCase):

    def setUp(self):
        # Set up a sample DataFrame for testing
        self.database = pd.DataFrame({
            'titulo_min': [
                "adiós nonino (live)",  # Similar to the input, but 'live' instead of 'vivo'
                "adios nonino",         # Matches except for missing '(vivo)'
                "goodbye nonino",       # Different language
                "nonino adiós (vivo)",  # Same words, different order
                "vivo adiós nonino",    # Same words, different order
                "something else"        # Completely different
            ]
        })

    def test_contain_most_words(self):
        title = "Adiós nonino (vivo)"

        indices = contain_most_words(self.database, title, 'titulo_min')

        # Check that the function returns the correct indices
        # In this case, rows 0, 3, and 4 should match the most words
        expected_indices = [1, 3, 4]

        self.assertEqual(indices, expected_indices)

if __name__ == '__main__':
    unittest.main()
