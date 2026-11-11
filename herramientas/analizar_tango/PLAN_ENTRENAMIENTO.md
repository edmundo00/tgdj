# Plan: enseñar al analizador de tangos, como se enseña a Kraken

*Escrito el 11-11-2026. Es solo un plan: no cambia nada del programa.*

## La idea en una frase

Con Kraken se hace así: unas cuantas páginas bien transcritas → se entrena → el modelo lee páginas nuevas → se corrigen sus fallos → se vuelve a entrenar con lo corregido. Con los tangos se puede hacer lo mismo en **dos de las tres cosas** que se piden (el pulso con el 1, y los golpes). En la tercera (separar bandoneón de violín) hoy **no es realista** con los medios de casa; abajo se explica por qué y qué se puede hacer en su lugar.

## Qué hay ahora (para saber de dónde partimos)

| Paso | Cómo lo hace hoy | Archivo |
|---|---|---|
| Separar instrumentos | BS-Roformer-SW (6 pistas, ya entrenado por otros). «Resto» se parte en marcato y ligado por cómo suenan (HPSS), no por instrumento. | `separar.py` |
| Pulso | librosa sobre mezcla + contrabajo, muy rígido; luego se ajusta a los golpes. | `pulso.py` |
| Dónde está el 1 | Reglas: el tiempo donde más cambia la armonía y más suena. | `pulso.py` (`donde_esta_el_1`) |
| Golpes | Reglas: subida de volumen (contrabajo, marcato) o flujo espectral (piano), con umbrales fijos. | `golpes.py` |
| Comprobar | MIDI o partitura alineada con la grabación. | `comprobar_con_midi.py` |

Lo único «aprendido» es el separador. Pulso, 1 y golpes son **reglas con números puestos a mano** (6 dB, 7 dB, 0,03…). Las reglas tienen un techo: cuando un tango se sale de lo normal (introducción libre, pianito suelto, final con rallentando, grabación con poco grave) fallan, y no aprenden de sus errores. Un modelo entrenado sí aprende, si se le dan ejemplos corregidos.

## Recomendación: el orden a seguir

1. **Paso 0 — Medir antes de entrenar** (0 h tuyas, ~1 h de máquina). Probar «Beat This!» *tal cual viene* en los tangos ya analizados y compararlo con el pulso actual. Quizá ya acierte más sin entrenar nada.
2. **Paso 1 — Modo «anotar» en el visor** (trabajo de programación, no tuyo). Sin esto no hay forma cómoda de dar ejemplos.
3. **Paso 2 — Pulso y el 1**: marcar el 1 en ~20 tangos (5 para examinar, 15 para enseñar) y ajustar Beat This! a D'Arienzo. **≈ 4–6 h tuyas**, unas horas de CPU. Es lo que más rinde por hora de trabajo.
4. **Paso 3 — Golpes**: un clasificador pequeño que diga si cada golpe candidato es de verdad y de qué instrumento, entrenado con tus «sí / no» en el visor, por rondas. **≈ 6–10 h tuyas** repartidas en 3–4 rondas, minutos de CPU.
5. **Paso 4 — En vez de separar bandoneón y violín: decir quién lleva la melodía en cada compás** (bandoneones / violines / piano / todos). Se anota por tramos, no nota a nota. **≈ 3–5 h tuyas**, minutos de CPU.
6. **Paso 5 (solo si algún día hay multipistas)** — afinar el separador. Necesita grabaciones con cada instrumento por separado y una GPU alquilada. Hoy no.

Todo lo de los pasos 0–4 **se entrena en tu ordenador, con la CPU**. No hace falta comprar nada ni pagar la nube.

---

## 1. Pulso y dónde está el 1

### Qué modelo

