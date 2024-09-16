from fuzzywuzzy import fuzz, process
import pandas as pd
import re

# Diccionario para convertir números escritos en español a dígitos
NUMBERS_MAP = {
    'cero': '0', 'uno': '1', 'dos': '2', 'tres': '3', 'cuatro': '4',
    'cinco': '5', 'seis': '6', 'siete': '7', 'ocho': '8', 'nueve': '9',
    'diez': '10', 'once': '11', 'doce': '12', 'trece': '13', 'catorce': '14', 'quince': '15',
    'dieciséis': '16', 'diecisiete': '17', 'dieciocho': '18', 'diecinueve': '19',
    'veinte': '20', 'treinta': '30', 'cuarenta': '40', 'cincuenta': '50',
    'sesenta': '60', 'setenta': '70', 'ochenta': '80', 'noventa': '90',
    'cien': '100', 'ciento': '100', 'doscientos': '200', 'trescientos': '300',
    'cuatrocientos': '400', 'quinientos': '500', 'seiscientos': '600',
    'setecientos': '700', 'ochocientos': '800', 'novecientos': '900', 'mil': '1000'
}


def normalize_text(text):
    """
    Normalizes the text by converting to lowercase and replacing numbers written in Spanish with digits.
    """
    text = text.lower()
    # Reemplazar números escritos en español con sus equivalentes en dígitos
    for word, digit in NUMBERS_MAP.items():
        text = re.sub(r'\b' + word + r'\b', digit, text)
    return text


class FuzzyMatcher:
    def __init__(self, dataframe, column):
        """
        Initializes the FuzzyMatcher with a DataFrame and the column to be used for fuzzy matching.

        :param dataframe: A pandas DataFrame containing the data.
        :param column: The column name (string) where the fuzzy matching will be performed.
        """
        self.dataframe = dataframe
        self.column = column

        if column not in dataframe.columns:
            raise ValueError(f"Column '{column}' does not exist in the DataFrame")

    def exact_match(self, query):
        """
        Finds exact matches for the query in the specified column.

        :param query: The string to search for exact matches.
        :return: A DataFrame with exact matches.
        """
        matches = self.dataframe[self.dataframe[self.column] == query]
        return matches

    def fuzzy_match(self, query, limit=5, scorer=fuzz.ratio, threshold=80):
        """
        Finds fuzzy matches for the query in the specified column using fuzzywuzzy.

        :param query: The string to search for fuzzy matches.
        :param limit: The maximum number of results to return.
        :param scorer: The fuzzy matching scorer function from fuzzywuzzy.
        :param threshold: The minimum similarity score to consider a match.
        :return: A DataFrame with fuzzy matches that meet the threshold.
        """
        # Extract matches with their scores
        matches = process.extract(query, self.dataframe[self.column].tolist(), limit=limit, scorer=scorer)

        # Filter matches based on the threshold
        filtered_matches = [(match, score) for match, score in matches if score >= threshold]

        # Extract indices of the matched rows
        matched_indices = [self.dataframe[self.dataframe[self.column] == match].index[0] for match, score in
                           filtered_matches]

        # Return the matching rows as a DataFrame
        return self.dataframe.loc[matched_indices]

    def best_match(self, query, scorer=fuzz.ratio):
        """
        Finds the best fuzzy match for the query in the specified column.

        :param query: The string to search for the best fuzzy match.
        :param scorer: The fuzzy matching scorer function from fuzzywuzzy.
        :return: A tuple containing the best match string and its similarity score.
        """
        best_match = process.extractOne(query, self.dataframe[self.column].tolist(), scorer=scorer)
        return best_match

    def partial_match(self, query, threshold=80):
        """
        Finds partial matches for the query in the specified column.

        :param query: The string to search for partial matches.
        :param threshold: The minimum similarity score to consider a partial match.
        :return: A DataFrame with partial matches that meet the threshold.
        """
        return self.fuzzy_match(query, scorer=fuzz.partial_ratio, threshold=threshold)

    def compare_titles_and_save(self, file_path):
        """
        Reads a CSV file, compares the "old title" and "new title" columns using various matching techniques,
        and writes the results back as new columns in the same file.

        :param file_path: The path to the CSV file.
        """
        # Read the CSV file with UTF-8 encoding and ';' as the separator
        df = pd.read_csv(file_path, encoding='utf-8', sep=';')

        # Check if required columns exist
        if 'old_title' not in df.columns or 'new_title' not in df.columns:
            raise ValueError("The CSV file must contain 'old title' and 'new title' columns")

        # Initialize lists to store match scores
        exact_matches = []
        partial_matches = []
        fuzzy_matches = []

        # Iterate through each row and compare the "old title" and "new title"
        for index, row in df.iterrows():
            # Normalize the titles
            old_title = normalize_text(str(row['old_title']).strip())
            new_title = normalize_text(str(row['new_title']).strip())

            # Exact match (case-insensitive and number normalized)
            exact_match = old_title == new_title
            exact_matches.append(1 if exact_match else 0)

            # Partial match using partial_ratio
            partial_score = fuzz.partial_ratio(old_title, new_title)
            partial_matches.append(partial_score)

            # Fuzzy match using ratio
            fuzzy_score = fuzz.ratio(old_title, new_title)
            fuzzy_matches.append(fuzzy_score)

        # Add the results as new columns in the DataFrame
        df['Exact Match'] = exact_matches
        df['Partial Match Score'] = partial_matches
        df['Fuzzy Match Score'] = fuzzy_matches

        # Write the updated DataFrame back to the same CSV file with UTF-8 encoding and ';' as the separator
        df.to_csv(file_path, index=False, encoding='utf-8', sep=';')

        print(f"Comparison results have been written to {file_path}")


# Usage Example
if __name__ == "__main__":
    # Example DataFrame
    data = {'titulo': ['Hola Mundo', 'Hola', 'Mundo Hola', 'Adiós Mundo', 'Hola Mundo!']}
    df = pd.DataFrame(data)

    # Initialize FuzzyMatcher with the DataFrame and the column to search
    matcher = FuzzyMatcher(df, 'titulo')

    # Perform exact match
    exact_matches = matcher.exact_match('Hola Mundo')
    print("Exact Matches:")
    print(exact_matches)

    # Perform fuzzy match
    fuzzy_matches = matcher.fuzzy_match('Hola Mundo!', threshold=80)
    print("\nFuzzy Matches:")
    print(fuzzy_matches)

    # Perform best match
    best_match = matcher.best_match('Hola Mundo!')
    print("\nBest Match:")
    print(best_match)

    # Perform partial match
    partial_matches = matcher.partial_match('Mundo', threshold=80)
    print("\nPartial Matches:")
    print(partial_matches)

    # Compare titles and save results in the CSV
    file_path = r"E:\Dropbox\MUSICA\MP3\TANGO\other_stuff\PYTHON\tgdj\output\coincidencias_20240916_213058.csv"
    matcher.compare_titles_and_save(file_path)
