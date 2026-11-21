# Página de ritmo · auditoría y rediseño (19-11-2026)

Edmundo: «es imposible hacer nada». Lo que necesita, por orden:
1. **Moverse por la canción**: saltar a cualquier sitio, ir a un compás concreto, un compás atrás/adelante mientras suena.
2. **Repetir un trozo** eligiendo los compases (de 5 a 8), sin tener que arrastrar.
3. **Ver la partitura y la lupa a la vez que el play**, sin subir y bajar.
4. **Que quepa en la pantalla**: hoy la lupa con 2 compases mide 530 px y la página entera 2.150 px.
5. **Entender cada botón**: hay 60 controles; varios heredados que nadie usa o que no se entienden.

## Auditoría: lo que hay hoy (de arriba abajo, en escritorio a 1300 px)

| Zona | Alto | Qué tiene | Problema |
|---|---|---|---|
| Cabecera | 90 | título, 5 etiquetas (compás, pulsos, el 1, binaria, golpes de), «Herramientas», elegir canción | ocupa mucho para información que casi no se mira |
| Barra fija | 70 | Escuchar, tiempo/compás, velocidad (5 botones), repetir el trozo | **no hay barra de la canción**: no se puede saltar; repetir depende de un trozo que se elige en otro sitio |
| Panel «Clic en / Comprobar» | 85 | clic en contrabajo/piano/bandoneones/bajo, metrónomo, tresillo/corcheas/semicorcheas | se usa poco y está fijo arriba |
| Cabecera de la lupa | 120 | ◀ ▶, «compás 66–67», se ven 1/2/4/8, casillas (3), golpes, cambios de nota, ondas, compases de la partitura, filas (5) | 2 líneas de interruptores; **◀ ▶ mueven la vista, no lo que suena** (confunde) |
| Aviso de golpes | 35 | «golpes aproximados…» | siempre ahí |
| Lupa | 530 | fila «onda graves» (90) + 5 filas de 78 | la fila «onda graves» repite lo que ya enseña la onda de cada fila; filas vacías (piano y voz casi siempre); todo muy alto: tapa lo de debajo |
| Leyenda | 25 | qué es cada marca | |
| Partitura | 850 | partes, tamaño, sigue la música, ayuda, partitura, cuadrar (texto largo + 2 botones) | **está debajo de la lupa**: para verla se pierde el play y la lupa |
| Canción entera | 110 | onda de toda la canción con números de compás | **es la única forma de saltar y está a 1.900 px de altura** |
| Dibujos encontrados | 70 | milonga 1-4-5-7, etc. | |
| Más herramientas (plegado) | — | **volumen de cada pista (oír un instrumento solo)**, la lupa sigue la música, onda por bandas (graves/medios/agudos/Hz), trozo para vídeo (±ms, guardar), «aquí suena un 1» | lo útil (oír un instrumento solo) está escondido entre lo raro |
| ¿Cómo se usa? (plegado) | — | | |

Heredado o raro: dos `<select>` escondidos (`ncomp`, `rejilla`) que mandan sobre los botones (solo por las pruebas);
onda por bandas en Hz; mover el trozo ±1…50 ms; «la lupa sigue la música» escondido; el aviso de golpes; tres sitios
distintos para elegir un trozo (lupa, partitura con Mayús, canción entera) y ninguno con números.

