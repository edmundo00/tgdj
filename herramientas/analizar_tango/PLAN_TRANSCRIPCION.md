# Plan · golpes y notas «inteligentes» (prueba con «El Huracán» de Donato)

Empezado el 18-11-2026 en el PC del trabajo. **Se sigue en el PC de casa.**

## Por qué
Los puntos de golpe de la lupa (`ritmo.html`) no valen:
- Sin separar instrumentos (99 de 112 canciones) las filas «Graves / Medios / Agudos» son franjas de sonido de la
  mezcla: unos 40 «golpes» por compás, casi todo ruido.
- Separadas (BS-RoFormer) salen unos 10 por compás, más limpios, pero en «Paciencia» los golpes por instrumento
  acertaron casi lo mismo que al azar (`Analisis tangos\_referencias\paciencia_midi\informe.txt`).
- Lo fiable: compás, el 1, el pulso (Beat This!) y la onda.

La idea: en vez de «subidas de volumen», sacar NOTAS con un modelo de transcripción (de audio a MIDI) y luego
cuadrarlas a la rejilla del compás con lo que se sabe del tango (marcato 1-2-3-4, síncopa en 4y, habanera 1·4·5·7…).

## Candidatos
- **MuScriptor** (2026, el mejor en sus propias pruebas). Licencia NO comercial; en Hugging Face hay que aceptar
  condiciones con cuenta → eso lo acepta Edmundo (Claude le abre la página en Chrome; él acepta y crea el token).
- **YourMT3+** (2024, código abierto, github mimbres/YourMT3).
- **Piano**: piano_transcription_inference (ByteDance), sobre la pista de piano separada.
- (Basic Pitch de Spotify: ligero, sobre cada pista separada.)

