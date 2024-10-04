
# TangoTags - Audio Tag Management and Presentation Creator

TangoTags is a Python-based tool designed to manage and edit audio tags for tango music collections. The tool includes features for generating presentations based on playlists and organizing your music library according to specific tag information.

## Features

### 1. **Audio Tag Management**
   - **Read and Edit Audio Tags:** Supports MP3, FLAC, and M4A files, allowing users to update metadata such as title, artist, year, genre, and composer.
   - **Tag Update UI:** Provides a user interface to view and edit tags, with options to save the updated tags back to the files.

### 2. **Playlist Management**
   - **M3U Playlist Converter:** Convert M3U playlists, adjusting file paths based on the computer the files were created on. The tool generates three different versions of the playlist, one for each defined path in the `path_map`.
   - **Playlist Preview:** Display the contents of an M3U playlist in a table, with special highlighting for paths containing "Dropbox".
   
### 3. **Presentation Generation**
   - **Create PowerPoint Presentations:** Automatically generate PowerPoint presentations based on a playlist. The tool allows you to set the background, add titles, and apply a gradient overlay for visual enhancement.
   - **Customizable Tanda Slides:** Create slides with structured information for each tanda (set of songs), including titles, years, and composers.

### 4. **Database Search and Integration**
   - **Search Database:** Filter and search your music database by title, artist, cantor, and date range. The results are displayed in an interactive table.
   - **Cross-Reference Matching:** Automatically match your audio files against a database of known songs, highlighting the best matches based on title, artist, and other tags.

### 5. **User Interface**
   - **Tkinter-based GUI:** A user-friendly graphical interface built with Tkinter, providing easy access to all features.
   - **Dynamic Layout:** The layout dynamically adjusts based on user actions, with support for scrolling and resizing.

## Setup and Installation

1. **Clone the Repository**
   ```
   git clone https://github.com/yourusername/tangotags.git
   cd tangotags
   ```

2. **Install Required Packages**
   ```
   pip install -r requirements.txt
   ```

3. **Run the Application**
   ```
   python tangotags.py
   ```

If you don't have `pip` installed, you can follow the instructions [here](https://pip.pypa.io/en/stable/installation/) to install it.

## Configuration

- **Path Mapping:** The `path_map` dictionary is used to define the file paths for different computers. Update this dictionary according to your environment.

```python
path_map = {
    "WINDOW-COMPUTER": "E:\Dropbox",
    "CAD065": "D:\Dropbox",
    "LAPTOP-ABRSCER9": "C:\Users\diana\Dropbox"
}
```

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.
git fetch -vp
git pull

git add <file_name>
para un archivo

PAra todos los cambios:
git add .

Luego 
git commit -m "Commit message"

Si quieres añadir todos los cambios y commit
git commit -a -m "Commit message"

git push

## License

This project is licensed under the MIT License.

## Contact

For questions or suggestions, feel free to open an issue or contact me at [your-email@example.com].
