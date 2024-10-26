import os
import time
import win32com.client

# Path to the tracklist file
tracklist_path = os.path.expandvars(r'%LocalAppData%\VirtualDJ\History\tracklist.txt')

# Function to read and parse the last line of the tracklist file
def read_last_line_of_tracklist(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            if lines:
                # The last line should have the format "Time : Artist - Song"
                last_line = lines[-1].strip()
                # Split the line to extract "Artist - Song" (ignore time)
                if " : " in last_line:
                    artist_song = last_line.split(" : ", 1)[1]
                    return artist_song  # Return the artist and song part only
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    return None

# Function to search for a slide by the content stored in the notes
def find_slide_by_notes(presentation, search_text):
    for slide in presentation.Slides:
        # Check the slide notes for the search_text
        notes = slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
        if search_text.lower() in notes.lower():
            return slide.SlideNumber
    return None

# Function to control the PowerPoint slideshow
def goto_slide(slideshow, slide_number):
    if slide_number:
        slideshow.View.GotoSlide(slide_number)
        print(f"Jumping to slide {slide_number}")
    else:
        print("Slide not found.")

# Open PowerPoint application
powerpoint = win32com.client.Dispatch("PowerPoint.Application")
powerpoint.Visible = True  # Make PowerPoint visible

presentation = powerpoint.Presentations.Open(
    r'D:\Dropbox\TDJ\PYTHON\tgdj\output\presentation.pptx')  # Update with the correct path to your presentation

# Main loop to wait for the slideshow to start and control it
while True:
    try:
        # Try to access the running slideshow window
        slideshow = powerpoint.SlideShowWindows(1)
    except IndexError:
        print("Waiting for you to start the slideshow...")
        time.sleep(2)
        continue

    # Slideshow has started, control it
    last_line = read_last_line_of_tracklist(tracklist_path)

    if last_line:
        print(f"Last line from tracklist: {last_line}")

        # Find the slide that has this song/artist in the notes
        slide_number = find_slide_by_notes(presentation, last_line)

        # If the slide is found, go to it
        goto_slide(slideshow, slide_number)

    # Wait for 5 seconds before checking again
    time.sleep(5)

