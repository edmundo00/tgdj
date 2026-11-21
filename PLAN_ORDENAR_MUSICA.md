# Plan · Ordenar TODA la música (una canción = una ficha, un archivo bueno)

*Propuesta del 20-11-2026 (PC de casa). Edmundo dijo «empieza» (fases 1–4) el mismo día.*

**Resultado fases 1–4 (20-11-2026, 15:55):** 49.703 archivos = 27.631 grabaciones; sobran 22.072 (154 GB).
Por sonido 7.595 grupos (96 % cuadra con el nombre), por tags 10.733, dudosas 2.509, sin ficha 6.794 (3.339 cortinas).
Carpeta Edmundo: 5.888 = 4.805 grabaciones, 1.083 copias (9,4 GB); 768 tienen mejor copia en otra colección.
Ajustes que hizo falta: tríos en vez de parejas, umbral 12 votos (medido), recopilaciones aparte (27).

**Estado (20-11-2026, 11:00):** scripts hechos y probados con 200 canciones + 100 extractos
(`herramientas\ordenar_musica\`: `huellas_todas.py`, `grupos.py`, `fichas.py`, todo seguido `ordenar_musica.bat`).
Huellas de todo en marcha. Los extractos de El Recodo **ya estaban bajados**: `tangolinkdatabase\MP3\_TANGO\mediatheque\`
(carpetas `30x` = trozo largo, 16.623; `2x` = corto), así que la decisión 2 está resuelta. En la prueba, la
agrupación salió muy clara (copias > 300 votos, distintas < 5) y ya juntó archivos con tags mal puestos.

## Cómo está ahora (medido el 20-11-2026)

- `TDJ\MUSICA`: **49.562 archivos, 398 GB**, en 11 colecciones de distinta gente (Eduardo 15.469, Dan 7.014,
  Edmundo 5.888, Camilo Gatica 4.897, Leandro 4.014, …).
- TangoTags ya tiene «Mi biblioteca» (SQLite con 46.313 canciones) y empareja cada archivo con la base de datos
  (tangoinfo / El Recodo / TangoTunes…) **por los tags**: 26.913 «perfecta», 7.402 «preferida», 6.647 «dudosa»,
  5.351 sin título o sin orquesta. Las que tienen tags malos no se pueden identificar así.
- Repetidos, contando por título + orquesta + año (aproximado; con tags malos se escapan más):
  - carpeta **Edmundo** (la del portátil): 5.882 archivos → ~4.285 temas, **~1.600 sobran, ~13 GB**;
  - **todo**: 46.313 archivos → ~24.000 temas, **~22.000 sobran, ~150 GB**.
- Shazam propio ya hecho y probado (`src\diapos\huellas.py`): 1,6 s por canción → todo en **~3 h** de máquina.

## La idea: tres capas que hoy están mezcladas

1. **El SONIDO** (huella acústica): dice qué archivos son la misma grabación aunque los tags estén mal
   o vacíos, se llamen distinto o estén en cualquier carpeta. No necesita ningún dato escrito.
2. **La FICHA** (qué grabación es): orquesta, cantor, título, fecha de grabación, sacada de la base de datos
   (El Recodo / tangoinfo). Se pone **una vez por grupo de sonido**, no por archivo.
3. **EL ARCHIVO BUENO**: de cada grupo, una sola copia «maestra» (la de más calidad); las demás son repetidas.

Las carpetas dejan de importar: se ordena desde la ficha, no desde dónde estaba el archivo.

## Fases (cada una se enseña probada y se espera el visto bueno, como «Mi biblioteca»)

**Fase 1 · Huellas de todo** (~3 h de máquina, prioridad baja, se corta y sigue). Una huella por archivo en
la base de datos de la biblioteca (la columna `huella` ya existe y está vacía). No toca ningún archivo.

**Fase 2 · Grupos «suenan igual»**. Cada archivo se busca contra todos → grupos de copias de la misma
grabación. Salen dos cosas útiles ya: la lista de repetidos de verdad (aunque tengan nombres distintos) y,
de paso, archivos rotos o cortados (un trozo que solo cuadra con parte de otro).
- Ojo: dos transferencias distintas del mismo disco de 78 (otra velocidad o tono) pueden NO salir juntas:
  el Shazam no aguanta cambios de velocidad. Se hace una segunda pasada que prueba ±3 % de velocidad
  entre los que tienen el mismo título; si cuadran, mismo grupo «transferencias distintas».

**Fase 3 · Ficha de cada grupo**. Se juntan los tags de todos los archivos del grupo (si 5 copias dicen
«Biagi 1938» y una dice «D'Arienzo», gana Biagi) y se empareja con la base de datos con el motor que ya
tiene TangoTags. Lo dudoso va a una lista «Revisar» de TangoTags, **un grupo cada vez** (24.000 grupos en vez de
46.000 archivos, y la mayoría saldrán solos). Duración del archivo ↔ duración en la base de datos ayuda a desempatar.
- **Si están los extractos de audio de El Recodo**: se les saca huella también y se identifica cada grupo
  POR EL SONIDO contra El Recodo. Eso es lo mejor: ni los tags hacen falta. (Ver decisión 2.)

**Fase 4 · Elegir la copia maestra** de cada grupo, sola: FLAC antes que MP3, más bits y frecuencia,
sin cortes ni silencio de más, transferencia preferida (p. ej. TangoTunes/HistoTango antes que otras;
la lista de preferencias la decide Edmundo). Se le escriben los tags correctos desde la ficha.

**Fase 5 · La biblioteca ordenada** (ver decisión 1). Una carpeta nueva `TDJ\BIBLIOTECA\` con una
canción por grabación: `<Orquesta>\<Año>\<Orquesta> - <Título> (<Cantor>) <AAAA-MM-DD>.flac`.
Las repetidas no se borran: van a `TDJ\_repetidos\` (como la papelera) hasta que Edmundo diga.
- **Ojo VirtualDJ / MusicBee / listas `.m3u`**: guardan los marcadores y el historial por ruta. Antes de
  mover nada, un script que reescriba las rutas viejas → nuevas en la base de VirtualDJ, las listas y
  MusicBee (copia de seguridad antes). Sin esto se perderían los cue points.

**Fase 6 · El portátil sin repetidos**. La carpeta del portátil deja de ser una copia a mano: es una
SELECCIÓN de la biblioteca (ver decisión 3) que se sincroniza con un script (añade lo nuevo, quita lo
que ya no va). Imposible que haya repetidos: cada grabación existe una sola vez.

**Fase 7 · Que no vuelva a desordenarse**. Todo lo nuevo entra por `TIDAL Download` (la bandeja):
huella → «¿ya la tengo?» (si la nueva es mejor, sustituye a la maestra; si no, a repetidos) → ficha →
a su sitio en `BIBLIOTECA`. Un botón en TangoTags.

Extra que sale gratis: el Shazam de la tablet (presentación en vivo) y «¿la tengo?» funcionan con toda la música.

## Decisiones de Edmundo (antes de empezar la fase 5; las fases 1–4 no tocan nada y se pueden hacer ya)

1. **Mover o copiar**: ¿la copia maestra se MUEVE a `BIBLIOTECA` (no ocupa más; las colecciones de Eduardo,
   Dan… se quedan solo con lo que no es repetido) o se COPIA y las colecciones se quedan intactas como archivo
   (unos 250 GB más en Dropbox)? Propuesta: mover.
2. **Extractos de El Recodo**: ¿dónde están? (en el PC solo se ha encontrado `El_Recodo_letras.csv`).
3. **Qué va al portátil**: ¿toda la biblioteca tango (~250 GB), o lo pinchado + con estrellas + lo marcado?
4. **Preferencia de transferencias**: cuando hay varias buenas del mismo disco, ¿cuál gana?
