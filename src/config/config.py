import os
import configparser
import tkinter as tk


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Path to the configuration file
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# Initialize the configparser
config = configparser.ConfigParser()

# Read the config file
config.read(CONFIG_FILE)

# Function to get the appropriate music path
def get_music_path():
    # Get current computer name or user name
    user_name = os.getenv('USERNAME', 'default')

    # Try to get the path defined under UserPaths for the current user
    music_path = config.get('UserPaths', user_name, fallback=None)

    # If no user-specific path is found, use the generic one
    if not music_path:
        music_path = config.get('Paths', 'music_path', fallback=None)

    if not music_path:
        raise ValueError("Music path not set in the config file. Please update the config.ini.")

    return music_path

# General paths and variables
MUSIC_PATH = get_music_path()
RESOURCES_PATH = os.path.join(PROJECT_ROOT, 'resources')

ICON_FOLDER = os.path.join(RESOURCES_PATH, 'icons')
IMAGE_FOLDER = os.path.join(RESOURCES_PATH, 'images')
FONTS_FOLDER = os.path.join(RESOURCES_PATH, 'fonts')

DATA_FOLDER = os.path.join(PROJECT_ROOT, 'data')
TEST_FILES_FOLDER = os.path.join(PROJECT_ROOT, 'tests', 'music_files')

OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, 'output')

# Add other common variables or constants here
DB_CSV_PATH = os.path.join(DATA_FOLDER, 'db.csv')


# def load_resources():
#     # Load Icons
#     icons = {
#         'archivo': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'album.png')),
#         'directorio': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'album-list.png')),
#         'correr': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'search-window.png')),
#         'play': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'play_resize.png')),
#         'stop': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'pause_resize.png')),
#         'transfer': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'transfer.png')),
#         'info': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'info-circle_resize.png')),
#         'trash': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'trash.png')),
#         'searchdb': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'searchdb.png')),
#         'presentacion': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'presentation.png')),
#         'playlist': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'playlist.png')),
#         'convert_playlist': tk.PhotoImage(file=os.path.join(ICON_FOLDER, 'convert_playlist.png'))
#     } 

#     # Load Images
#     images = {
#         'background': tk.PhotoImage(file=os.path.join(IMAGE_FOLDER, 'background_tango.png'))
#         # Add more images if needed
#     }

#     return icons, images

def load_resources_paths():
    # Load Icons
    icons = {
        'archivo': os.path.join(ICON_FOLDER, 'album.png'),
        'directorio': os.path.join(ICON_FOLDER, 'album-list.png'),
        'correr': os.path.join(ICON_FOLDER, 'search-window.png'),
        'play': os.path.join(ICON_FOLDER, 'play_resize.png'),
        'stop': os.path.join(ICON_FOLDER, 'pause_resize.png'),
        'transfer': os.path.join(ICON_FOLDER, 'transfer.png'),
        'info': os.path.join(ICON_FOLDER, 'info-circle_resize.png'),
        'trash': os.path.join(ICON_FOLDER, 'trash.png'),
        'searchdb': os.path.join(ICON_FOLDER, 'searchdb.png'),
        'presentacion': os.path.join(ICON_FOLDER, 'presentation.png'),
        'playlist': os.path.join(ICON_FOLDER, 'playlist.png'),
        'convert_playlist': os.path.join(ICON_FOLDER, 'convert_playlist.png')
    } 

    # Load Images
    images = {
        'background': os.path.join(IMAGE_FOLDER, 'background_tango.png')
        # Add more images if needed
    }

    return icons, images

