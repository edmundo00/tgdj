# TangoTags

Pone bien las tags de las canciones de tango según la base de datos (`data/mergeddb.csv`),
siempre con el mismo formato, y crea las diapos de las tandas.

## Arrancar

Doble clic en **`TangoTags.bat`**, o:

```
.venv\Scripts\python tangotags.py
```

## Cómo se usa

La barra de arriba sigue el orden de trabajo:

| Paso | Botones | Qué hace |
|---|---|---|
| ① Cargar | Archivos · Carpeta · Playlist · MusicBee | Carga canciones y las busca en la base de datos |
| ② Revisar | Marcar sugeridas · Desmarcar todo · Buscar en BD · Parar música | A la izquierda las tags del archivo, a la derecha las coincidencias **ya con el formato final**. Marca **Usar** en la buena (las sugeridas vienen marcadas). Puedes editar las celdas de la BD; doble clic en una canción sin coincidencias para buscarla a mano. ▶ para escuchar |
| ③ Aplicar | Aplicar tags | Muestra antes/después y, si confirmas, escribe las tags |
| ④ Diapos | Crear diapos · Control diapos | Crear la presentación de las tandas desde una playlist / pasar diapos durante la milonga |

Los filtros de **Mostrar** ocultan grupos (por ejemplo las *Perfectas*, que ya están bien).
Menú **Ayuda → Cómo se usa** (F1) tiene la misma explicación dentro de la app.

Si cargas desde MusicBee, después de aplicar haz en MusicBee *Herramientas → Volver a leer tags*.

## Formato de las tags

Definido en un solo sitio: [`src/utils/formato_tags.py`](src/utils/formato_tags.py) (con tests en `tests/utils/formato_tags_test.py`).

| Tag | Formato | Ejemplo |
|---|---|---|
| Artista | `Orquesta / Cantor` (varios: `A y B`) | `Juan D'Arienzo / Héctor Mauré` |
| Fecha | `AAAA-MM-DD` (o `AAAA-MM` / `AAAA` si no se sabe más) | `1941-07-14` |
| Género | minúsculas | `tango`, `tango vals`, `tango milonga` |
| Compositor | `Musica: X - Letra: Y`, siempre (`?` si no se sabe) | `Musica: Horacio Pettorossi - Letra: Horacio Pettorossi` |

Si un dato no se conoce en la base de datos (vacío, `?`, `-`…) esa tag no se toca. El compositor se escribe siempre:
`Musica: ? - Letra: ?` es la marca de que la canción ya pasó por la base de datos.
Formatos de audio: mp3, flac, m4a, wav, aiff, wma.

## Configuración

- `config.ini` → ruta de Dropbox (`music_path`).
- `src/config/config.py` → base de datos (`DB_CSV_PATH`), datos por defecto de la milonga para las diapos, etc.

## Tests

```
run_all_test.bat
```

## Otros scripts

- `crear_diapos.py` – creador de diapos (lo abre el botón *Crear diapos*).
- `control_slides.py` / `control_slides.exe` – control de diapos en la milonga.
- `tangotags_tk_antiguo.py` – la versión vieja en Tkinter (ya no hace falta, se puede borrar).

## Git

```
git add .
git commit -m "mensaje"
git push
```
