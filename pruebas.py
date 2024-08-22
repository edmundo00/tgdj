from PIL import Image, ImageDraw, ImageFilter

# Dimensiones de la imagen
img_width = 500
img_height = 100

# Crear una imagen nueva con fondo transparente
image = Image.new("RGBA", (img_width, img_height), (255, 255, 255, 0))

# Crear un objeto de dibujo
draw = ImageDraw.Draw(image)

# Coordenadas de la línea
start_x = 50
start_y = 50
end_x = 450
end_y = 50
line_width = 20

# Color de la línea
line_color = (255, 255, 255, 255)  # Blanco

# Dibujar la línea con extremos redondeados
draw.line((start_x, start_y, end_x, end_y), fill=line_color, width=line_width, joint="curve")

# Aplicar un filtro de suavizado para el biselado 3D
image = image.filter(ImageFilter.GaussianBlur(radius=3))

# Guardar la imagen como PNG
image.save("linea_biselada_3D.png")
