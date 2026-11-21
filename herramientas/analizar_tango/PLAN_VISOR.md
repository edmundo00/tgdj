# Plan · «mega visor» de cada tango (audio + lupa + partitura + vídeo de pisadas, todo con el mismo play)

*Empezado el 19-11-2026 (PC de casa). Lo pidió Edmundo: juntar en una ventana el audio, la partitura y el vídeo
de los pasos. La base es la página de ritmo (`ritmo_plantilla.html` → `Analisis tangos\ritmo.html?c=<canción>`).*

Lo que pidió además (19-11, mientras se hacía la fase 1):
- **Un «cuadrador»** para la partitura y para los vídeos: que lo intente poner bien solo, pero que se pueda
  **arrastrar** para corregirlo a mano. El vídeo puede cuadrarse solo comparando su sonido con nuestro FLAC.
- **Que no se vea un pegote encima de otro**: cada cosa en su panel, que se pueda abrir y cerrar (vídeo, partitura)
  y **ocultar instrumentos**.

Reglas que siguen valiendo: una sola página para todas las canciones (REGLA 0b), datos por canción en un `.js` que
se carga con `<script>` (doble clic, sin servidor, sin internet), bibliotecas guardadas en local en una versión fija.

---

## Fase 1 · Partitura — HECHA (19-11-2026)

Probada con «El Huracán» (Donato), partitura general de 12 partes × 92 compases (`Partituras\convertidas\El_Huracán_general.mxl`).

