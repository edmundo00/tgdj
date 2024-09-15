import pandas as pd
from tinytag import TinyTag
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import os


def update_tags(file_path, title=None, artist=None, year=None, genre=None, composer=None):
    # Get the file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    try:
        if ext == '.mp3':
            # Load the MP3 file
            audio = MP3(file_path, ID3=EasyID3)
        elif ext == '.flac':
            # Load the FLAC file
            audio = FLAC(file_path)
        elif ext == '.m4a':
            # Load the M4A file
            audio = MP4(file_path)
        else:
            print(f"Unsupported file format: {ext}")
            return

        # Update tags
        if title:
            if ext == '.m4a':
                audio['\xa9nam'] = title  # Tag for title in M4A files
            else:
                audio['title'] = title

        if artist:
            audio['artist'] = artist

        if year:
            audio['date'] = year

        if genre:
            audio['genre'] = genre

        if composer:
            if ext == '.m4a':
                audio['\xa9wrt'] = composer  # Tag for composer in M4A files
            else:
                audio['composer'] = composer

        # Save the updated tags
        audio.save()
        print(f"Updated tags for: {file_path}")

    except Exception as e:
        print(f"Error updating tags for {file_path}: {e}")


# Path to the CSV file
csv_path = r"E:\Dropbox\MUSICA\MP3\TANGO\other_stuff\PYTHON\tgdj\output\residuos.csv"

# Read the CSV file with UTF-8-BOM encoding and semicolon delimiter
try:
    df = pd.read_csv(csv_path, delimiter=';', encoding='utf-8-sig', on_bad_lines='skip')
except pd.errors.ParserError as e:
    print(f"Error reading CSV: {e}")
    exit(1)

# Initialize lists to store the data
original_titles = []
strings_to_remove = []
final_titles = []

# Iterate over each row in the dataframe
for index, row in df.iterrows():
    file_path = row.iloc[3]  # Full path of the music file
    string_to_remove = row.iloc[2]  # String to be removed from the title

    # Check if file_path is valid and the file exists
    if isinstance(file_path, str) and os.path.isfile(file_path):
        try:
            # Load the music file using TinyTag to read the title
            tag = TinyTag.get(file_path)
            original_title = tag.title  # Get the title
            print(original_title)

            if original_title and string_to_remove and original_title.endswith(string_to_remove):
                # Remove the specified string from the end of the title
                final_title = original_title[: -len(string_to_remove)]
            else:
                final_title = original_title  # No change if the string is not at the end

            # Append data to the lists
            original_titles.append(original_title)
            strings_to_remove.append(string_to_remove)
            final_titles.append(final_title)

        except Exception as e:
            # Handle errors from TinyTag
            print(f"Error processing file {file_path}: {e}")
            original_titles.append(None)
            strings_to_remove.append(string_to_remove)
            final_titles.append(None)
    else:
        # Handle missing or invalid file paths
        original_titles.append(None)
        strings_to_remove.append(None)
        final_titles.append(None)

# Create a DataFrame to display the results
result_df = pd.DataFrame({
    'Original Title': original_titles,
    'String to Remove': strings_to_remove,
    'Final Title': final_titles
})

# Display the DataFrame
print(result_df)

# Optionally, save the results to an Excel file for easier review
result_df.to_excel('music_titles_review.xlsx', index=False)
print("Results saved to 'music_titles_review.xlsx'.")

# After reviewing the changes, proceed with updating the titles
update_titles = input("Do you want to update the titles in the music files? (yes/no): ").strip().lower()

if update_titles == 'yes':
    for index, row in df.iterrows():
        file_path = row.iloc[3]
        final_title = final_titles[index]  # Use the updated title from the list

        if isinstance(file_path, str) and os.path.isfile(file_path) and final_title:
            # Update the tags using Mutagen
            update_tags(file_path, title=final_title)

    print("Titles have been updated successfully.")
else:
    print("No changes were made to the titles.")
