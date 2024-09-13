import tkinter as tk
from tkinter import filedialog, messagebox
from src.config.config import musicbee_start_folder, musicbee_tags
import pandas as pd  # Import Pandas for DataFrame management


class MusicBeeLibraryTools:
    def __init__(self, root, file_path=None):
        """
        Initializes the MusicBeeLibraryTools class.

        :param root: The root Tkinter window for displaying GUI components.
        :param file_path: Optional path to the MusicBee library file. If provided, the library is parsed immediately.
        """
        self.root = root  # Store the root Tkinter window
        self.file_path = file_path  # Optional file path for the MusicBee library
        self.library_df = pd.DataFrame()  # Initialize the library DataFrame

        # If a file path is provided during initialization, parse the library
        if file_path:
            self.parse_library()

    def decode_from_7bit(self, data):
        """
        Decodes a 7-bit encoded integer from a list of bytes.

        :param data: List of bytes containing the 7-bit encoded integer.
        :return: Decoded integer value.
        """
        result = 0  # Initialize result to 0
        for index, char in enumerate(data):
            # Extract 7 bits from each byte and shift them into the result
            result |= (char & 0x7f) << (7 * index)
            # Stop if the high bit is not set (indicating end of this number)
            if char & 0x80 == 0:
                break
        return result

    def read_int(self, bytes_):
        """
        Reads a signed integer from bytes using little-endian byte order.

        :param bytes_: Bytes to convert to an integer.
        :return: Signed integer value.
        """
        return int.from_bytes(bytes_, byteorder="little", signed=True)

    def read_uint(self, bytes_):
        """
        Reads an unsigned integer from bytes using little-endian byte order.

        :param bytes_: Bytes to convert to an unsigned integer.
        :return: Unsigned integer value.
        """
        return int.from_bytes(bytes_, byteorder="little")

    def read_str(self, file):
        """
        Reads a length-prefixed string from a binary file.

        :param file: Open file object to read from.
        :return: Decoded string.
        """
        len_1 = file.read(1)  # Read the first byte for the length
        # Check if the length byte indicates a 7-bit encoding
        if self.read_uint(len_1) > 0x7F:
            len_2 = file.read(1)  # Read the second byte
            # If the second byte is also 7-bit encoded, continue reading
            if self.read_uint(len_2) > 0x7F:
                length = self.decode_from_7bit([
                    self.read_uint(len_1),
                    self.read_uint(len_2),
                    self.read_uint(file.read(1))
                ])
            else:
                # Otherwise, use the first two bytes to determine the length
                length = self.decode_from_7bit([self.read_uint(len_1), self.read_uint(len_2)])
        else:
            # For a single byte length, use it directly
            length = self.read_uint(len_1)
        # If length is zero, return an empty string
        if length == 0:
            return ""
        # Read the string of the determined length and decode it from UTF-8
        return file.read(length).decode("utf-8")

    def parse_library(self):
        """
        Parses the MusicBee library file to extract metadata about each media item.

        Populates self.library_df with a DataFrame containing metadata for each media file.
        """
        if not self.file_path:
            return  # Exit if no file path is set

        records = []  # List to collect each media record as a dictionary

        with open(self.file_path, "rb") as mbl:  # Open the file in binary read mode
            count = self.read_int(mbl.read(4))  # Read the first 4 bytes as the file count

            # Validate the file format by checking the first byte
            if not count & 0xFF:
                raise ValueError("Invalid file format")

            count = count >> 8  # Adjust count by shifting right 8 bits

            while True:  # Start reading media entries
                media = {"file_designation": self.read_uint(mbl.read(1))}  # Read the file designation
                # If the designation is 1, it indicates the end of entries
                if media["file_designation"] == 1:
                    break

                # Process media files if designation is between 2 and 9
                if 10 > media["file_designation"] > 1:
                    media["status"] = self.read_uint(mbl.read(1))  # Read status byte
                    if media["status"] > 6:
                        raise ValueError("Invalid status value")  # Validate the status value

                    # Read various metadata fields for the media entry
                    media["play_count"] = self.read_uint(mbl.read(2))
                    media["date_last_played"] = self.read_int(mbl.read(8))
                    media["skip_count"] = self.read_uint(mbl.read(2))
                    media["file_path"] = self.read_str(mbl)  # Read and decode the file path

                    # Ensure the file path is valid
                    if media["file_path"] == "":
                        raise ValueError("Empty file path found")

                    # Read additional metadata fields
                    media["file_size"] = self.read_int(mbl.read(4))
                    media["sample_rate"] = self.read_int(mbl.read(4))
                    media["channel_mode"] = self.read_uint(mbl.read(1))
                    media["bitrate_type"] = self.read_uint(mbl.read(1))
                    media["bitrate"] = self.read_int(mbl.read(2))
                    media["track_length"] = self.read_int(mbl.read(4))
                    media["date_added"] = self.read_int(mbl.read(8))
                    media["date_modified"] = self.read_int(mbl.read(8))

                    # Process tags associated with the media
                    media["tags"] = {}
                    while True:
                        tag_code = self.read_uint(mbl.read(1))  # Read tag code
                        # If tag code is 0, end of tags
                        if tag_code == 0:
                            break
                        # Read and store tag value associated with the tag code
                        media["tags"][str(tag_code)] = self.read_str(mbl)

                    # Map tag codes to descriptive names using musicbee_tags
                    for tag_name, tag_code in musicbee_tags.items():
                        media[tag_name] = media["tags"].get(tag_code, "")

                    # Append the processed media entry to records
                    records.append(media)
                else:
                    raise ValueError("Unexpected file designation")  # Handle invalid designations

        # Convert records to a DataFrame
        self.library_df = pd.DataFrame.from_records(records)

    def get_files_by_artist(self, artist_name):
        """
        Returns a list of file paths where the artist's name matches the specified artist_name.

        :param artist_name: The name of the artist to search for.
        :return: List of file paths matching the artist name.
        """
        artist_column = musicbee_tags['artist']  # Use the artist tag code from the config
        if artist_column in self.library_df.columns:  # Check if artist column exists
            # Filter rows where the artist column contains the artist name (case-insensitive)
            return self.library_df[self.library_df[artist_column].str.contains(artist_name, case=False, na=False)][
                'file_path'].tolist()
        else:
            return []

    def open_musicbee_library(self):
        """
        Opens a file dialog to select the MusicBee library file and loads it.

        Displays success or error messages based on the outcome.
        """
        # Open a file dialog starting from the configured start folder
        file_path = filedialog.askopenfilename(
            title="Select MusicBee Library File",
            filetypes=[("MusicBee Library Files", "*.mbl"), ("All Files", "*.*")],
            initialdir=musicbee_start_folder
        )
        if file_path:
            try:
                # Initialize the MusicBeeLibraryTools with the selected file
                self.file_path = file_path
                self.parse_library()
                messagebox.showinfo("Success", "Library loaded successfully!")

                # After loading, show a popup to search for artist
                self.show_artist_search_popup()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load library: {e}")

    def show_artist_search_popup(self):
        """
        Show a popup with an entry to search files by artist.
        """
        if self.library_df.empty:
            messagebox.showwarning("Warning", "Please load a library first.")
            return

        # Create the popup window
        popup = tk.Toplevel(self.root)
        popup.title("Search by Artist")
        popup.geometry("400x200")

        # Label and entry for artist name
        artist_label = tk.Label(popup, text="Enter Artist Name:")
        artist_label.pack(pady=10)

        artist_entry = tk.Entry(popup)
        artist_entry.pack(pady=5, fill=tk.X, padx=10)

        # Button to trigger the search
        search_button = tk.Button(popup, text="Search", command=lambda: self.show_files_by_artist(artist_entry.get()))
        search_button.pack(pady=10)

    def show_files_by_artist(self, artist_name):
        """
        Display a popup with a list of files by the selected artist.
        """
        if self.library_df.empty:
            messagebox.showwarning("Warning", "Please load a library first.")
            return

        files = self.get_files_by_artist(artist_name)

        # Create a new popup window
        result_popup = tk.Toplevel(self.root)
        result_popup.title(f"Files by {artist_name}")
        result_popup.geometry("400x300")

        # Add a Listbox to show the file paths
        listbox = tk.Listbox(result_popup)
        listbox.pack(fill="both", expand=True)

        # Populate the Listbox with file paths
        for file_path in files:
            listbox.insert(tk.END, file_path)

        # If no files found, show a message
        if not files:
            messagebox.showinfo("Info", f"No files found for artist '{artist_name}'.")

