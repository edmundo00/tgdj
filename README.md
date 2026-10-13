# TangoTags

Pone bien las tags de las canciones de tango según la base de datos, siempre con el mismo
formato, y crea las diapos de las tandas.

## Arrancar

- Doble clic en **`TangoTags.bat`** o en el acceso directo `tangotags.vbs` del escritorio (necesitan el `.venv`
  de este proyecto), o
- **`dist\TangoTags\TangoTags.exe`** (no necesita Python; se genera con `crear_exe.bat`).

## Mi biblioteca (la pestaña de inicio)

Al abrir la app ves **toda tu música** (pestaña *📚 Mi biblioteca*), al día sola. A la izquierda, listas:

| Lista | Qué hay |
|---|---|
| 🆕 **Nuevas** | Desde la última vez que abriste la app · últimos 7 días · últimos 30 días |
| ✎ **Por revisar** | *Sugeridas* (hay una grabación clara) · *Hay que elegir* (y de ellas, *con fecha de CD*) · *Título / Artista no encontrado* · *Por comparar* |
| 📚 **Toda la música** | Todas · Perfectas · No tocar · ☁ Solo en la nube (archivos de Dropbox sin descargar en ese ordenador) |
| 🗂 **Colecciones** | Cada colección con su árbol de carpetas |

Las «No tocar» no salen en *Por revisar*. La caja de arriba busca dentro de la lista (palabras sueltas, `1944`,
`1940-1945`, `1940s`); clic en una cabecera para ordenar. **Revisar estas** (o doble clic, o Intro) lleva las
seleccionadas —o toda la lista— a la pestaña *✎ Revisar*. Espacio escucha; clic derecho: abrir carpeta, «No tocar».

Lo que haces (aplicar, editar, deshacer, «No tocar», mover duplicados) se ve en Mi biblioteca **al momento**
(si son más de 40 canciones, en unos segundos: se hace en segundo plano).

## Cómo se usa

La barra de arriba sigue el orden de trabajo:

| Paso | Botones | Qué hace |
|---|---|---|
| ① Cargar | Archivos · Carpeta · Playlist · MusicBee | Carga canciones y las busca en la base de datos. Las ya revisadas se saltan (*Opciones*) |
| ② Revisar | Marcar sugeridas · Desmarcar todo · Buscar en BD · Parar música | A la izquierda las tags del archivo, a la derecha las coincidencias **ya con el formato final**. Marca **Usar** en la buena (las sugeridas vienen marcadas). Se pueden editar las celdas de la BD; doble clic en una canción sin coincidencias para buscarla a mano. ▶ para escuchar |
| ③ Aplicar | Aplicar tags · Deshacer | Muestra antes/después y, si confirmas, escribe. Siempre guarda antes una copia para poder **deshacer** |
| ④ Diapos | Crear diapos · Control diapos | Presentación de las tandas desde una playlist .m3u o .mbp de MusicBee (con vista previa y **revisión**) / pasar diapos durante la milonga |

**Colores** de la comparación: verde = igual, amarillo = parecido (p. ej. mismo año), naranja =
parcial (falta el dato), rojo = distinto.

### Revisión antes de crear las diapos

Al cargar la playlist en *Crear diapos* (vale la `.mbp` de MusicBee directamente) se revisa y se ve abajo
(clic en un aviso = ir a la tanda; en la tabla, la hora a la que empieza cada tanda):

- ❌ **Errores**: canciones fuera de `MUSICA\Edmundo` (no estarán en el portátil) o que no existen, falta una
  cortina entre tandas, el mismo archivo o tema dos veces en una tanda. Si hay errores, pregunta antes de crear.
- ⚠ **Avisos**: tandas que no son de 3–4 temas, mezcla de orquestas, de instrumentales y cantadas o de cantores,
  años separados más de 8, sin año, cortinas dobles, vals y milonga sin tango en medio, la misma orquesta o
  cantor a menos de 4 tandas, un tema que suena dos veces en la noche, archivos solo en la nube, que la música
  no quepa en el horario.
