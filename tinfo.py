import requests
from bs4 import BeautifulSoup
import pandas as pd
import string


# Función para scrapear solo los datos de la página principal, incluyendo enlaces TIWC y TINT
def scrape_page(url, session):
    try:
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "lxml")

        # Encuentra la tabla con las pistas
        table = soup.find("table", class_="listing sortable")
        if not table:
            print(f"No se encontraron datos para {url}")
            return []

        scraped_data = []

        # Iterar sobre cada fila de la tabla
        rows = table.find("tbody").find_all("tr")
        for i, row in enumerate(rows):
            cols = row.find_all("td")

            # Extrae los datos básicos y enlaces específicos
            track_data = {
                "Image Link": "https://tango.info" + cols[0].find("a")["href"] if cols[0].find("a") else None,
                "Title": cols[1].get_text(strip=True),
                "Title Link": "https://tango.info" + cols[1].find("a")["href"] if cols[1].find("a") else None,
                "TIWC": cols[2].get_text(strip=True),
                "TIWC Link": "https://tango.info" + cols[2].find("a")["href"] if cols[2].find("a") else None,
                "Genre": cols[3].get_text(strip=True),
                "Instrumentalists": cols[4].get_text(strip=True),
                "Vocalists": cols[5].get_text(strip=True),
                "Language": cols[6].get_text(strip=True),
                "Perf. Date": cols[7].get_text(strip=True),
                "Duration": cols[8].get_text(strip=True),
                "TINT Number": cols[9].get_text(strip=True),
                "TINT Link": "https://tango.info" + cols[9].find("a")["href"] if cols[9].find("a") else None,
            }
            scraped_data.append(track_data)

            # Imprimir progreso
            print(f"Scraping letter {url[-1]}: {i + 1} de {len(rows)} canciones procesadas")

        return scraped_data

    except Exception as e:
        print(f"Error al scrapear {url}: {e}")
        return []


# URL base para cada letra
base_url = "https://tango.info/track/"

# Lista para almacenar todos los datos
all_data = []

# Crear una sesión de requests para optimizar
with requests.Session() as session:
    # Iterar a través de cada letra del alfabeto
    for letter in string.ascii_uppercase:
        url = f"{base_url}{letter}"
        print(f"Scraping {url}")
        page_data = scrape_page(url, session)

        # Agregar los datos de la letra actual a la lista principal
        if page_data:
            all_data.extend(page_data)
        else:
            print(f"No se encontraron datos para la letra {letter}")

# Crear un DataFrame y guardar todos los datos en un solo archivo CSV
df = pd.DataFrame(all_data)
df.to_csv("tangoinfo_all_letters_with_links.csv", index=False, sep=';', encoding='utf-8')
print("Datos guardados en 'tangoinfo_all_letters_with_links.csv'")
