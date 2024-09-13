import os
from tkinter import filedialog, messagebox, ttk, Toplevel, Frame
import tkinter as tk
from src.config.config import playlist_path_map
from datetime import datetime

class PlaylistOperations:
    def __init__(self, root, m3u_start_folder, path_map):
        # Initialize the class with the main window, starting path for M3U files, and path mappings
        self.root = root
        self.m3u_start_folder = m3u_start_folder
        self.path_map = path_map
        self.playlist_path_map = playlist_path_map
        self.pad = 5  # Padding used for UI elements

    def merge_playlist(self):
        """
        Allow the user to select and merge multiple M3U playlists, avoiding duplicates.
        """
        file_paths = self._prompt_for_files("Select M3U Playlists to Merge")
        if not file_paths:
            return

        unique_titles = self._extract_unique_titles(file_paths)
        merged_lines = list(unique_titles.values())

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"merge{timestamp}"

        self._show_playlist_in_popup(merged_lines, "merged_playlist.m3u", filename)

    def convert_playlist(self):
        """
        Allow the user to select and display a single M3U playlist for conversion.
        """
        m3u_file_path = self._prompt_for_file("Select M3U Playlist")
        if not m3u_file_path:
            return

        m3u_lines = self._read_file_lines(m3u_file_path)
        if m3u_lines is not None:
            filename = os.path.splitext(os.path.basename(m3u_file_path))[0]
            self._show_playlist_in_popup(m3u_lines, m3u_file_path, filename)

    def _prompt_for_files(self, title):
        """
        Prompt the user to select multiple M3U files.
        """
        return filedialog.askopenfilenames(
            title=title,
            filetypes=[("M3U files", "*.m3u")],
            initialdir=self.m3u_start_folder
        )

    def _prompt_for_file(self, title):
        """
        Prompt the user to select a single M3U file.
        """
        return filedialog.askopenfilename(
            title=title,
            filetypes=[("M3U files", "*.m3u"), ("All files", "*.*")],
            initialdir=self.m3u_start_folder
        )

    def _read_file_lines(self, file_path):
        """
        Read the lines of a file, handling errors.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.readlines()
        except Exception as e:
            messagebox.showerror("Error", f"Error reading file: {e}")
            return None

    def _extract_unique_titles(self, file_paths):
        """
        Extract unique file paths from multiple M3U files.
        """
        unique_titles = {}

        def extract_title_from_path(line):
            split_point = line.lower().find('dropbox')
            return line[split_point + len('Dropbox'):] if split_point != -1 else line

        for file_path in file_paths:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith("#"):  # Skip empty lines and comments
                        title = extract_title_from_path(line)
                        if title not in unique_titles:
                            unique_titles[title] = line
        return unique_titles

    def _show_playlist_in_popup(self, m3u_lines, m3u_file_path, filename):
        """
        Display the contents of an M3U playlist in a popup window.
        """
        m3u_lines = [line.strip() for line in m3u_lines if line.strip()]

        popup = self._create_popup("Playlist Preview", "800x600")
        frame = self._create_frame(popup)
        tree = self._create_treeview(frame)

        self._populate_treeview(tree, m3u_lines)
        self._add_convert_button(popup, m3u_lines, m3u_file_path, filename)

        self._finalize_popup(popup)

    def _create_popup(self, title, size):
        """
        Create and configure a popup window.
        """
        popup = Toplevel(self.root)
        popup.title(title)
        popup.geometry(size)
        return popup

    def _create_frame(self, parent):
        """
        Create a frame inside a given parent widget.
        """
        frame = Frame(parent)
        frame.pack(fill='both', expand=True)
        return frame

    def _create_treeview(self, parent):
        """
        Create a Treeview widget to display playlist contents.
        """
        columns = ('#', 'Path')
        tree = ttk.Treeview(parent, columns=columns, show='headings')
        tree.heading('#', text='#')
        tree.heading('Path', text='Path')
        tree.column('#', width=30, anchor='center')
        tree.column('Path', anchor='w')

        # Add scrollbar to the Treeview
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)

        return tree

    def _populate_treeview(self, tree, m3u_lines):
        """
        Populate the Treeview with lines from an M3U playlist.
        """
        for index, line in enumerate(m3u_lines):
            if 'Dropbox' in line:
                tree.insert('', 'end', values=(index + 1, line), tags=('highlight',))
                tree.tag_configure('highlight', foreground='blue')
            else:
                tree.insert('', 'end', values=(index + 1, line))

    def _add_convert_button(self, popup, m3u_lines, m3u_file_path, filename):
        """
        Add a button to convert and save the playlist.
        """
        convert_button = ttk.Button(
            popup,
            text="Convert Playlist",
            command=lambda: self.convert_and_save(m3u_lines, filename)
        )
        convert_button.pack(pady=self.pad)

    def _finalize_popup(self, popup):
        """
        Finalize the popup by setting it as modal.
        """
        popup.transient(self.root)
        popup.grab_set()
        self.root.wait_window(popup)

    def convert_and_save(self, m3u_lines, filename):
        """
        Convert playlist paths to match different Dropbox paths and save them for each computer.
        """
        path_map = self.path_map

        def get_computer_name_for_path(path):
            for computer_name, dropbox_path in path_map.items():
                if path.startswith(dropbox_path):
                    return computer_name
            return None

        for computer_name, dropbox_path in path_map.items():
            new_m3u_path = os.path.join(self.playlist_path_map[computer_name], f"{filename}_{computer_name}.m3u")

            try:
                with open(new_m3u_path, 'w', encoding='utf-8') as new_file:
                    for line in m3u_lines:
                        if 'Dropbox' in line:
                            split_point = line.lower().find('dropbox')
                            original_computer = get_computer_name_for_path(line)
                            if original_computer == computer_name:
                                new_line = line
                            else:
                                new_line = dropbox_path + line[split_point + len('Dropbox'):]
                            new_file.write(new_line + '\n')
                        else:
                            new_file.write(line + '\n')
            except Exception as e:
                messagebox.showerror("Error", f"Error saving file for {computer_name}: {e}")
                return

        self._show_success_message(path_map,filename)

    def _show_success_message(self, path_map, filename):
        """
        Display a success message listing the saved M3U file paths.
        """
        saved_files = ', '.join(
            [os.path.join(self.playlist_path_map[cn], f"{filename}_{cn}.m3u") for cn in path_map.keys()]
        )
        messagebox.showinfo("Success", f"Playlists converted and saved successfully at:\n{saved_files}")
