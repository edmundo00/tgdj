# TangoTags

Pone bien las tags de las canciones de tango según la base de datos, siempre con el mismo
formato, y crea las diapos de las tandas.

## Arrancar

- Doble clic en **`TangoTags.bat`** (necesita el `.venv` de este proyecto), o
- **`dist\TangoTags\TangoTags.exe`** (no necesita Python; se genera con `crear_exe.bat`).

## Cómo se usa

La barra de arriba sigue el orden de trabajo:

| Paso | Botones | Qué hace |
|---|---|---|
| ① Cargar | Archivos · Carpeta · Playlist · MusicBee | Carga canciones y las busca en la base de datos. Las ya revisadas se saltan (*Opciones*) |
| ② Revisar | Marcar sugeridas · Desmarcar todo · Buscar en BD · Parar música | A la izquierda las tags del archivo, a la derecha las coincidencias **ya con el formato final**. Marca **Usar** en la buena (las sugeridas vienen marcadas). Se pueden editar las celdas de la BD; doble clic en una canción sin coincidencias para buscarla a mano. ▶ para escuchar |
| ③ Aplicar | Aplicar tags · Deshacer | Muestra antes/después y, si confirmas, escribe. Siempre guarda antes una copia para poder **deshacer** |
| ④ Diapos | Crear diapos · Control diapos | Presentación de las tandas desde una playlist (con vista previa) / pasar diapos durante la milonga |

**Colores** de la comparación: verde = igual, amarillo = parecido (p. ej. mismo año), naranja =
parcial (falta el dato), rojo = distinto.

Menú **Ayuda → Cómo se usa** (F1) tiene la misma explicación dentro de la app.
Si cargas desde MusicBee, después de aplicar haz en MusicBee *Herramientas → Volver a leer tags*.

### Fechas de CD y "Marcar por disco"

Muchos archivos traen la fecha de salida del CD (p. ej. 2014), no la de grabación. Si la fecha es
posterior a la muerte del director, o muy posterior a todas las grabaciones, se muestra como
**"2014 (CD)"** y no se usa para elegir: la canción queda en *Hay que elegir* sin nada marcado.
Las opciones salen en orden cronológico y sin repetir. 💿 marca las que encajan con los años de las
demás canciones del mismo disco (álbum o carpeta); **Marcar por disco** marca la opción cuando solo
encaja una. Siempre se puede escuchar el archivo (▶) y los fragmentos de la BD (▶30s/▶10s).

### Buscar en la base de datos (Ctrl+F)

Una sola caja: escribe palabras de título, orquesta, cantor o compositor en cualquier orden, sin
preocuparte de acentos (`rosa firpo`, `pugliese chanel`). Un año (`1944`), un rango (`1940-1945`) o
una década (`1940s`) filtran por fecha. Filtros de un clic por estilo, fuente y "con audio".
Las filas repetidas de la misma grabación salen juntas, con su fuente (El Recodo / tango.info).
La ventana puede quedarse abierta: sigue a la canción seleccionada y *Usar para esta canción*
(o doble clic / Enter) se la asigna. *Corregir datos…* guarda correcciones en
`data/correcciones.csv`, que se aplican siempre al cargar.

### Deshacer

Cada *Aplicar tags* guarda `output/backups/tags_FECHA.csv` con el valor anterior de cada campo.
**Deshacer** (Ctrl+Z) restaura el último; *Archivo → Historial de cambios* cualquiera anterior.

## Formato de las tags

Definido en un solo sitio: [`src/utils/formato_tags.py`](src/utils/formato_tags.py).

| Tag | Formato | Ejemplo |
|---|---|---|
| Artista | `Orquesta / Cantor` (varios: `A y B`) | `Juan D'Arienzo / Héctor Mauré` |
| Fecha | `AAAA-MM-DD` (o `AAAA-MM` / `AAAA` si no se sabe más) | `1941-07-14` |
| Género | minúsculas | `tango`, `tango vals`, `tango milonga` |
| Compositor | `Musica: X - Letra: Y`, siempre (`?` si no se sabe) | `Musica: Horacio Pettorossi - Letra: Horacio Pettorossi` |

Si un dato no se conoce en la base de datos esa tag no se toca. El compositor se escribe siempre:
`Musica: ? - Letra: ?` es la marca de que la canción ya pasó por la base de datos.
Formatos de audio: mp3, flac, m4a, wav, aiff, wma.

La búsqueda del artista entiende `Orquesta / Cantor`, `Orquesta; Cantor`, `feat.`,
`Apellido, Nombre` y "Orquesta Típica de …", sin importar mayúsculas ni acentos
([`src/utils/buscar_artista.py`](src/utils/buscar_artista.py)).

## Base de datos

- `data/mergeddb.csv` – la base original (El Recodo + tango.info).
- `data/tangodb.csv` – la que usa la app: `mergeddb.csv` limpia por
  [`src/utils/mejorar_bd.py`](src/utils/mejorar_bd.py) (una sola grafía por orquesta/cantor,
  compositores y fechas completados solo cuando no hay duda).
  Se regenera con *Archivo → Regenerar base de datos limpia* o `python -m src.utils.mejorar_bd`.
- `output/informe_fechas_dudosas.csv` – grabaciones cuya fecha no se pudo arreglar.

## Configuración

- `config.ini` → ruta de Dropbox (`music_path`).
- `src/config/config.py` → datos por defecto de la milonga para las diapos, carpetas, etc.

## Estructura

```
tangotags.py               arranque de la app
src/ui/                    ventanas (principal, crear diapos)
src/diapos/generador.py    creación del PowerPoint
src/utils/                 formato de tags, búsqueda, historial, base de datos
control_slides.py          control de diapos (también abre suelto / control_slides.exe)
herramientas/              scripts sueltos: descargar tango.info, preparar fotos de orquestas
tests/                     run_all_test.bat
```

## Git

```
git add .
git commit -m "mensaje"
git push
```
