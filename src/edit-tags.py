import pandas as pd
import config.config as cfg
import os
import wave
from tinytag import TinyTag
import mutagen
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.wavpack import WavPack
from mutagen.aiff import AIFF

def load_tags(file_path):
    """Load tags from an audio file based on its format."""
    extension = os.path.splitext(file_path)[-1].lower()
    
    if extension == '.flac':
        return load_flac_tags(file_path)
    elif extension == '.m4a':
        return load_m4a_tags(file_path)
    elif extension == '.mp3':
        return load_mp3_tags(file_path)
    elif extension == '.wav':
        return load_wav_tags(file_path)
    elif extension == '.aif' or extension == '.aiff':
        return load_aiff_tags(file_path)
    else:
        raise ValueError(f"Unsupported file format: {extension}")

def load_flac_tags(file_path):
    """Load tags from a FLAC file."""
    audio = FLAC(file_path)
    return dict(audio)

def load_m4a_tags(file_path):
    """Load tags from an M4A file."""
    audio = MP4(file_path)
    tags = {}
    for key, value in audio.tags.items():
        if key.startswith("----"):
            # Handle custom tags
            tags[key] = value[0].decode('utf-8') if isinstance(value[0], mutagen.mp4.MP4FreeForm) else value
        else:
            tags[key] = value
    return tags

def load_mp3_tags(file_path):
    """Load tags from an MP3 file."""
    audio = MP3(file_path)
    tags = {}
    for key, value in audio.tags.items():
        tags[key] = value.text if hasattr(value, 'text') else value
    return tags

def load_wav_tags(file_path):
    """Load tags from a WAV file."""
    audio =  wave.open(file_path, 'rb')
    tags = {}
    for key, value in audio.tags.items():
        tags[key] = value.text if hasattr(value, 'text') else value
    return tags

def load_aiff_tags(file_path):
    """Load tags from an AIFF file."""
    audio = AIFF(file_path)
    tags = {}
    for key, value in audio.tags.items():
        tags[key] = value.text if hasattr(value, 'text') else value
    return tags

def process_audio_files(directory):
    """Process all audio files in the given directory and load their tags."""
    audio_tags = {}
    
    for root, _, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                tags = load_tags(file_path)
                audio_tags[file_name] = tags
            except ValueError as e:
                print(f"Skipping unsupported file: {file_name}, error: {e}")
            except Exception as e:
                print(f"Error processing file: {file_name}, error: {e}")
    
    return audio_tags

def load_db():
    """
    Load the CSV file into a pandas DataFrame.

    Returns:
    - pd.DataFrame: A DataFrame containing the data from the CSV file.
    """
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(cfg.DB_CSV_PATH, sep=';', encoding='utf-8')

    # Display the first few rows to verify it loaded correctly
    print(df.head())

    # Search by 'titulo'
    search_title = "Japonesita"
    result = df[df['titulo'].str.contains(search_title, case=False, na=False)]

    # Display the search results
    print(result)

    return df



# def load_audio_metadata(directory):
#     audio_metadata = []

#     # Traverse the directory and its subdirectories
#     for root, dirs, files in os.walk(directory):
#         for file in files:
#             try_append_metadata(audio_metadata, root, file)

#     # Convert the list of metadata to a pandas DataFrame
#     df = pd.DataFrame(audio_metadata)

#     return df

# def try_append_metadata(audio_metadata, root, file):
#     if file.endswith(('.mp3', '.m4a', '.wav', '.flac', '.aif')):
#         file_path = os.path.join(root, file)

#         # Load the file using mutagen
#         audio_file = TinyTag.get(file_path)

#         if audio_file:
#             # Extract metadata
#             metadata = {
#                         'file_path': file_path,
#                         'file': file,
#                         'title': audio_file.tags.get('TITLE', 'Unknown') if audio_file.tags else 'Unknown',
#                         'artist': audio_file.tags.get('ARTIST', 'Unknown') if audio_file.tags else 'Unknown',
#                         'album': audio_file.tags.get('ALBUMARTIST', 'Unknown') if audio_file.tags else 'Unknown',
#                         'genre': audio_file.tags.get('GENRE', 'Unknown') if audio_file.tags else 'Unknown',
#                         'composer': audio_file.tags.get('Composer', 'Unknown') if audio_file.tags else 'Unknown',
#                         'year': audio_file.tags.get('RECYEAR', 'Unknown') if audio_file.tags else 'Unknown',
#                         'date': audio_file.tags.get('Date', 'Unknown') if audio_file.tags else 'Unknown',
#                         'perfomer': audio_file.tags.get('PERFORMER', 'Unknown') if audio_file.tags else 'Unknown',
                        
#                         'duration': audio_file.info.length if audio_file.info else 'Unknown',
#                         'bitrate': audio_file.info.bitrate if hasattr(audio_file.info, 'bitrate') else 'Unknown',
#                         'sample_rate': audio_file.info.sample_rate if hasattr(audio_file.info, 'sample_rate') else 'Unknown',
#                     }

#             # Add metadata to the list
#             audio_metadata.append(metadata)



# Example usage
directory = cfg.TEST_FILES_FOLDER
# metadata_df = load_audio_metadata(directory)
# print(metadata_df)
tags = process_audio_files(directory)
print(tags)
