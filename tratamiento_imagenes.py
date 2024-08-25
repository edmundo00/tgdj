from PIL import Image as PilImage
from os import listdir, makedirs
from os.path import isfile, join, splitext, basename


def apply_gradient_overlay(background_image_path, orchestra_path, image_folder):
    # Extract the base name (filename with extension)
    base_name = basename(orchestra_path)
    # Split the base name into filename and extension
    file_name_without_extension, _ = splitext(base_name)

    # Open the original image
    base = PilImage.open(background_image_path).convert("RGBA")
    orchestra = PilImage.open(orchestra_path).convert("RGBA")

    maximum_in_width = 0.4 * base.width
    maximum_in_height = base.height

    resize_factor = maximum_in_height / orchestra.height

    if (resize_factor * orchestra.width) > maximum_in_width:
        resize_factor = maximum_in_width / orchestra.width

    new_width = int(orchestra.width * resize_factor)
    new_height = int(orchestra.height * resize_factor)

    # Resize the orchestra image
    orchestra = orchestra.resize((new_width, new_height), PilImage.Resampling.LANCZOS)

    # Create a gradient overlay
    gradient = PilImage.new('L', (base.width, base.height))
    for x in range(base.width):
        gradient_value = int(255 * (1 - x / base.width))
        for y in range(base.height):
            gradient.putpixel((x, y), gradient_value)

    # Convert gradient to RGBA
    gradient_rgba = PilImage.new('RGBA', base.size)
    for y in range(base.height):
        for x in range(base.width):
            gradient_rgba.putpixel((x, y), (105, 105, 105, gradient.getpixel((x, y))))

            # Apply the gradient to the base image
    combined = PilImage.alpha_composite(base, gradient_rgba)

    # Paste the resized orchestra image onto the combined image
    position = (0, combined.height - orchestra.height)
    combined.paste(orchestra, position, orchestra)

    # Save the combined image
    merged_image_path = join(image_folder, f'{file_name_without_extension}_background.png')
    combined.save(merged_image_path, "PNG")

    return merged_image_path


def apply_to_all_images_in_folder(background_image_path, source_folder, destination_folder):
    # Ensure the destination folder exists
    makedirs(destination_folder, exist_ok=True)

    # Get all files in the source folder
    files = [f for f in listdir(source_folder) if isfile(join(source_folder, f))]

    # Apply the overlay to each image in the folder
    for file_name in files:
        source_file_path = join(source_folder, file_name)
        # Call the function for each image
        apply_gradient_overlay(background_image_path, source_file_path, destination_folder)


# Example Usage
background_image_path = "E:\\Dropbox\\MUSICA\\MP3\\TANGO\\other_stuff\\PYTHON\\tgdj\\images\\backgounds\\background_tango.png"
source_folder = "E:\\Dropbox\\MUSICA\\MP3\\TANGO\\other_stuff\\PYTHON\\tgdj\\images\\orquestas"
destination_folder = "E:\\Dropbox\\MUSICA\\MP3\\TANGO\\other_stuff\\PYTHON\\tgdj\\images\\orquestas_con_fondo"

apply_to_all_images_in_folder(background_image_path, source_folder, destination_folder)