**Página:** [El Huracán con partitura](file:///D:/Dropbox/TDJ/Analisis%20tangos/ritmo.html?c=Edgardo%20Donato%20-%20El%20hurac%C3%A1n)

**Visor viejo quitado (19-11-2026):** la página de ritmo es ya la única para ver una canción. `visor.html`, las gráficas,
los `datos.js`, los `escuchar.html` y las copias OGG están en `Analisis tangos\_papelera\2026-11-19_visor_viejo\`.
`analizar_tango.py` ya no los hace: separa pistas, escribe los .csv y `resumen.txt`, y al terminar lanza `ritmo.py`.

### Qué hay
- **`partitura.py`** (nuevo, `analizar_tango\`): `python partitura.py "<carpeta de _ritmo\canción>" "<x.mxl>"`.
  Lee el MusicXML (Python estándar), lo cuadra con la grabación y deja en la carpeta de la canción:
  `partitura.json` (qué partitura y las anclas), `partitura_datos.js` (el MusicXML + tabla compás → segundo, ~1,7 MB)
  y `partitura.txt` (la tabla en texto, con «coste» por compás y si suena la nota del bajo).
  `--ancla 5=17.52` (varias), `--sin-anclas`, `--todas` (rehace todas las que tengan `partitura.json`).
  `ritmo.py` la rehace sola al volver a analizar una canción que tenga `partitura.json`.
- **Cómo cuadra** (explicado arriba del todo en `partitura.py`): rejilla de pulsos de ritmo.py arreglada (rellena
  donde Beat This! cuenta a medio tiempo y la alarga al principio y al final) → coste tiempo a tiempo (notas que
  empiezan en cada negra de la partitura contra lo que suena al empezar cada pulso, en la mezcla y en las pistas
  separadas de contrabajo y piano, como `comprobar_con_midi.py --alinear-con`) → **compás a compás**: cada compás
  empieza en un pulso y paga por cada tiempo de más o de menos (`PENAL = 0.35`). Las anclas obligan.
  Probado antes el emparejamiento libre (DTW, por segundos y por pulsos): daba compases de 0,9 a 3,7 s, inservible.
  Si la partitura está escrita al doble o a la mitad del pulso, lo detecta solo.
- **`ritmo_plantilla.html`**: carga `_ritmo/<canción>/partitura_datos.js` si existe; si no, no cambia nada.
  - Panel plegado **«Partitura»** debajo de la lupa (solo si hay partitura). **Rapidez** (arreglado el 19-11, Edmundo
    se quejó de lo que tardaba): lo lento no era Verovio (leer 2,5 s + dibujar 1,5 s) sino que el navegador pintara la
    partitura entera de golpe (54.000 piezas de SVG: ~19 s al abrir el panel). Ahora (1) la página carga Verovio y la
    dibuja **de antemano**, a los 2,5 s de abrirla y solo mientras no suena nada, y (2) la partitura va **por páginas**:
    cada página es un hueco de su tamaño y solo se rellenan las que están a la vista o cerca (IntersectionObserver);
    abrir el panel tarda 0,1 s. `probar_ritmo.py` falla si abrir tarda más de 5 s.
  - Compás que suena en **amarillo** con una aguja que avanza dentro del compás; la partitura **se mueve sola**
    («sigue la música»). Funciona a 100/75/60/50/25 %, con «repetir el trozo» y con ← → (lo que se ve en la lupa
    sale sombreado en la partitura y la partitura va ahí).
  - **Clic en un compás** = el audio va ahí. **Mayús + clic** = elige el trozo entre el compás marcado y ese.
  - **Partes**: Todas / Bandoneones / Piano / Contrabajo / Cuerdas / Otros (se suman; se recuerda en el navegador).
    En el móvil empieza solo con bandoneones, piano y contrabajo, y los nombres van cortos (Bn 1, Pno, Cb).
  - **Tamaño** A− / A+.
  - La barra de arriba dice también el compás de la partitura («compás 12 · partitura 21»).
  - **El cuadrador**: en la lupa salen rayas azules «P21» = dónde empieza cada compás de la partitura.
    **Se arrastran** con el ratón o el dedo hasta donde de verdad empieza el compás → «ancla» (⚓). También:
    clic en un compás de la partitura y pulsar «El compás marcado empieza aquí» (o la tecla A) al oírlo.
    Entre dos anclas el resto se reparte en línea recta; se ve al momento y se guarda en el navegador.
    Para que valga siempre: el texto `ANCLAS 5=17.520 …` (y la orden de `partitura.py`) que sale en el panel →
    Edmundo lo pega en el chat → `python partitura.py "<carpeta>" --ancla … ` (vuelve a cuadrar con esas anclas).
  - **Filas** de la lupa: botones con el nombre de cada instrumento arriba de la lupa para ocultarlas o enseñarlas.
  - **〰 ondas** (pedido por Edmundo el 19-11): detrás de los puntos de cada fila, la onda de su pista separada
    (escala de toda la canción: se ve quién suena fuerte y quién calla). Fila nueva **«Voz»** (pista `voz.flac`, solo
    onda, sin golpes ni clics): `pagina_ritmo.pistas_de` la mete en el `ritmo_datos.js` si existe.
    Pendiente si Edmundo quiere: separar la fila «bandoneones» (hoy es la pista «resto», con violines) en
    bandoneones y violines (están en `_datos\<canción>\pistas\`).
- **Verovio 4.3.1** (`lib\verovio-toolkit-wasm.js`, 7,4 MB, todo en un archivo; bajado de jsdelivr el 19-11-2026).
  `pagina_ritmo.py` lo copia a `Analisis tangos\lib\`. Verovio numera mal los compases de estas partituras (empezaba
  en 19): la página pone encima los números escritos.
- **`probar_ritmo.py`** comprueba también la partitura si la hay (se dibuja, nº de compases, compás marcado = el que
  suena a 100 % y a 60 %, clic, repetir el trozo, ← →, anclas, solo piano) y, sin partitura, que el panel no salga.
  `--partitura foto.png [ancho] [compás]` = foto del panel. TODO BIEN con «El Huracán» y con 6 canciones sin partitura.
- `indice.js` lleva `partitura: true` → «𝄞 con partitura» en `HERRAMIENTAS.html` y en la lista de la página.

**Arreglado el 19-11-2026:** Verovio desordenaba los compases de «El Huracán» (ponía los 18 primeros al final) por unas
casillas de 1.ª/2.ª vez mal cerradas en los compases 83–84: la marca amarilla iba corrida aunque el cuadre estuviera bien.
`xmlConPartes()` quita los `<ending>` antes de dibujar; `probar_ritmo.py` compara las notas de cada compás dibujado con
las del archivo. Ancla de Edmundo: compás 7 (empieza el tema, tras 6 de introducción) = 17,3 s.

### Lo que no está bien todavía (fase 1)
- **El cuadre de «El Huracán» no está comprobado de oído.** Medida de la máquina: del compás 60 al 92 la nota del
  bajo escrita suena 25/45 veces (corrida 2 o 4 tiempos, 12–16/45) → ahí cuadra. Del 1 al 60 el bajo no coincide en ningún
  desplazamiento: o la parte de contrabajo está mal leída ahí (Audiveris no reconoce la clave de fa: puede tener
  notas cambiadas en algunas líneas) o el cuadre va corrido. Al principio la grabación tiene ~13 s de introducción
  (1,5–15 s) sin contrabajo y Beat This! no da pulsos hasta el 16,8: ahí la partitura sigue un pulso inventado.
  → **Edmundo: escuchar el principio y poner 2–3 anclas** (p. ej. dónde empieza de verdad el compás 5, el 30 y el 60).
- La partitura de Audiveris trae corchetes «1» (casillas de repetición) que no son de verdad, y pentagramas de
  clave de fa vacíos en los bandoneones. Son de la conversión, no de la página.
- Si una partitura tiene **repeticiones** (𝄆 𝄇, casillas), hoy se lee de corrido (sin repetir). Falta: desplegarlas
  en `leer_partitura` (y en la página, dibujar una vez y saltar). «El Huracán» no tiene.

## Fase 2 · Vídeo de pisadas — HECHA (19-11-2026)

Probada con «Nueve puntos» (Di Sarli 1956, London & Sol, 22 pisadas):
[página](file:///D:/Dropbox/TDJ/Analisis%20tangos/ritmo.html?c=21.Francisco%20Canaro%20-%20Nueve%20puntos%20%2807-03-1956%29)

- **`video.py`** (`analizar_tango\`): `python video.py "<carpeta _ritmo\canción>" "<vídeo.mp4 | carpeta marcar_…>"
  [--id x] [--bailarines "Sol:follower,London:leader"] [--inicio s] [--pisadas f]`. Con carpeta `marcar_…` usa su
  `config.json` (ya alineado) y su `pisadas.txt`/`.json`; con un vídeo suelto lo alinea con `bailarines\alinear.py`.
  Deja `video_<id>.mp4` (copia ligera: 720 px, sin sonido, fotograma clave cada 10 → saltar es instantáneo; ~6 MB
  por 17 s), `video.json` y `video_datos.js` (`window.VIDEO`, pisadas ya en segundos de la grabación). Varios vídeos
  por canción. Sin vídeo: `video.py "<carpeta>"` rehace el .js (p. ej. pisadas nuevas); `--id x --inicio s` corrige el
  cuadre (el texto «VIDEO x inicio=…» de la página); `--quitar x`; `--todas`. `indice.js` lleva `video: true` (🎬).
- **Página**: botón «🎬 Vídeo» en la barra (tecla V; se recuerda). El vídeo va **a la derecha** (es vertical), fijo
  bajo la barra y tan alto como la pantalla (a 1900 × 950: 411 × 731 px; la lupa y la partitura se estrechan, no se
  montan); en pantallas de menos de 900 px, encima de la lupa. Sigue a `ahora()`: parado = su fotograma; sonando, se
  corrige con `playbackRate` (±12 %) y solo salta si se va más de 0,3 s. Medido: se separa 4–6 ms al 100 % y al 60 %.
  Fuera del vídeo: «El vídeo empieza en el compás N · clic aquí para ir». Clic en el vídeo = escuchar/parar.
  **Cuadrador**: ⚓ −50 ms / −1 fot. / +1 fot. / +50 ms bajo el vídeo, o arrastrar en la lupa la raya morada
  «▶ vídeo» / «vídeo ◀» (en la tira de arriba); ↺ = volver al de la máquina; se guarda en el navegador y sale el texto
  `VIDEO <id> inicio=…`. En la franja de la canción entera, una raya morada = lo que cubre el vídeo.
  **Pisadas**: una fila «👣 <nombre>» por bailarín al final de la lupa (I arriba, D abajo; aro = adorno; color de su
  papel); su 🔔 = un clic en cada pisada (agudo ella, grave él); se ocultan como cualquier fila.
- `probar_ritmo.py` → `probar_video()`: carga, tamaño y que no se monte con la lupa, fotograma parado, desvío al 100 % y
  60 % (falla si pasa de 80 ms), aviso fuera, ⚓ y ↺, filas 👣, ✕ y 🎬. Sin vídeo, que no salga nada.
- **Subir un vídeo desde la página** (Edmundo: «¿no puedo simplemente subir un vídeo y analizar?»): «🎬 Vídeo» sale
  en todas las canciones; sin vídeo, abre el elegidor de archivos (y ＋ añade otro). `cuadraVideo()` hace en el navegador
  lo de `alinear.py`: envolvente de subidas de volumen (graves/medios/agudos, 10 ms), sin el primer medio segundo y
  con tope en el 1 % más fuerte (si no, el arranque de silencio a música del vídeo «encajaba» con el principio del
  disco), correlación normalizada en toda la canción y luego velocidades 0,94–1,06 a ±1,5 s. «Nueve puntos»: 53,707 s
  (bueno: 53,696) en ~3 s, seguridad 9,1; en otra canción 4,1 (< 6 pregunta). Se guarda en IndexedDB (`tdj_videos`,
  con el archivo), así que solo en ese navegador; 🗑 lo quita. `probar_ritmo.py --subir x.mp4 [segundo]` lo prueba.
- No hecho: «vídeo flotante» (no hace falta: el vídeo ya está siempre a la vista a la derecha).

Plan original:

Para los tangos con una carpeta `marcar_<vídeo>\` (ejemplo `Instagram\borradores\nueve-puntos-seoul\fuente\`;
herramienta en `analizar_tango\bailarines\`, leer su `INSTRUCCIONES.md`).

1. **Cuadrar solo**: ya existe `bailarines\alinear.py` (correlación de golpes y croma probando velocidades
   0,94–1,06 → segundo de la grabación donde empieza el vídeo y velocidad). `marcar_pisadas.py` lo guarda en
   `config.json`/`alineado.json` de la carpeta. Reutilizarlo: nuevo `video.py "<carpeta _ritmo\canción>" "<vídeo o carpeta marcar_…>"`
   que deja `_ritmo\<canción>\video.json` (vídeo, desfase, velocidad, pisadas) y `video_datos.js` (solo datos; el
   vídeo NO va dentro del .js: es grande; se enlaza con ruta relativa `<video src="../../Instagram/...mp4">`, que sí
   funciona con doble clic). Si el vídeo no está en Dropbox, copiarlo a `_ritmo\<canción>\video.mp4` (720p, sin audio).
2. **Página**: panel plegado **«Vídeo»** (como «Partitura»): `<video muted>` que sigue a `ahora()`:
   `currentTime = (t − desfase) / velocidad`, corrigiendo solo si se va más de 60 ms (si no, da tirones);
   a velocidades lentas, `playbackRate` igual que el audio. Fuera del trozo que cubre el vídeo: fotograma gris
   «el vídeo empieza en el compás N». Clic en el vídeo = play/parar.
3. **El cuadrador del vídeo**: botones −1 fotograma / +1 fotograma y −50/+50 ms, y una raya «V» en la lupa
   (como las «P» de la partitura) que se arrastra; texto `VIDEO desfase=…` para pasárselo a Claude.
4. **Pisadas en la lupa**: una fila más por bailarín (los puntos de `pisadas.txt`), ocultable con «Filas».
5. **Que no se monte todo**: en escritorio ancho, vídeo y partitura lado a lado (rejilla de 2 columnas) cuando los
   dos están abiertos; en el móvil, uno debajo de otro. Opción «vídeo flotante» (pequeño, en una esquina) para
   ver a la vez la lupa.
6. `probar_ritmo.py`: con vídeo, comprobar que `video.currentTime` va con el audio (±80 ms) a 100 % y 60 %.

## Fase 3 · Ideas para después
- Cuadrador de la partitura en Python mejor: usar el bajo de YourMT3+ (ver `PLAN_TRANSCRIPCION.md`) además del croma.
- Elegir la partitura desde la página (lista de `Partituras\convertidas\` con el mismo título) en vez de pedirlo a Claude.
- Colorear en la partitura las notas que la máquina oye (golpes de la pista separada) para ver dónde no sigue al disco.