## La referencia para medir
- Partitura: `Partituras\pdf\coleccion\Community Tango Orchestra\Arrangements\Huracan - Donato\` (11 partes, PDF de
  Sibelius, no escaneo). Pone «Donato (30's) - Instrumental · transcr/Arr. Korey Ireland & Stephan Schellin».
  Ojo: es transcripción + arreglo (lleva flauta, viola, chelo): vale para ritmo y armonía, no nota a nota exacta.
- Grabación: `MUSICA\Dan\Edgardo Donato\Edgardo Donato y sus Muchachos 1932-1939\Edgardo Donato - El huracán.flac`
  (9-12-1932, 2:56). Hay otra copia en `MUSICA\Camilo Gatica\Juan Cambareri\...\12.Edgardo Donato - El huracán.wav`.
- Antes hubo otra referencia (MuseScore de Acevedo, de oído, solo compases 1–25): `_referencias\huracan_donato\`.

## Hecho (18-11-2026)
- Ritmo con instrumentos separados de esa grabación: `Analisis tangos\_ritmo\Edgardo Donato - El huracán\`
  (página: `ritmo.html?c=Edgardo Donato - El huracán`). Separar tardó 8 min en el PC del trabajo.
- Empezado un entorno de Python 3.11 en el PC del trabajo (`%USERPROFILE%\venvs\transcribir`, solo torch cu126):
  **Edmundo cortó la instalación**. En casa hay que hacerlo de nuevo (los entornos no van por Dropbox).
  Preguntar a Edmundo antes de instalar/bajar (varios GB) y si cortó por algo concreto.

## Hecho en casa (18-11-2026, tarde)
- Edmundo cortó la instalación del trabajo solo porque se tenía que ir a casa. En casa: permiso para bajar lo necesario.
- En casa ya había **YourMT3+** en el procesador (`%USERPROFILE%\venvs\yourmt3` + `venvs\yourmt3_code`, del 11-11).
  Al mismo entorno se le añadió **piano_transcription_inference** (modelo de 172 MB en `%USERPROFILE%\piano_transcription_inference_data`).
  **MuScriptor**: entorno nuevo `venvs\transcribir` (torch CPU + muscriptor). Edmundo aceptó las condiciones en
  Hugging Face (cuenta `edmundofraga`, token de lectura guardado con `hf auth login`); modelo large (~5 GB) en
  `%USERPROFILE%\.cache\huggingface`. Se usa con su programa (`muscriptor transcribe`): la función de Python
  `transcribe_to_midi` ya no existe en la versión instalada → `transcripcion\muscriptor_tr.py`.
- Scripts nuevos en `analizar_tango\transcripcion\`: `yourmt3.py` (python de `venvs\yourmt3`), `piano.py` (ByteDance,
  mismo entorno), `muscriptor_tr.py` (python de `venvs\transcribir`), `partitura_audiveris.py` (python de `venvs\analizar_tango`).
- Grabación usada: la de casa, `MUSICA\Edmundo\Edgardo Donato\Edgardo Donato, Félix Gutierrez - El huracán.flac`
  (3:00). Es la MISMA grabación que la del trabajo (pistas separadas iguales; estribillo cantado de 80 a 140 s).
  Análisis completo y pistas: `Analisis tangos\_datos\Edgardo Donato, Félix Gutierrez - El huracán\`.
- Está desafinada **un cuarto de semitono bajo** (−0,25 a −0,35). Antes no se corregía y la nota del bajo salía
  «la bemol» en vez de «la»: ahora `comprobar_con_midi.py` mide la afinación y la corrige sola.
- Partitura → MIDI: Audiveris 5.6.1 (instalado en `C:\Program Files\Audiveris`) + `transcripcion\partitura_audiveris.py`.
  Audiveris lee bien el ritmo, pero con estos PDF de Sibelius: no reconoce la clave de fa (lee ese pentagrama como
  si fuera de sol), lee la de sol como «sol 8va» y **no ve ningún sostenido**. El script lo arregla (`--fa`, `--sol8`,
  `--bemoles 2`, `--sostenidos F` = fa# de la sensible en sol menor). Revisado a ojo contra el PDF (compases 7–10 de
  piano, contrabajo y bandoneón: bien). Sale en `Analisis tangos\_referencias\huracan_transcripcion\partitura\`.
  Si se corta por tiempo: `-constant org.audiveris.omr.Main.sheetStepTimeOut=1200` y no tener otra cosa gastando CPU.
- `comprobar_con_midi.py` nuevo: `--alinear-con <pista>` (empareja la parte con su pista separada, nota a nota en cada
  pulso: el bajo pasa de 34 % a 43 % de notas iguales), `--tramos` (medir solo donde la partitura sigue al disco),
  `--transcripcion [instrumento=]x.mid ...` (mide los modelos) y una prueba «sin modelo» (¿la nota de la partitura
  es de las que más suenan en la pista separada?) que dice si la partitura vale para medir ese instrumento.
- La partitura de Ireland/Schellin sigue al disco de 15 a 90 s y de 135 a 180 s; en medio (estribillo cantado) no.

## Resultados (18-11-2026, noche, PC de casa)

Medido solo de 15 a 90 s y de 135 a 180 s (donde la partitura sigue al disco), cada parte emparejada con su pista
separada (`--alinear-con`). Entre paréntesis, lo mismo «al azar» (partitura corrida 5 tiempos): **si el número no
supera claramente al azar, no vale**. Columnas: ataques = % de notas de la partitura con una nota del modelo a ±70 ms;
nota = además con la misma nota (sin contar octava); cae = % de las notas del modelo que caen en un ataque de la partitura.
Medidas completas: `Analisis tangos\_referencias\huracan_transcripcion\medida_*.txt`.

**¿Vale la partitura para medir?** (sin modelo: ¿la nota escrita está entre las que más suenan en la pista separada?)
contrabajo **46 % (19 %) sí** · piano 47 % (30 %) a medias · bandoneón 1 30 % (27 %) **no** (el arreglo no sigue al disco).

| Modelo · qué escucha | Contrabajo: ataques / **nota** / cae | Piano: ataques / **nota** / cae | Bandoneón 1: nota |
|---|---|---|---|
| YourMT3+ · mezcla (todas las notas) | 67 (67) / **44 (19)** / 43 (43) | 51 (49) / **19 (14)** / 44 (44) | 7 (7) |
| YourMT3+ · mezcla, solo graves (< re3) | 42 (43) / **23 (5)** / 54 (53) | – | – |
| YourMT3+ · su pista separada | 15 (12) / 8 (4) / 42 (33) | 8 (7) / 3 (1) / 30 (27) | 2 (1) |
| piano ByteDance · mezcla | 51 (48) / 28 (18) / 59 (62) | 19 (21) / 7 (4) / 29 (31) | 3 (4) |
| piano ByteDance · pista de piano | – | 33 (33) / **11 (7)** / 36 (38) | – |
| MuScriptor large · mezcla | 58 (59) / 23 (26) / 29 (30) | 67 (67) / 26 (25) / 52 (55) | 8 (6) |
| MuScriptor large · mezcla, solo graves | 24 (23) / 8 (8) / 32 (31) | – | – |
| MuScriptor large · su pista separada | 22 (24) / 6 (8) / 26 (29) | 41 (38) / **16 (11)** / 45 (44) | 9 (6) |

(Subir el volumen de las pistas separadas, `yourmt3_alto\`, no cambia nada.)

Lo que se ve:
- **Los ataques solos no dicen nada**: en todos los modelos salen igual que al azar. En el tango casi todos los
  tiempos llevan algo, así que «hay una nota cerca» se cumple siempre. Lo que distingue es **la NOTA**.
- **Contrabajo: YourMT3+ sobre la mezcla, quedándose con los graves** → 23 % de notas iguales frente a 5 % al azar
  (226 notas en 3 min, la mitad cayendo justo en un ataque de la partitura). Es lo único claramente bueno.
- **Piano**: flojo con todos (lo mejor, YourMT3+ mezcla 19 % frente a 14 %, MuScriptor sobre la pista 16 % frente a 11 %).
  Ojo: la partitura del piano solo vale «a medias» (47 % frente a 30 %), así que parte del fallo es de la referencia.
- **Bandoneón**: no se puede medir con esta partitura.
- **YourMT3+ con pistas separadas no sirve** (casi no saca notas). Hay que darle la mezcla.
- **MuScriptor decepciona aquí**: tarda muchísimo (44 min para 3 min de mezcla en el procesador; 10–29 min por pista)
  y no supera al azar en nada salvo un poco en el piano. Motivo visible: **cuadra todas las notas a su propia rejilla
  de tempo** (está hecho para sacar partituras) y esa rejilla se va del pulso de verdad: mediana 45 ms a la corchea más
  cercana en la mezcla y 80 ms en el piano, frente a 24 ms de YourMT3+ y 31 ms de ByteDance. No tiene opción para
  sacar las notas sin cuadrar. Además, a las pistas separadas les pone instrumentos raros (guitarra, órgano, batería).

**Recomendación:** YourMT3+ sobre la mezcla (~9 min por canción en el procesador, `transcripcion\yourmt3.py`),
y de lo que saque, **fiarse solo del bajo** (notas graves). Piano y bandoneones: todavía no. MuScriptor y ByteDance: no
usarlos para esto.

## Segunda prueba del bajo y fila en la lupa (19-11-2026, mañana, PC de casa)

Con partituras de contrabajo de Community Tango Orchestra que dicen ser transcripción de un disco concreto
(pasadas a MIDI por la conversión de todas las partituras, `Partituras\convertidas\todas\...`; Audiveris 5.11 ya lee
bien la clave de fa). Medidas en `Analisis tangos\_referencias\segunda_prueba_bajo\medida_*.txt`.

| Canción | ¿La partitura vale? (sin modelo) | YourMT3+ graves: nota bien |
|---|---|---|
| El Huracán (Donato 1932) | 46 % (19 %) sí | **23 % (5 %)** |
| El Pescante (Demare-Berón 1943) | 35 % (15 %) sí | **23 % (8 %)** |
| Sentimiento gaucho (Lomuto 1942) | 18 % (16 %) **no** (el arreglo no sigue al disco) | no se puede medir |

- **Resultado igual en dos orquestas y épocas distintas**: el bajo de YourMT3+ es fiable (1 de cada 4 notas bien,
  3–5 veces más que al azar). Las notas «de más» que saca también caen en tiempos razonables.
- Trampa encontrada: «El Pescante» está desafinado a medio camino entre dos notas. Mi medidor (CQT de la pista)
  ponía la partitura medio tono abajo y YourMT3+ oía la de arriba → salía 4 % (4 %). `comprobar_con_midi.py` ahora
  prueba el modelo tal cual y ±1 semitono y se queda lo mejor (y lo mismo al azar); lo dice con «[−1 st]».
- Probado y descartado: dejar que YourMT3+ diga CUÁNDO y que la pista de contrabajo separada diga QUÉ NOTA (la que
  más suena): peor (19 % y 16 % frente a 23 %).
- `transcripcion\yourmt3.py` ahora mide la afinación del disco y la corrige antes de transcribir (en El Huracán
  salía «Sol#» por «La»).
- **Fila «Bajo (notas)» en la lupa** (`ritmo_plantilla.html`): barritas con el nombre de la nota, más arriba = más
  aguda; su botón de clic toca la nota. Datos: `_ritmo\<canción>\bajo_datos.js`, los escribe
  `transcripcion\bajo_lupa.py "<canción.flac>"` (transcribe con YourMT3+ si no se le da `--mid`; la canción tiene que
  tener ya su carpeta de `_ritmo`). Hecho con El Huracán, El Pescante y Sentimiento gaucho.

## Pasos que faltan
1. ~~Partitura a MIDI~~, ~~alinear~~, ~~transcribir con los 3 modelos~~, ~~medir~~ (hecho, arriba).
2. ~~Aviso en la lupa~~ (hecho: sin separar, los golpes ● se esconden y sale un aviso rojo; separadas, «aproximados»).
3. ~~Bajo de YourMT3+ en la lupa~~ (hecho el 19-11, arriba). Falta, si se quiere: pasarlo a todas las canciones
   con página de ritmo (~9 min cada una en el procesador), y cuadrarlo a la rejilla de semicorcheas.
4. Para piano/bandoneón haría falta una referencia mejor (una partitura que siga al disco nota a nota) antes de
   volver a probar modelos.