## Propuesta

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐ barra fija
│ ▶  ⏮ ⏭   compás [ 22 ] de 92 · 1:17,8    velocidad [100 ▾]   🔁 de [ 5 ] a [ 8 ]  ☐ repetir   │  (≈ 90 px)
│ ▁▂▃▅▃▂▁▂▃▅▇▅▃ 1 · 5 · 9 · 13 … ▏(onda de toda la canción: clic = saltar, arrastrar = trozo)  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Ver: [Lupa] [Partitura] [Las dos]                se ven [1 2 4 8] compases   ⚙ ver…           │
│ ┌──────────┬───────────────────────────────────────────────────────────────────────────────┐ │
│ │Contrabajo│ ◆ ● onda                                                                       │ │  lupa: filas
│ │ 🎧 🔔     │                                                                                │ │  de 44 px,
│ │Bandoneón │                                                                                │ │  sin la fila
│ │Bajo notas│                                                                                │ │  «onda graves»
│ └──────────┴───────────────────────────────────────────────────────────────────────────────┘ │
│ ┌ partitura (lo que queda de pantalla; sigue a la música) ───────────────────────────────────┐ │
│ └────────────────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
▸ Herramientas (plegadas): comprobar tresillo/corcheas · dibujos · cuadrar la partitura · corregir el 1 · trozo para vídeo
```

1. **Reproductor de verdad en la barra fija** (siempre a la vista):
   - Onda de toda la canción con los números de compás: clic = saltar ahí (sonando o no); arrastrar = elegir trozo.
   - ⏮ ⏭ = un compás atrás/adelante **de lo que suena** (y la lupa lo sigue). Teclas ← →.
   - «compás [22]»: se escribe un número y Intro = ir a ese compás.
   - «de [5] a [8]» + repetir: el trozo con números de compás. Arrastrar en la lupa, la partitura o la onda rellena
     esos números, y al revés. Tecla R = repetir sí/no.
   - Velocidad en un desplegable corto (sigue con ↑ ↓).
2. **Una sola zona de trabajo que cabe en la pantalla**, con «Ver: Lupa / Partitura / Las dos» (solo si hay partitura).
   En «Las dos», la lupa compacta arriba y la partitura debajo, sin pasar del alto de la pantalla. En el móvil, una u otra.
3. **Lupa compacta**: filas de ~44 px (se pueden agrandar), sin la fila «onda graves» (cada fila ya tiene su onda),
   y las filas sin nada se ocultan solas. En el nombre de cada fila: 🎧 = oír ese instrumento solo y 🔔 = clic en
   sus golpes (sustituye al panel «Clic en» y a los volúmenes escondidos).
4. **Un solo botón «⚙ ver…»** con lo que se enciende o apaga: golpes, cambios de nota, ondas, casillas
   (semicorcheas/corcheas/tresillos), rayas de la partitura, qué filas. Se quita la segunda línea de interruptores.
5. **Abajo, plegado, «Herramientas»**: comprobar tresillo/corcheas con metrónomo, dibujos encontrados, cuadrar la
   partitura (anclas), corregir el 1 o el compás, trozo para vídeo. La onda por bandas en Hz se quita (nadie la usa).
6. **Cabecera de una línea**: título, elegir canción y un «ⓘ» con compás, pulsos, el 1, etc.
7. **Por dentro**: fuera los `<select>` escondidos; un solo «estado» (dónde suena, trozo, vista) que leen todas las
   partes; probar_ritmo.py se cambia a la vez y se le añaden pruebas de saltar, ⏮ ⏭, ir a compás N y repetir de N a M.

### Fases (cada una se prueba con probar_ritmo.py y fotos en escritorio y móvil antes de pasar a la siguiente)
- **A · Reproductor**: barra fija con la canción entera, ⏮ ⏭, ir a compás, repetir de N a M. (Lo más urgente.)
  **HECHA el 19-11-2026.** `ir(t)` es el único sitio que mueve lo que suena (clic en la franja, en la lupa, en la
  partitura, ⏮ ⏭, el número de compás); salir del trozo apaga 🔁. ⏮ vuelve al principio del compás si ya lleva
  ~0,9 s dentro (a 100 %); si no, al anterior (así se puede pulsar dos veces). Las casillas «de/a» siempre dicen el
  trozo elegido (o el compás que suena si no hay trozo). La franja de la canción entera ya no está abajo.
  Además (pedido por Edmundo): cabecera de una línea (el selector de canción hace de título; ☰ solo en el móvil) y
  la página usa todo el ancho de la pantalla (`.ancho` hasta 2600 px; su pantalla es de ~1900). «repetir» no se
  recuerda al recargar (Chrome lo dejaba marcado sin trozo).
  Pruebas: `probar_reproductor()` en probar_ritmo.py. Ojo: la prueba vieja de «clics al 60 %» falla a veces sola
  (2–3 de 5) cuando el PC va cargado; repetirla antes de buscar un fallo.
- **B · Espacio**: vista Lupa / Partitura / Las dos que cabe en la pantalla, lupa compacta, ⚙ ver…, 🎧 y 🔔 por fila.
  **Primera parte HECHA el 19-11-2026** (Edmundo: «sí, hazlo»): fuera el panel «Clic en / Comprobar»; encima de la lupa
  una línea con ◀ ▶, «se ven», «🔔 Comprobar ▾» (metrónomo + tresillo/corcheas/semicorcheas) y «⚙ Ver ▾» (casillas,
  ● ◆ 〰 𝄞, filas ocultas y el aviso de golpes como ⓘ; sin pistas separadas el aviso sigue en rojo a la vista).
  Clic en el nombre de una fila (`filaEn`, `abreMenuFila`): 🎧 oír solo (`ponSolo`, pone los volúmenes de «Qué se oye»),
  🔔 clic en sus golpes (en el bajo: tocar sus notas), ocultar. En la fila salen 🎧/🔔 si están encendidos y arriba
  unos chips con todo lo encendido (`cambiaClics`); clic en un chip = apagarlo. Los `[data-rej]` siguen (pruebas).
  Prueba: `probar_menus()`.
  **Segunda parte HECHA el 19-11-2026:** en la barra fija «Ver: Lupa / Partitura / Las dos» (solo con partitura;
  se recuerda en el navegador; de entrada «Las dos» en el escritorio y «Lupa» en el móvil). `ponVista`/`ajustaVista`:
  en «Las dos» la partitura se queda con el alto que deja la lupa (a 1900 × 950 cabe todo sin bajar) y se esconden la
  leyenda, la ayuda y el título de la partitura (`body[data-vista]`). Lupa compacta: filas de 50 px (44 en el móvil;
  «filas altas» en ⚙ Ver = las de antes), la «onda graves» apagada (⚙ Ver «onda de graves arriba»; los botones de banda
  de «Más herramientas» la encienden); si hay partitura queda una tira fina de 22 px para las rayas «P…» (se agarran ahí
  o en la de los números). La lupa escondida no se pinta. Prueba: `probar_vistas()` (pone la ventana a 1900 × 950).
  No hecho: ocultar solas las filas vacías (el piano o la voz están vacíos en unos compases y en otros no).
- **C · Limpieza**: herramientas plegadas, cabecera de una línea, fuera lo heredado, ayuda al día.
  **HECHA el 19-11-2026.** Abajo, un solo `<details id="herramientas">` plegado: dibujos encontrados, volumen de cada
  pista (los sliders; 🎧 de la fila los pone al día), cuadrar la partitura (`#caja_cuadrar`, solo con partitura; el botón
  «⚓ cuadrar…» de la partitura abre y lleva ahí), si el compás o el 1 están mal, trozo para vídeo (±10/50 ms).
  Quitados: el panel suelto de dibujos, «Más herramientas», la onda por Hz (`lo`/`hi`/`banda_de` → `BANDA`), los
  `<select>` `ncomp`/`rejilla` (→ `NCOMP`/`SUB`), la leyenda de debajo de la lupa (está en «¿Cómo se usa?», reescrita).
  «la lupa sigue la música» pasó a ⚙ Ver. Móvil: los datos de la cabecera detrás de una ⓘ.
  De paso: fila «Voz» fuera en los 11 tangos instrumentales (su pista era silencio y en opus salía un zumbido en sierra);
  Edge de las pruebas con `--mute-audio` (Edmundo oía la música de las pruebas).
