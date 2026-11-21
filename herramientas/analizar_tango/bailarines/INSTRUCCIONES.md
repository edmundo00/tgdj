# Marcar pisadas · instrucciones completas

(Sacado de CLAUDE.md el 18-11-2026. Léelo entero antes de usar marcar_pisadas.py o video_pisadas.py.)

Para ver qué pisan los bailarines sobre la música (vídeos de Instagram, exhibiciones, alumnos) y hacer reels con
destellos en cada pisada. Carpeta: `PYTHON\tgdj\herramientas\analizar_tango\bailarines\`.

1. **Vídeo**: si es de Instagram, pedir permiso a Edmundo y bajarlo con
   `python -m yt_dlp --ffmpeg-location C:\ffmpeg\bin -f "bv*+ba/b" -o "...\original\<nombre>.%(ext)s" <enlace>`.
   Si el vídeo es de otros, pedir permiso a sus autores antes de publicar (mensaje + Colaboración de Instagram).
2. **Preparar la página** (alinea, analiza si hace falta, saca fotogramas, música y cambios de plano):
   `python marcar_pisadas.py "video.mp4" "grabación.flac" ["otra versión.flac" ...] --compases 26-30 --bailarines "Sol,London" [--salida carpeta]`
   - Con varias grabaciones candidatas elige sola la que suena (parecido > 1,0 = buena; < 1,0 = sospechar).
     La canción suele venir en los comentarios del post; buscar todas sus versiones en `D:\Dropbox\TDJ\MUSICA`.
   - Salida por defecto: `<carpeta del vídeo>\marcar_<vídeo>\` → `index.html` (dar el enlace file:/// a Edmundo).
   - Repetirlo con otros `--compases` reutiliza el alineado (config.json) y conserva las pisadas (se guardan en Chrome).
3. **Edmundo marca en la página** (la detección automática NO sirve: abrazados, el detector de cuerpo mezcla a las
   personas y el suelo de madera tiene el color de los tacones; probado con Keypoint R-CNN el 17-11-2026).
   Papeles: `--bailarines "Sol:follower,London:leader"` (carriles «Follower izq/der», «Leader izq/der»; follower
   oro/naranja, leader azul/turquesa; I/D dentro del punto). La **línea de tiempo** es lo principal: onda de la música
   con sus topes, tiempos 1 2 3 4, zoom con la rueda. Poner pisadas: arrastrar el pie desde su botón a la línea o
   al pie en la imagen; doble clic en un carril; clic en el pie en la imagen; o **al vuelo con la música: Q W (follower
   izq/der), O P (leader izq/der)** con «retraso dedo». **Imán** por defecto «sonido» (al tope de la onda); también
   rejilla, instrumento o no. Elegir una pisada en la línea la deja «a colocar»: el letrero de la imagen lo dice y el
   siguiente clic en la imagen la pone en el pie (no crea otra). Arrastrar = mover en el tiempo o a otro carril;
   Mayús+clic = varias; Esc = soltar. Botón grande PARAR / Espacio. Plegados: rejilla del compás, afinar, lista,
   estadísticas por pie, CSV. Ayuda con `?`.
   Tras cambiar la página: `probar_pagina.py` (25 comprobaciones; debe decir TODO BIEN).
   **Lo normal: «📋 Copiar para Claude»** (Ctrl+C): Edmundo pega en el chat un texto `PISADAS <id> · Sol,London · N`
   + una línea por pisada (`fotograma bailarín pie a|o x y`). **Guárdalo tal cual en `<carpeta marcar_...>\pisadas.txt`.**
   También existe «💾 Guardar» (Ctrl+S → `pisadas.json` en la carpeta que elija; si no, en Descargas).
4. **Vídeo con destellos**: `python video_pisadas.py "<carpeta marcar_...>" [--lento 0.5] [--compases 28-29] [--filas piano,contrabajo]`
   → `pisadas.mp4` con destello en cada pisada (color de cada bailarín; adorno = rosa) y la rejilla «1 y 2 y 3 y 4 y»
   estilo El Flete arriba. Textos: `--rotulos rotulos.json` (`{"27": ["español", "english"]}`, uno por compás, bajo la
   rejilla), `--titulo "A cámara lenta|Slow motion"`, `--final "pregunta|question"` (últimos 2,5 s), `--creditos "..."`.
   **Para explicar, mejor `--rejilla rejilla.json`** y **solo DOS filas a la vez** (Edmundo: con más no se sabe dónde
   mirar): una fila de música que cambia en cada compás (`"mostrar_en": [27]`: A TIEMPO → SÍNCOPA → PIANITOS → …) y la
   fila PISAN. **Lo que se explica, escrito y claro, no por brillo**: tipo `fuerte_debil` (1 y 3 «FUERTE» llenos, 2 y 4
   «débil» apagados, la palabra dentro de la casilla) y tipo `patron` con las casillas que dice el oído de Edmundo
   (`"casillas": [0,1,3,4,6]` = 1·1y·2y·3·4); se ven enteros desde el principio del compás y dan un fogonazo al sonar.
   La detección sola (golpes) confunde instrumentos: para explicar, mejor `patron`. Destellos: estrellas (`--forma
   estrella`, por defecto) en los pies de LOS DOS. Otros tipos de fila (`tiempos`, `acentos` =
   fuerte/débil por la fuerza del tiempo, `golpes` de unas pistas en unos compases —p. ej. SÍNCOPA o PIANITOS—, `pisadas`
   con una sola fila si la pareja pisa junta) y `"parados": [27, 29]` (escribe PARADOS). El 3.er elemento de cada rótulo
   es la fila que se enmarca en oro (las demás se apagan). `--destellos 0` = solo en el pie de ella; `--clics` = clic en
   cada pisada (para la cámara lenta). Ejemplo completo: `Instagram\borradores\nueve-puntos-seoul\fuente\` (rejilla.json,
   rotulos.json, armar_reel.py: varias partes + unirlas). Ojo: el separador a veces mete los bandoneones en la pista del
   piano (Di Sarli 1956: pista de bandoneones vacía en la síncopa); si Edmundo oye otro instrumento, la fila se llama
   por lo que hace (SÍNCOPA), no por el instrumento.
   Usa lo más reciente de: `pisadas.txt` / `pisadas.json` de la carpeta, o `pisadas*.json` de Descargas.
5. **(19-11-2026) Ahora también se pueden marcar en la página de ritmo** (botón «👣 marcar» junto al vídeo: Q W O P,
   fotograma a fotograma con , .): da el mismo texto PISADAS (sin la posición del pie, «0 0»: los destellos de
   video_pisadas.py necesitan x y, así que para destellos en los pies sigue haciendo falta esta herramienta).
5. **Verlo en la página de ritmo** (19-11-2026): `python ..\video.py "<carpeta _ritmo\canción>" "<carpeta marcar_...>"`
   → el vídeo a la derecha de la lupa, con el play, y las pisadas como filas «👣». Tras pegar pisadas nuevas en
   `pisadas.txt`: `python ..\video.py "<carpeta _ritmo\canción>"` (rehace los datos).
- Lanzar desde aquí con `-X utf8` y `set TDJ_SIN_PAUSA=1` (los .bat paran al final). Probar la página sin abrir nada
  en pantalla: `python probar_pagina.py "<carpeta marcar_...>"` (Edge sin ventana, perfil aparte: no toca el Chrome de Edmundo).
- Primer caso: `Instagram\borradores\nueve-puntos-seoul\` (London & Sol, «Nueve puntos» Di Sarli 1956, síncopa + parada +
  pianitos en los compases 28–29). Antes, `charamusca-seoul\` (pianitos demasiado rápidos: mal ejemplo).
