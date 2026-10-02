"""Abre el creador de diapos de las tandas (se lanza desde TangoTags → Crear diapos)."""
import tkinter as tk

from presentation_app import PresentationApp

if __name__ == "__main__":
    root = tk.Tk()
    PresentationApp(root)
    root.mainloop()