- ℹ **Info**: minutos libres, pocas instrumentales, Pugliese en el primer tercio, temas sin compositor en la diapo.
- **Patrón de bloques** (arriba en la ventana): *Detectarlo* averigua cuál sigues —2-1-2-1 (T-T-V-T-T-M), 3-1-3-1,
  4-1-4-1 o 2-1-1-1 (T-T-V-T-M)— y avisa donde se rompe («aquí tocaría milonga», «otra vez vals»); también se
  puede elegir uno o *Libre*. Empezar con más tangos para calentar no es error. **Sin milonga los últimos 40 min**
  (se puede cambiar; 0 = no mirar). Abrir con una orquesta difícil (Pugliese, Salgán…) o ponerla en el primer
  tercio sale como consejo. Todo son consejos: nunca impide crear la presentación.
- **Carácter** (columna de la tabla): sale de `data/caracter_orquestas.csv`, una fila por orquesta y época (y a veces
  cantor) con carácter (rítmico, melódico, lírico, dramático), energía 1–5, dificultad 1–3 y notas. Botón
  *Editar tabla de carácter…* (se abre con Excel; guarda y pulsa *↻ Volver a revisar*). Con ella avisa de tandas
  que mezclan carácter, de 3 tandas muy tranquilas o muy enérgicas seguidas, de abrir con algo difícil, y lista
  las orquestas que aún no están en la tabla.
- **BPM** (columna en las tandas y en las canciones): se calcula del audio al cargar la playlist (30 s del centro
  de cada tema, ~0,2 s por canción) y se guarda en `%LOCALAPPDATA%\TangoTags\bpm.sqlite` (la próxima vez sale al
  momento). Cada género se mide en su escala (tango 85–170, vals 150–300, milonga 70–140) para que no salga a la
  mitad o al doble. En las milongas es menos fiable (el ritmo de habanera confunde).
- **Con el BPM**: aviso si un tema de la tanda va más de un 10 % más rápido o lento que el resto (en milonga solo
  info); info si la tanda *baja* (cierra con el tema más lento), si un bloque de tangos va de más a menos energía,
  o si la milonga del ciclo tiene menos energía que su vals.
- **Curva de la noche** (abajo a la derecha): una barra por tanda, altura = energía (tabla de carácter afinada con
  el BPM), color = tango / vals / milonga, la hora de inicio y una raya donde empieza el final sin milonga.
  Clic en una barra = ir a la tanda.
- **Cortinas**: aviso si una cortina se repite en la noche, dura menos de 25 s o parece de tango (su artista es una
  orquesta); info si hay 3 del mismo artista o dos seguidas. Se mide cuánto «se mueve» cada cortina (columna BPM de
  las canciones: *tranquila / media / animada*, límites sacados de tus cortinas de 5 estrellas) y se aconseja si una
  muy tranquila va antes de una milonga o de una tanda con mucha energía, o una muy animada antes de una tranquila.
- **Milongas anteriores en el mismo sitio** (playlists `AAMMDD_Lugar` de la misma carpeta, último año): info de las
  cortinas y tandas que ya sonaron allí; si casi toda la noche se repite, un solo aviso («Es casi la misma playlist…»).
- **La Cumparsita** al final va sola (aunque no lleve cortina delante): su propia diapo, sin compararla con nada.
  Dentro de una tanda o a mitad de la noche: aviso.

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

### Ver qué cambiará, editar a mano y columnas

Al marcar una opción, las celdas de tu archivo que van a cambiar salen en amarillo como «antes → después».
**Editar a mano** (botón, tecla **E** o doble clic en la parte del archivo): formulario con título, orquesta,
cantor, fecha, estilo, música y letra, con el formato correcto, copia de seguridad y deshacer.
Clic derecho en la cabecera de cualquier tabla para ocultar/mostrar columnas; los anchos se recuerdan.

### ¿La tengo? (en el buscador)

Columna **Tuya**: ✔ esa grabación está en tu colección, ≈ tienes ese tema por esa orquesta con otra fecha.
Filtros **La tengo** / **Me falta** (p. ej. `di sarli rufino` + *Me falta* = lo que te falta de Di Sarli con
Rufino). La ficha dice dónde la tienes y *Escuchar la mía*. Usa los datos de Mi biblioteca.

