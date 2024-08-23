from ui.gui import MainWindow, load_resources
import tkinter as tk

if __name__ == "__main__":
    print("Starting the application...")  
    root = tk.Tk()
    icons, images = load_resources()
    app = MainWindow(root, icons, images)
    root.mainloop()
    print("Application ended.") 