import tkinter as tk
from tkinter import filedialog
import config.config as cfg
import os



def load_resources():
    resources_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources')

    # Load Icons
    icons_path = os.path.join(resources_path, 'icons')
    icons = {
        'archivo': tk.PhotoImage(file=os.path.join(icons_path, 'album.png')),
        'directorio': tk.PhotoImage(file=os.path.join(icons_path, 'album-list.png')),
        'correr': tk.PhotoImage(file=os.path.join(icons_path, 'search-window.png')),
        'play': tk.PhotoImage(file=os.path.join(icons_path, 'play_resize.png')),
        'stop': tk.PhotoImage(file=os.path.join(icons_path, 'pause_resize.png')),
        'transfer': tk.PhotoImage(file=os.path.join(icons_path, 'transfer.png')),
        'info': tk.PhotoImage(file=os.path.join(icons_path, 'info-circle_resize.png')),
        'trash': tk.PhotoImage(file=os.path.join(icons_path, 'trash.png')),
        'searchdb': tk.PhotoImage(file=os.path.join(icons_path, 'searchdb.png')),
        'presentacion': tk.PhotoImage(file=os.path.join(icons_path, 'presentation.png')),
        'playlist': tk.PhotoImage(file=os.path.join(icons_path, 'playlist.png')),
        'convert_playlist': tk.PhotoImage(file=os.path.join(icons_path, 'convert_playlist.png'))
    } 

    # Load Images
    images_path = os.path.join(resources_path, 'images')
    images = {
        #'background': tk.PhotoImage(file=os.path.join(images_path, 'background.png'))
        # Add more images if needed
    }

    return icons, images

class MainWindow:
    def __init__(self, root, icons, images):
        self.root = root
        self.icons = icons
        self.images = images

        # Create the main window
        self.root.title("Tkinter Window with Menu, Icon, and Status Bar")
        self.root.state('zoomed')

        # Create a menu bar
        self.menubar = tk.Menu(root)
        self.root.config(menu=self.menubar)

        # Create a 'File' menu and add it to the menu bar
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New")
        self.file_menu.add_command(label="Open")
        self.file_menu.add_command(label="Save")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)

        # Create an 'Edit' menu and add it to the menu bar
        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Undo")
        self.edit_menu.add_command(label="Redo")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut")
        self.edit_menu.add_command(label="Copy")
        self.edit_menu.add_command(label="Paste")

        # Create an icon bar
        self.icon_bar = tk.Frame(root, relief=tk.RAISED, bd=2)
        self.icon_bar.grid(row=0, column=0, columnspan=3, sticky="ew")

        # Add buttons with icons to the icon bar
        self.load_button_music_file = tk.Button(self.icon_bar, image=self.icons['archivo'], relief=tk.FLAT,
                                                command=self.load_music_file)
        self.load_button_music_file.grid(row=0, column=0, padx=2, pady=2)

        self.load_button_music_folder = tk.Button(self.icon_bar, image=self.icons['directorio'], relief=tk.FLAT,
                                                  command=self.load_music_folder)
        self.load_button_music_folder.grid(row=0, column=1, padx=2, pady=2)

        self.save_button = tk.Button(self.icon_bar, image=self.icons['correr'], relief=tk.FLAT)
        self.save_button.grid(row=0, column=2, padx=2, pady=2)

        self.transfer_button = tk.Button(self.icon_bar, image=self.icons['transfer'], relief=tk.FLAT,
                                         command=self.apply_tags)
        self.transfer_button.grid(row=0, column=3, padx=2, pady=2)

        self.trash_button = tk.Button(self.icon_bar, image=self.icons['trash'], relief=tk.FLAT, command=self.clear_all)
        self.trash_button.grid(row=0, column=4, padx=2, pady=2)

        self.search_button = tk.Button(self.icon_bar, image=self.icons['searchdb'], relief=tk.FLAT, command=self.search_db)
        self.search_button.grid(row=0, column=5, padx=2, pady=2)

        self.presentation_button = tk.Button(self.icon_bar, image=self.icons['presentacion'], relief=tk.FLAT,
                                             command=self.open_presentation_popup)
        self.presentation_button.grid(row=0, column=6, padx=2, pady=2)

        self.playlist_button = tk.Button(self.icon_bar, image=self.icons['playlist'], relief=tk.FLAT,
                                         command=self.open_playlist)
        self.playlist_button.grid(row=0, column=7, padx=2, pady=2)

        self.convert_playlist_button = tk.Button(self.icon_bar, image=self.icons['convert_playlist'], relief=tk.FLAT,
                                                 command=self.convert_playlist)
        self.convert_playlist_button.grid(row=0, column=8, padx=2, pady=2)

        # Create a main content area
        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # Create a canvas widget
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Add a vertical scrollbar to the canvas
        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Configure the canvas to use the scrollbar
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Create a frame inside the canvas to hold the main content
        self.main_content = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.main_content, anchor="nw")

        # Bind the canvas to update its scroll region whenever the main_content frame changes size
        self.main_content.bind("<Configure>", self.on_frame_configure)

        # Make the canvas expandable
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Bind mousewheel scrolling to the canvas
        self.root.bind_all("<MouseWheel>", self._on_mouse_wheel)

        # Create the first subframe
        self.subframe1 = tk.Frame(self.main_content, bg='white', bd=1, relief="ridge")
        self.subframe1.grid(row=0, column=0, sticky="nsew")

        # Create the second subframe
        self.subframe2 = tk.Frame(self.main_content, bg='white', bd=1, relief="ridge")
        self.subframe2.grid(row=0, column=1, sticky="nsew")

        # Configure grid weights to ensure subframes take up half of the main frame
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(1, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)

        # Create a status bar
        self.status_bar = tk.Label(root, text="Status: Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, columnspan=3, sticky="ew")

        # Configure grid weights to make the main content expandable
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

    def on_frame_configure(self, event):
        # Update the scroll region of the canvas
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mouse_wheel(self, event):
        # Scroll the canvas vertically
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_music_file(self):
        # Function to load a music file
        pass

    def load_music_folder(self):
        # Function to load a music folder
        pass

    def apply_tags(self):
        # Function to apply tags
        pass

    def clear_all(self):
        # Function to clear all inputs
        pass

    def search_db(self):
        # Function to search the database
        pass

    def open_presentation_popup(self):
        # Function to open a presentation popup
        pass

    def open_playlist(self):
        # Function to open a playlist
        pass

    def convert_playlist(self):
        # Function to convert a playlist
        pass