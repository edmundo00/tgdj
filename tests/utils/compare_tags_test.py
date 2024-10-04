import unittest
import pandas as pd
from src.utils.utils import compare_tags, TagLabels

class Tag:
    def __init__(self, artist, title, year, genre, composer, _file_name):
        self.artist = artist
        self.title = title
        self.year = year
        self.genre = genre
        self.composer = composer
        self._file_name = _file_name

    def __repr__(self):
        return (f"Tag(artist={self.artist}, title={self.title}, year={self.year}, "
                f"genre={self.genre}, composer={self.composer}, _file_name={self._file_name})")



class CompareTagsTest(unittest.TestCase):
    
    def setUp(self):
        # Set up a simple DataFrame for testing
        self.database = pd.DataFrame({
            'titulo': ['Pasional', 'La Cumparsita', 'El Choclo'],
            'titulo_min': ['pasional', 'la cumparsita', 'el choclo'],
            'artista': ["Osvaldo Pugliese", "Carlos Gardel", "Astor Piazzolla"],
            'artista_min': ["osvaldo pugliese", "carlos gardel", "astor piazzolla"],
            'cantor': ["Alberto Morán", None, None],
            'cantor_min': ["alberto moran", None, None],
            'fecha': ["1951", "1928", "1962"],
            'fecha_ano': ["1951", "1928", "1962"],
            'estilo': ["Tango", "Tango", "Nuevo Tango"],
            'compositor_autor': ["Manuel Romero", "Gerardo Matos Rodríguez", "Ángel Villoldo"]
        })

    def test_compare_tags_exact_match(self):
        # import pdb; pdb.set_trace()  # Debugger will start here

        # Create a tag object with attributes matching the first row in the DataFrame
        tag = Tag(
            artist="Osvaldo Pugliese feat. Alberto Morán",
            title="Pasional",
            year="1951",
            genre="Tango",
            composer="Manuel Romero",
            _file_name="dummy.flac"
        )

        # Call compare_tags and check the results
        results = compare_tags(self.database, tag)
        
        # Assert that the title matches
        self.assertTrue(results[TagLabels.TITULO].any())
        self.assertTrue(results[TagLabels.TITULO_EXACTO].any())

        # Assert that the artist matches
        self.assertTrue(results[TagLabels.ARTISTA].any())
        # self.assertTrue(results[TagLabels.ARTISTA_EXACTO].any())

        # Assert that the cantor matches
        self.assertTrue(results[TagLabels.CANTOR].any())
        self.assertTrue(results[TagLabels.CANTOR_EXACTO].any())

        # Assert that the year matches
        self.assertTrue(results[TagLabels.FECHA].any())
        self.assertTrue(results[TagLabels.ANO].any())

        # Assert that the genre matches
        self.assertTrue(results[TagLabels.GENERO].any())

        # Assert that the composer matches
        self.assertTrue(results[TagLabels.COMPOSITOR_AUTOR].any())

        # Assert that everything matches
        self.assertTrue(results[TagLabels.TODO].any())

    def test_compare_tags_no_match(self):        
        tag = Tag(
            artist="Unknown Artist",
            title="Unknown Title",
            year="1900",
            genre="Unknown Genre",
            composer="Unknown Composer",
            _file_name="dummy.flac"
        )

        # Call compare_tags and check the results
        results = compare_tags(self.database, tag)
        
        # Assert that there are no matches
        for key, value in results.items():
            if isinstance(value, pd.Series) or isinstance(value, list):
                self.assertFalse(any(value))
            else:
                self.assertFalse(value)

    def test_compare_tags_partial_match(self):
        tag = Tag(
            artist="Carlos Gardel",
            title="La Cumparsita",
            year=None,  # No year provided
            genre="Tango",
            composer=None,
            _file_name="dummy.flac"
        )

        # Call compare_tags and check the results
        results = compare_tags(self.database, tag)

        # Assert partial matches
        self.assertTrue(results[TagLabels.TITULO].any())
        self.assertTrue(results[TagLabels.ARTISTA].any())
        self.assertTrue(results[TagLabels.GENERO].any())

        # Assert missing fields do not match
        self.assertFalse(results[TagLabels.CANTOR])
        self.assertFalse(results[TagLabels.COMPOSITOR_AUTOR].any())

    # Add more test cases as needed

if __name__ == '__main__':
    unittest.main()
