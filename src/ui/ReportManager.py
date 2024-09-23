import pandas as pd


class ReportManager:
    def __init__(self):
        """
        Initialize the class with an empty list to collect report rows.
        """
        self.report_data = []  # List to hold dictionaries (rows of data)

    def add_row(self, row_data):
        """
        Add a row (as a dictionary) to the report.

        :param row_data: dict
            A dictionary where keys are column names and values are the row values.
        """
        self.report_data.append(row_data)  # Add the row to the list

    def finalize_report(self):
        """
        Convert the list of dictionaries to a pandas DataFrame and set 'file_path' as the index.
        """
        if self.report_data:
            self.report_df = pd.DataFrame(self.report_data)
            if 'file_path' in self.report_df.columns:
                self.report_df.set_index('file_path', inplace=True, drop=False)
            else:
                print("Error: 'file_path' column not found.")
        else:
            self.report_df = pd.DataFrame()  # Handle the case where no data was added
            print("No data to finalize.")

    def save_report(self, file_path):
        """
        Save the report DataFrame to a CSV file.

        :param file_path: str
            Path to save the report CSV.
        """
        if hasattr(self, 'report_df') and not self.report_df.empty:
            self.report_df.to_csv(file_path, index=False)
            print(f"Report saved to {file_path}")
        else:
            print("Error: No data to save.")

    def load_report(self, file_path):
        """
        Load an existing report from a CSV file into the DataFrame.

        :param file_path: str
            Path to the report CSV file to load.
        """
        try:
            self.report_df = pd.read_csv(file_path).fillna("")
            print(f"Report loaded from {file_path}")
        except Exception as e:
            print(f"Error loading report: {e}")

    def filter_report(self, column_name, condition):
        """
        Filter the DataFrame based on a condition.

        :param column_name: str
            The name of the column to filter on.
        :param condition: callable
            A function to apply as a filter condition.
        :return: pd.DataFrame
            Filtered DataFrame.
        """
        filtered_df = self.report_df[self.report_df[column_name].apply(condition)]
        return filtered_df

    def generate_file_report(self, file_path, artist, title, year, genre, composer):
        """
        Generate a row report for a file based on provided data.

        :param file_path: str
            Path to the file to analyze.
        :param artist: str
            Artist name.
        :param title: str
            Title of the file.
        :param year: str
            Year of the song.
        :param genre: str
            Genre of the song.
        :param composer: str
            Composer of the song.
        :return: dict
            Dictionary with tag information for reporting.
        """
        return {
            'file_path': file_path,
            'title': title,
            'artist': artist,
            'year': year,
            'genre': genre,
            'composer': composer,
            "Artista encontrado": False,  # Default values based on your logic
            "Titulo encontrado": False,
            "Numero de coincidencias": 0,
            "Hay coincidencia preferida": False,
            "No hay coincidencia preferida": False,
            "Coincidencia perfecta": False
        }

    def update_tags_in_report(self, update_dict):
        """
        Update rows in the report based on new tag data.

        :param update_dict: dict
            Dictionary where keys are file paths and values are dictionaries of tag updates.
        """
        for file_path, new_tags in update_dict.items():
            self.report_df.loc[self.report_df['file_path'] == file_path, list(new_tags.keys())] = list(
                new_tags.values())

    def summarize(self):
        """
        Print a summary of the report.
        """
        if hasattr(self, 'report_df') and not self.report_df.empty:
            print(f"Report Summary: {len(self.report_df)} entries.")
            print(self.report_df.head())
        else:
            print("No data to summarize.")
