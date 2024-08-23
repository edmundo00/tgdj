import tkinter as tk
from presentation_app import PresentationApp


def test_presentation_app():
    # Create the main Tkinter root window
    root = tk.Tk()

    # Create an instance of the PresentationApp class
    app = PresentationApp(root)

    # Run the Tkinter main loop to start the application
    root.mainloop()


if __name__ == "__main__":
    test_presentation_app()
