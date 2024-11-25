import win32print
import win32gui

# Obtén el factor de escalado del DPI
def obtener_factor_dpi():
    hdc = win32gui.GetDC(0)  # Obtiene el contexto del dispositivo de la pantalla principal
    dpi_x = win32print.GetDeviceCaps(hdc, 88)  # DPI horizontal
    dpi_y = win32print.GetDeviceCaps(hdc, 90)  # DPI vertical
    return dpi_x / 96, dpi_y / 96  # 96 DPI es el valor de referencia para 100%

factor_x, factor_y = obtener_factor_dpi()
print("Factor de escalado en X:", factor_x)
print("Factor de escalado en Y:", factor_y)