- **Beat This!** (Universidad Johannes Kepler de Linz, ISMIR 2024): encuentra pulsos y «downbeats» (el 1) a la vez, sin reglas añadidas. Código y modelos libres (licencia MIT), funciona en CPU, se instala con `pip install beat-this`. Tiene un modelo grande (78 MB) y uno **pequeño (8 MB)**, que es el bueno para ajustar en CPU.
  [Código](https://github.com/CPJKU/beat_this) · [PyPI](https://pypi.org/project/beat-this/) · [artículo](https://arxiv.org/html/2407.21658v1)
- Alternativa más ligera: la red TCN de Böck y Davies (la de madmom), con solo unos 22 000 parámetros: se entrena en minutos. [Artículo](https://www.eurasip.org/Proceedings/Eusipco/eusipco2019/Proceedings/papers/1570533824.pdf)

### ¿Funciona ajustar con pocos tangos? Sí, y hay pruebas

El caso más parecido al tuyo: Maia y colaboradores ajustaron una TCN entrenada con música occidental a **samba y candombe** (músicas rioplatenses con el 1 «raro» para un modelo occidental). Antes de ajustar, el modelo encontraba el 1 solo el 4–10 % de las veces. **Con 40 segundos anotados** subió al 61–82 %; **con 12 minutos anotados**, al 95–96 %. Y lo entrenaron «en un ordenador normal, con CPU».
[Artículo](https://ar5iv.labs.arxiv.org/html/2304.07186) · [resumen del taller LAMIR](https://lamir-workshop.github.io/lamir_hackathon/ch1_intro/few_data.html) · [póster ISMIR 2022](https://ismir2022program.ismir.net/static/posters/272.pdf)

Lo mismo se ha hecho con salsa ([Rapini y Jordanous, 2024](https://kar.kent.ac.uk/id/document/3448877)). Funciona mejor cuanto más **homogéneo** es el estilo, y D'Arienzo es de lo más homogéneo que existe. No he encontrado ningún conjunto de tangos argentinos anotados: el único «tango» en estas bases es el de baile de salón ([Ballroom](https://archives.ismir.net/ismir2013/paper/000051.pdf)), que no se parece. Habrá que anotarlos nosotros.

### Datos que hacen falta

- **5 tangos de examen**, que nunca se usan para enseñar (como las páginas de prueba en Kraken). Incluir «Loca» (tenemos la partitura de los compases 1–8) y uno con introducción rara o pianitos.
- **10–15 tangos para enseñar**, de varias épocas de D'Arienzo (1936–40, años 40, años 50–60) y con y sin cantor. Unos 30–45 minutos de música: más del doble de lo que les bastó a Maia y colaboradores.
- Qué se anota: **cada 1** (el 1 del bailarín: un compás de 4 tiempos = dos compases de 2/4 de la partitura). Los otros tres tiempos los pone el programa repartiendo y ajustando a los golpes; tú solo corriges donde se vea mal.

### Tu trabajo

- Escuchar el tango pulsando una tecla en cada 1: lo que dura el tango (3 min).
- Repasarlo con el clic del visor y corregir donde no cuadre: 5–10 min.
- **≈ 15 min por tango → 20 tangos ≈ 5 h.** Se puede repartir: 2–3 tangos al día.

### Máquina

- Tu CPU de 12 núcleos basta. Ajustar el modelo pequeño de Beat This! con 15 tangos: **calculo de 1 a 3 horas** (una tarde o una noche); la TCN, minutos. Es una estimación: el Paso 0 dirá cuánto tarda de verdad.
- Ojo: Beat This! no trae un botón de «ajustar»; trae el programa de entrenamiento completo. Habrá que escribir un guion corto que cargue el modelo pequeño y siga entrenándolo con nuestros tangos (con poca velocidad de aprendizaje y cambiando un poco tono y tempo para que no se aprenda los tangos de memoria). Es trabajo de programación de un día, no tuyo.

### Qué mejora esperar

- En «Loca» el 1 ya está bien; la mejora no se verá ahí, sino en **los tangos donde hoy falla** (todavía no sabemos cuántos son: por eso el Paso 0). Con los resultados publicados, lo razonable es esperar el **1 acertado en más del 95 % de los compases** y un pulso más pegado al golpe real en los cambios (introducciones, pianitos, finales).
- Lo que no arreglará: tangos de otra orquesta muy distinta (Pugliese, Di Sarli) necesitarán unos cuantos ejemplos suyos.

### Primeros pasos concretos

1. Instalar `beat-this` en el entorno `C:\Users\edmun\venvs\analizar_tango` y pasarlo por los 8 tangos ya analizados de `Analisis tangos`.
2. Comparar con `comprobar_con_midi.py` en «Loca» y, a oído con el clic, en los demás: ¿dónde pone cada uno el 1?
3. Si Beat This! sin entrenar ya iguala o mejora el pulso actual, sustituir `pulso.py` por él y entrenar a partir de ahí. Si no, entrenar igualmente: partir de un modelo que ya sabe de música es mejor que partir de cero (es lo que dicen todos los artículos citados).

---

## 2. Clasificar cada golpe por instrumento (y descartar los falsos)

### La idea

`golpes.py` ya encuentra golpes «candidatos». Hoy decide con un umbral fijo (≥ 6 dB, ≥ 7 dB). El plan es **bajar un poco los umbrales para que salgan más candidatos** (no perder golpes) y que un clasificador pequeño decida, para cada uno:
**contrabajo / piano / marcato de bandoneón / otra cosa (violín, voz) / falso (no hay golpe)**.

Es exactamente lo que se hace con Kraken y eScriptorium: el modelo propone, tú corriges, el modelo aprende de lo corregido, y en la siguiente ronda propone mejor y hay menos que corregir. Se llama aprendizaje activo: el programa te enseña primero **los golpes de los que está menos seguro**, que son los que más le enseñan.

### Qué mira el clasificador

Un trocito de unos 150 ms alrededor de cada golpe, en la mezcla y en cada pista separada (cuánta energía hay en graves, medios y agudos, lo rápido que sube, cuánto dura), más dónde cae en el compás. Con esto basta un modelo sencillo (por ejemplo, árboles de decisión de scikit-learn, que ya está en el entorno); si se queda corto, una red convolucional pequeña.

### Datos que hacen falta

- Unos **1 000–2 000 golpes revisados**, de 8–10 tangos. Cada tango tiene unos 90 compases del bailarín, y cada compás, entre contrabajo, piano y marcato, unos 10–20 golpes: con 3–4 tangos bien revisados ya hay más de mil.
- Importante: el tramo revisado tiene que quedar marcado como revisado. Igual que en Kraken solo se entrena con líneas corregidas, aquí lo que no has mirado no puede contar como «no hay golpe».

### Tu trabajo

- En la mayoría de los compases bastará con escuchar y pulsar «compás bien» (Intro). Donde no, un clic en la casilla equivocada y, si falta un golpe, otro clic para añadirlo.
- A media velocidad: **≈ 20–30 min por tango.** Primera ronda, 3 tangos (1,5 h); luego 3–4 rondas cortas de 1–2 tangos cada una, cada vez con menos que corregir. **Total ≈ 6–10 h**, repartidas en semanas.

### Máquina

- Entrenar: **segundos o pocos minutos** en CPU. Se puede reentrenar después de cada sesión de revisión.

### Qué mejora esperar

- Contrabajo: del 88 % de golpes encontrados (en «Loca») a **más del 95 %**, con menos golpes falsos.
- Marcato: menos «golpes» que en realidad son el arco de un violín o el ataque de una sílaba del cantor.
- Lo que **no** puede arreglar: si el separador mezcló dos instrumentos en una pista, el clasificador puede decir «esto suena más a bandoneón» mirando la mezcla, pero no inventa lo que el separador perdió.

### Primeros pasos concretos

1. Hacer que `golpes.py` guarde, además del golpe aceptado, **todos los candidatos** con sus medidas (subida en dB, flujo, energía por bandas, posición en el compás).
2. Montar el modo «anotar golpes» del visor (abajo).
3. Revisar 3 tangos, entrenar la primera versión, y medir con el tango de examen.

---

## 3. Separar bandoneón de violín

### Con franqueza: hoy no es viable con tus medios

Para enseñar a un separador hace falta audio en el que **se sepa exactamente qué suena en cada instrumento**: cada instrumento grabado aparte y luego mezclado. Para el tango de los años 40 eso no existe (se grababa todo junto, en mono, en un solo micrófono). Las opciones, una por una:

| Opción | Qué es | Problema | ¿Viable? |
|---|---|---|---|
| **Mezclas sintéticas** | Partituras MIDI tocadas con sonidos de bandoneón y violín y mezcladas a mano, como el conjunto Slakh ([artículo](https://arxiv.org/pdf/1909.08494)). | No tenemos las partituras de D'Arienzo (son de pago). Bandoneón gratis solo hay una SoundFont de aficionado ([foro de MuseScore](https://musescore.org/en/node/151276)); las buenas son de pago ([PSound, 89 $](https://bigbearsound.com/products/psound-bandoneon-virtual-instrument)). Y el sonido sintético está muy lejos de una grabación de 1940: el propio artículo de Slakh reconoce que sus mezclas no son realistas. | **No**: mucho trabajo para un resultado dudoso. |
| **Multipistas de orquestas actuales** | Pedir a una orquesta típica actual (Los Reyes del Tango, Sexteto Milonguero, etc.) las pistas de estudio de algunas grabaciones. | Depende de que quieran dártelas. Suenan modernas, pero son tango de verdad, con fraseo de verdad. | **La única con futuro.** 10–20 temas bastarían para un primer intento. |
| **Conjuntos públicos con bandoneón** | — | No he encontrado ninguno con bandoneón aislado. Los de notas sueltas (TinySOL, OrchideaSOL) traen acordeón, no bandoneón ([TinySOL](https://zenodo.org/record/3632193)). | **No.** |

Y aunque hubiera datos, **ajustar BS-Roformer no se hace en CPU**. El programa de referencia para entrenarlo ([Music-Source-Separation-Training de ZFTurbo](https://context7.com/zfturbo/music-source-separation-training)) necesita una GPU NVIDIA con mucha memoria. Hay un artículo de 2026 de la misma universidad de Linz que amplía un BS-Roformer de 4 a 8 pistas ajustando solo una parte pequeña del modelo (LoRA), que es justo la técnica que habría que usar ([artículo](https://arxiv.org/html/2603.04032)). Eso se haría alquilando una GPU (abajo los precios): unas **20–60 horas de GPU, 10–40 €**. El dinero es poco; lo caro son las semanas de preparación y que el resultado no está garantizado.

### Lo que sí se puede hacer ya: decir quién lleva la melodía

En vez de separar el sonido, **etiquetar el tiempo**: en cada compás, ¿quién lleva la voz cantante? (bandoneones / violines / piano / tutti / cantor). Un bailarín y un DJ lo oyen enseguida, y es lo que de verdad interesa para las publicaciones («aquí entran los violines», «variación de bandoneones»).

- **Datos**: marcar tramos en 10–15 tangos («del compás 33 al 48, violines»). Un tango tiene 6–10 tramos.
- **Tu trabajo**: ≈ 10–15 min por tango → **3–5 h**.
- **Máquina**: minutos en CPU (un clasificador del timbre de la pista «resto», compás a compás).
- **Mejora**: la fila «Ligado» podría decir «violines» o «bandoneones» con bastante seguridad cuando uno de los dos lleva claramente la melodía. Cuando tocan juntos al unísono, seguirá diciendo «los dos», que es la verdad.

---

## La máquina: CPU, tu RX 6600 y la nube

- **CPU de 12 núcleos**: basta para los pasos 0–4. Es la recomendación.
- **AMD RX 6600 en Windows**: hoy **no sirve** para entrenar sin pelearse.
  - El PyTorch oficial de AMD para Windows (ROCm) solo admite las Radeon 7000 y 9000; la RX 6600 (serie 6000) no está ([notas de AMD](https://www.amd.com/en/resources/support-articles/release-notes/RN-AMDGPU-WINDOWS-PYTORCH-7-2.html), [anuncio](https://www.amd.com/en/blogs/2025/the-road-to-rocm-on-radeon-for-windows-and-linux.html)). Hay un proyecto de aficionados que dice que «debería funcionar», sin probarlo ([RCOm-windows-gfx1030](https://github.com/ssubedir/RCOm-windows-gfx1030)).
  - DirectML (la otra vía en Windows) no saca versión nueva desde septiembre de 2024: parece abandonada ([torch-directml en PyPI](https://pypi.org/project/torch-directml)).
  - Con Linux instalado aparte y ROCm suele funcionar «engañando» al driver para que la tome por una RX 6800. Es posible, pero es un trabajo de días, y con 8 GB de memoria tampoco alcanzaría para ajustar BS-Roformer.
- **Nube**: una RTX 4090 alquilada cuesta unos **0,35–0,70 $ la hora** (RunPod, Vast.ai; precios de terceros de 2026, cambian a menudo) ([comparativa](https://findstack.com/resources/runpod-vs-vast-ai), [otra](https://www.spheron.network/blog/runpod-vs-vastai-2026/)). Solo tendría sentido para el Paso 5. Para los pasos 1–4 sería pagar por algo que la CPU hace en una tarde.

---

## Cómo añadir al visor un modo «anotar» (descripción, sin implementar)

### Qué se ve

Un botón **«Anotar»** junto a «Escuchar». Al pulsarlo, el visor cambia de color de fondo (para no confundirlo con el modo de escuchar) y aparece una línea de estado: *«Anotando · 1 marcados: 42 · golpes revisados: compases 1–17 · guardado hace 5 s»*.

### Marcar el 1 (pulso)

- Con el tango sonando (100 % o 75 %), pulsas **la tecla `1`** (o `J`) cada vez que llega un 1. Se guarda el instante.
- **Corrección del retraso de la mano**: antes de empezar, una prueba de 10 segundos con un clic regular («pulsa con el clic») mide cuántos milisegundos te retrasas o te adelantas, y se descuenta. Además, cada pulsación se ajusta al golpe fuerte más cercano (±60 ms), igual que hace hoy `pulso.py`.
- Lo que marcas se pinta encima de la rejilla: una raya verde donde tú pusiste el 1, y en rojo los compases donde el programa no está de acuerdo. Así se ve de un vistazo dónde se equivoca.
- **Retroceso** borra el último 1 marcado; **Mayús+`1`** sobre un compás dice «aquí no hay compás» (introducción libre, calderón).

### Confirmar o rechazar golpes

- **Clic en una casilla con golpe**: pasa por ✓ (bien) → ✗ (no hay golpe) → «es de otro instrumento» (aparece un menú: contrabajo, piano, marcato, violín, voz).
- **Clic en una casilla vacía**: «aquí falta un golpe». Se guarda el centro de la casilla y luego el programa lo ajusta al ataque real más cercano.
- **Intro**: «este compás está revisado»: todo lo que no has tocado se da por bueno y pasa al compás siguiente. Es lo que harás en la mayoría.
- Con «Repetir 1 compás» y velocidad al 50 %, cada compás se escucha las veces que haga falta.
- Las casillas revisadas llevan un borde fino, para saber qué está hecho.
- **Orden inteligente** (a partir de la segunda ronda): un botón «Lo más dudoso primero» salta a los compases donde el clasificador está menos seguro.

### Marcar quién lleva la melodía (para el Paso 4)

- Teclas **B** (bandoneones), **V** (violines), **P** (piano), **T** (tutti), **C** (cantor): marcan desde el compás actual hasta que se pulse otra.

### Cómo se guarda

El visor es un `.html` que se abre sin servidor, y un navegador no puede escribir archivos donde quiera. Dos maneras:

1. **La sencilla**: se guarda solo, cada pocos segundos, en la memoria del navegador (para no perder nada si se cierra), y un botón **«Guardar anotaciones»** descarga el archivo `anotaciones.json`. Luego hay que moverlo a la carpeta del tango (`Analisis tangos\_datos\<tango>\`), o un pequeño programa lo recoge de Descargas.
2. **La cómoda** (Chrome y Edge): el visor pide permiso una vez para la carpeta `Analisis tangos` y desde entonces escribe directamente `anotaciones.json` en la carpeta de cada tango. Es la que recomiendo, con la 1 como reserva.

### Qué hay dentro del archivo

```json
{
  "tango": "Juan D'arienzo - Loca 69681_rp",
  "analisis_de": "2026-11-11",          // con qué versión del análisis se anotó
  "retraso_mano_ms": 35,
  "unos": [10.42, 12.31, 14.20],         // segundos de cada 1 que marcaste
  "sin_compas": [[0.0, 9.8]],            // tramos sin compás (introducción libre)
  "golpes": [
    {"seg": 10.43, "propuesto": "contrabajo", "veredicto": "bien"},
    {"seg": 10.71, "propuesto": "marcato",    "veredicto": "falso"},
    {"seg": 11.05, "propuesto": "marcato",    "veredicto": "violines"},
    {"seg": 11.20, "propuesto": null,         "veredicto": "piano"}   // golpe añadido
  ],
  "compases_revisados": [[1, 17]],       // solo esto cuenta para entrenar
  "melodia": [{"desde": 1, "hasta": 16, "quien": "bandoneones"}]
}
```

Los entrenadores (uno para el pulso, otro para los golpes, otro para la melodía) leen todos los `anotaciones.json` que encuentren en `Analisis tangos`. Como en Kraken: cuantas más páginas corregidas, mejor modelo, sin hacer nada más.

Nota: otra sesión está cambiando ahora el código del analizador y del visor. Este modo conviene construirlo **cuando esa sesión termine**, para no pisarse.

---

## Resumen de costes

| Paso | Tus horas | Máquina | Dinero | Mejora esperada |
|---|---|---|---|---|
| 0. Probar Beat This! tal cual | 0 (mirar resultados: 30 min) | ~1 h de CPU | 0 | Saber si el pulso de hoy es el cuello de botella |
| 1. Modo anotar en el visor | 0 (es programación) | — | 0 | Hace posible lo demás |
| 2. Pulso y 1 entrenados | ≈ 5 h (20 tangos) | 1–3 h de CPU | 0 | 1 acertado > 95 % también en tangos difíciles |
| 3. Golpes con aprendizaje activo | ≈ 6–10 h, por rondas | minutos de CPU | 0 | Contrabajo 88 % → > 95 %; menos golpes falsos |
| 4. Quién lleva la melodía | ≈ 3–5 h | minutos de CPU | 0 | Distinguir violines / bandoneones por tramos |
| 5. Afinar el separador | depende de conseguir multipistas | 20–60 h de GPU alquilada | 10–40 € + semanas de trabajo | Incierta; hoy no se recomienda |

**Total realista para los pasos 0–4: unas 15–20 horas tuyas de escuchar y marcar, repartidas en varias semanas, y nada de dinero.**

## Otras fuentes consultadas

- Aprendizaje autosupervisado para pulso con pocos ejemplos (Gagneré, Essid y Peeters, ISMIR 2024): [arXiv](https://pdf.arxiv.org/pdf/2411.04152)
- Análisis de interpretaciones de tango con herramientas informáticas (Troilo, «Mi refugio», Per Musi 2020): [artículo](https://periodicos.ufmg.br/index.php/permusi/article/view/26898)
- Anotaciones de entrenamiento de Beat This!: [beat_this_annotations](https://github.com/CPJKU/beat_this_annotations)
- BS-Roformer, artículo original: [arXiv](https://arxiv.org/pdf/2309.02612)

---

## Resultado del Paso 0 (11-11-2026): Beat This! sin entrenar

Probado con `probar_beat_this.py` en los 8 tangos analizados (modelo grande `final0`; el pequeño `small0` da casi lo mismo).

| Tango | Pulsos iguales al programa | Dónde pone Beat This! el 1 (en nuestros tiempos) | Golpes en el tiempo o la «y»: programa → Beat This! |
|---|---|---|---|
| El flete | 94 % | 100 % en nuestro 1 ✓ (comprobado con el reel) | 76 % → 83 % |
| Loca 1942 | 93 % | 100 % en nuestro 1 ✓ (comprobado con la partitura) | 71 % → 73 % |
| 9 de Julio | 95 % | 100 % en nuestro 1 | 78 % → 81 % |
| Nada más | 97 % | 98 % en nuestro **2**: uno de los dos se equivoca | 83 % → 83 % |
| Loca (Los Reyes) | 94 % | mitad en el 1, mitad en el 4: Beat This! duda (nuestro 1 cuadra con la partitura) | 72 % → 74 % |
| Aclaremos (años 50) | 66 % | 52 % en el 1, el resto repartido: los dos dudan | 62 % → 64 % |
| Cajita de música (milonga) | 54 % | repartido | 49 % → 61 % |
| Candombe oriental (milonga) | 63 % | entre el 1 y el 3 | 55 % → 57 % |

Conclusiones:
- **Los pulsos de Beat This! encajan algo mejor con los golpes en todos los tangos** (de 0 a 12 puntos más). Merece la pena usarlos en lugar de los de `pulso.py`.
- **El 1**: donde tenemos comprobación (El flete, Loca 1942) Beat This! coincide con el programa. Discrepa en «Nada más» (hay que oírlo) y duda en Los Reyes, Aclaremos y las milongas. Esto es justo lo que arreglaría el Paso 2 (ajustarlo con 1 marcados a mano).
- Nota técnica: el servidor de modelos de la Universidad de Linz usa un certificado de Let's Encrypt que este Python no reconoce; los modelos se bajaron con `curl` (verificado) a `%USERPROFILE%\.cache\torch\hub\checkpoints\`. La huella SHA-256 de `final0` coincide con la publicada en otra copia.