- **D · Las 20 mejoras** (Edmundo: «todo», 19-11-2026). **HECHAS el mismo día.**
  Compacto: (1) filas sin nada que enseñar = raya fina «vacía» (`vacia()`, `FINA`, alturas por fila `m.altos`/`m.ys`);
  (2) aviso de golpes → pastilla «⚠ golpes no fiables»; (3) velocidad en «⏱ 100 % ▾»; (4) datos de la canción tras ⓘ
  también en el escritorio; (5) la cabecera va dentro de la barra fija (una línea); (6) «🔍 2 compases ▾»; (7) sola, la
  lupa llena la pantalla (filas de 44 a 90 px); (8) el vídeo con una sola línea arriba y lo demás en «⚓ ▾»;
  (9) elegir canción escribiendo (buscador en vez de lista); (10) móvil girado = vídeo al lado; en vertical, encima y más pequeño.
  Funciones: (11) 👣 marcar pisadas en la página (Q W O P, Z, clic = borrar, «📋 Copiar para Claude»; localStorage
  `tdj_pis:<canción>:<vídeo>`); (12) fotograma a fotograma (‹ › , .); (13) Ctrl + rueda / pellizco = compases a la vista,
  Mayús + rueda = mover; (14) arrastrar en la fila de números de la franja = mover la lupa; (15) marcas con texto (M,
  `tdj_marcas:`, texto MARCAS); (16) recuerda dónde te quedaste (`tdj_pos:`; `?compas=N` manda); (17) cuenta de entrada
  (🔔 Comprobar); (18) 🔊 sonido del vídeo en vez del disco (video.py ya copia el sonido); (19) clip para reel
  («💾 Guardar el trozo» lleva el vídeo → `clip_reel.bat`/`clip_reel.py` → `Instagram\borradores\_clips\`, 1080×1920,
  sonido del disco, a la velocidad que se escuchaba); (20) «⇄ comparar» con otra grabación (fila con su onda cuadrada
  compás a compás, «su compás = este ± n», oírla desde aquí, abrir su página en ese compás).
  Pruebas nuevas en probar_ritmo.py: marcar/deshacer/fotograma/sonido (en `probar_video`), `probar_extras` (marcas,
  cuenta de entrada, comparar, recordar posición y `?compas=`). TODO BIEN con Nueve puntos, El Huracán y Loca (D'Arienzo).
  Después (19-11, Edmundo): ⭐ estrellas en los pies sobre el vídeo (pisadas con x y; video.py ya las guarda; clic en
  el pie al marcar = su sitio), deshacer también lo borrado / «volver a las originales», y 🧲 imán al marcar (a los
  tiempos —por defecto—, a las casillas o a los golpes de sonido; ±0,15 s) con «🧲 ajustar todas».
  Y después: tocar una pisada = elegirla (barrita: ←/→ un fotograma, 🧲 1 tiempo/½/¼/tresillo, I↔D, adorno, 🗑/Supr, Esc; arrastrar = moverla); ya no se borra al tocarla.
  20-11 (Edmundo: «quiero ver el vídeo lo más grande posible para poner bien las pisadas»): al marcar, los botones van
  en una columna A LA IZQUIERDA del vídeo (cogiendo sitio de la lupa) y el vídeo llega casi al alto de la pantalla.
  Botones «I D» por bailarín con su papel (FOLLOWER / LEADER) y el nombre editable; teclas Q W / O P en pequeño.
  Lo poco usado (imantar todas, originales, copiar, retraso) en «⋯ más». Marcando, las estrellas son aros finos con la
  letra del pie (no tapan el pie); la elegida, aro con cruz abierta. Lupa ×3 con cruz al pasar el ratón por el vídeo.
  Tab / Mayús+Tab = siguiente / anterior pisada sin sitio; E = esconder marcas. Prueba en `probar_video`;
  foto: `probar_ritmo.py <carpeta> --foto-marcar x.png`.
  Y (Edmundo: «que se vean los anteriores y los de él cuando voy a marcar no ayuda»): marcando, en el vídeo solo sale
  la pisada elegida (o la recién puesta) y, muy tenue, la anterior del MISMO pie del MISMO bailarín; nada del otro.
  «⋯ más → ver todas las marcas» las enseña todas (`arosVisibles`).
  Y (Edmundo, moviola): el espacio, con un trozo elegido, sigue desde donde se paró (antes volvía al principio del
  trozo; `desdeDonde`). Con el vídeo a la vista: ← → = 1 fotograma, Mayús + flecha = ¼ de tiempo (`pasoRejilla`),
  Ctrl + flecha = un compás. Sin vídeo, las flechas como antes. Prueba «moviola» en `probar_video`.
  Y (Edmundo: «las estrellas son muy grandes, casi no se ven los pies»): al sonar, un punto de luz: SOLO 1 px opaco en el
  centro, que cae enseguida y sigue casi transparente hasta desaparecer a 32 px (degradado, sin borde; 4 px opacos
  a 16 px tampoco le gustó), del color del bailarín; se apaga en
  0,45 s (`ondaPie`; adorno = más flojo). Probados antes y descartados por Edmundo: estrella grande, aro fino,
  estrellita con punto y borde, foco «screen» que se abría (le parecía un círculo opaco que crecía).
  La lupa del pie no sale mientras suena. Foto: `probar_ritmo.py <carpeta> --foto-ondas x.png`.

- 20-11-2026 · Lupa del pie grande: era un círculo de 150 px ×3 (Edmundo: «tan pequeña y tan ampliada no veo nada»).
  Ahora cuadrada con esquinas redondas, ~64 % del ancho del vídeo (máx. 48 % del alto, entre 200 y 480 px), ×2 y nítida
  (devicePixelRatio). Va en la esquina contraria al ratón para no tapar el pie. Rueda del ratón sobre el vídeo =
  más o menos aumento (×1,25 a ×5, se recuerda en el navegador). Prueba: «lupa grande» en probar_ritmo.py.
- 20-11-2026 · La lupa del pie NO se escondía nunca: `canvas {display:block}` ganaba a `hidden`. Arreglado con `canvas[hidden]{display:none !important}`; la prueba ahora mira si se VE (offsetWidth), no la propiedad hidden. Lección: probar lo que se ve en pantalla.