### Revisar rápido con el teclado

En la tabla: **1–9** elige la opción, **0** ninguna, **Espacio** escucha tu archivo, **S** va a la siguiente
canción por decidir, **X** la marca como **No tocar** (no vuelve a aparecer al cargar;
*Archivo → Canciones «No tocar»* para deshacerlo).

### Grafías de nombres

`data/grafias.csv` dice cómo escribir cada orquesta/cantor ("Carlos di Sarli", "Alfredo de Angelis"…) y
manda sobre la base de datos. Se creó con la forma que más usas en tu colección;
*Archivo → Grafías de nombres…* para cambiarla.

### Biblioteca (toda tu música)

La app conoce toda tu música: `TDJ/MUSICA` (cada subcarpeta es una colección; sin `musica_variada_edmundo`)
y `TDJ/TIDAL Download` (la bandeja de entrada). Se configura en *Archivo → Carpetas de la biblioteca* y se
guarda en `data/biblioteca.json` (rutas relativas a Dropbox: vale en todos los ordenadores).

Al abrir la app se pone al día **en segundo plano** (abajo a la derecha: «📚 46.308 canciones · al día»): mira
tamaño y fecha de cada archivo (unos segundos) y solo lee las tags de lo nuevo o cambiado. Reconoce las
canciones **movidas** (p. ej. de TIDAL Download a MUSICA) sin perder su fecha de llegada. Los archivos
«solo en la nube» de Dropbox no se abren. *Archivo → Actualizar la biblioteca ahora* para volver a mirar.

La base de datos es local (`%LOCALAPPDATA%\TangoTags\biblioteca.sqlite`, una por ordenador) y es una
caché: si se borra, se reconstruye. Tus decisiones (No tocar, grafías, correcciones, copias) siguen en Dropbox.
Para no tener que reconstruirla nunca:

- tras cada actualización se guarda una copia (`biblioteca.sqlite.copia`, menos de 1 s);
- al abrir se comprueba; si estuviera dañada se aparta (`.dañada-FECHA`), se recupera la copia y avisa;
- aunque abras la app dos veces, solo una actualiza la biblioteca;
- si una carpeta raíz no está (Dropbox o un disco no disponibles) o «desaparece» de golpe más del 20 % de su
  música, no se quita nada de la biblioteca.

**En otro ordenador** (p. ej. el portátil, con Dropbox en `C:\Dropbox`): la primera vez la biblioteca se
prepara sola leyendo las tags de toda la música (unos 30 minutos; un aviso arriba enseña el progreso y se
puede usar la app mientras). Después, como siempre: segundos.

### Estado de la colección y duplicados

*Archivo → Estado de la colección*: por colección, cuántas perfectas, sugeridas, por elegir, sin coincidencia…
(sale de la biblioteca: al momento). Doble clic en una colección para revisarla.
*Archivo → Duplicados*: copias de audio idéntico **dentro de cada colección**; se elige cuál conservar y el
resto se **mueve** a `MUSICA/_duplicados` (nunca se borra; se puede deshacer).

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

- `config.ini` → ruta de Dropbox (`music_path`). Como está dentro de Dropbox es el mismo en todos los
  ordenadores: si esa ruta no existe en uno (p. ej. `D:\Dropbox` en el portátil, que lo tiene en `C:\Dropbox`),
  la app usa la carpeta que dice el propio Dropbox. También se puede poner una por usuario de Windows en
  `[UserPaths]`. Las rutas guardadas en un ordenador (copias para deshacer, playlists, duplicados movidos) se
  traducen solas al otro.
- `src/config/config.py` → datos por defecto de la milonga para las diapos, carpetas, etc.

## Estructura

```
tangotags.py               arranque de la app
src/biblioteca/            Mi biblioteca: SQLite local, escáner incremental, emparejado en procesos aparte
src/motor/emparejar.py     el motor que compara una canción con la base de datos de tango
src/ui/                    ventanas (principal, Mi biblioteca, buscador, estado, duplicados, playlists, diapos)
src/diapos/generador.py    creación del PowerPoint
src/diapos/revision.py     revisión de la playlist antes de las diapos
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
