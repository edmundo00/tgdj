# Partituras → MusicXML (.mxl) + MIDI · inventario y plan  — 18-11-2026

Objetivo: que toda la música de `TDJ\Partituras\` esté en un formato que Claude pueda leer:
**MusicXML (`.mxl`) + MIDI sacado de él**, en `Partituras\convertidas\`. Para leer un `.mxl`: `resumen_mxl.py`.
(Pasar GRABACIONES a notas es otra cosa: `analizar_tango\PLAN_TRANSCRIPCION.md`.)

## Hecho

| Qué | Cuántos | Cómo | Salida |
|---|---|---|---|
| MuseScore `.mscz` | 44 | `convertir_partituras.py` (MuseScore 4, sin ventanas) | `<nombre>.mxl` + `.mid` |
| MIDI sueltos `.mid` / `.midi` | 18 (15 de `midi\`, 3 de Editorial Orquesta Típica) | el mismo script (18-11-2026) | `<nombre>_desde_midi.mxl` |
| MusicXML que ya venían | 3 (`coleccion\Partituras\amarras1.mvt1-3.mxl`) | ya se leen tal cual | — |

Los `_desde_midi.mxl` tienen el ritmo cuantizado por MuseScore (aproximado, voces del piano mezcladas, sin
dinámicas ni articulación). Valen para notas y armonía; para ritmo fino, mejor una partitura de verdad.

`resumen_mxl.py <archivo.mxl> [--compases 1-8] [--parte piano]`: título, autores, compases, tonalidad y compás
(y dónde cambian), tempo, repeticiones, indicaciones, cifrado; por parte: registro, notas y figuras más usadas,
tresillos; con `--compases`, las notas compás a compás con su tiempo (1, 1½, 2¼…). Solo Python estándar.

## Falta (inventario)

| Tipo | Cuántos | Dónde | ¿Se puede? |
|---|---|---|---|
| **PDF hechos con ordenador** (tienen texto) | ~830 | casi todos `pdf\coleccion\` (Community Tango Orchestra, 809), `pdf\sueltas\` (11), 9 de Editorial | **Audiveris**: es donde mejor sale |
| **PDF escaneados** (sin texto) | ~590 | 586 en `pdf\Editorial Orquesta Típica\` | Audiveris, peor (depende del escaneo); manuscritos, mal |
| **Imágenes** sueltas `.jpg` / `.tif` | 406 jpg + 95 tif | Editorial (383 jpg, 95 tif; p. ej. «Julián» sexteto), `pdf\arreglos\` (22 jpg) | Audiveris lee imágenes también |
| **Dentro de .zip / .rar** | 554 archivos (414 zip + 140 rar) | `pdf\coleccion\Partituras\<letras>\` | Dentro: 1.688 jpg (partituras de piano escaneadas), 30 pdf, 20 `.enc`, 5 mid, 8 mp3. Hay que descomprimir (7-Zip está en `C:\Program Files\7-Zip`) y pasar los jpg a Audiveris. 5 no se pudieron mirar |
| **Sibelius `.sib`** | 58 | 6 obras de Editorial: «El paisanito» (19), «Corazón de oro» (16), «Gota de lluvia» (10), «Orlando Goñi» (8), «Quedémonos aquí» (3), «Ahora no me conoces» (2) | No hay programa libre que los abra (MuseScore no puede). Posible vía gratis: **Sibelius First** (versión básica de Avid; creo que es gratis con cuenta y que exporta MusicXML: **comprobarlo antes**) — necesita permiso de Edmundo para crear la cuenta e instalar. Las 6 carpetas traen también sus PDF (9–15 cada una): se pueden pasar esos por Audiveris |
| Finale `.MUS` / `.ETF`, Encore `.ENC` | 3 + 1 + 1 (+20 `.enc` dentro de zips) | Editorial («Comme il faut», «Felicia», «Corazón de oro») | Nada libre los abre. Ignorar (o PDF si lo hay) |

## Audiveris (PDF / imagen → MusicXML) · instalado y probado el 18-11-2026

Está en `audiveris\Audiveris\` (165 MB, versión de consola 5.11.0, sin instalar en Windows, trae su Java; sacado del
.msi con `msiexec /a ... /qn TARGETDIR=...`). Uso: `convertir_partituras.py --pdf <pdf | imagen | carpeta> ...`
→ `convertidas\<nombre>_audiveris.mxl` + `.mid`; registro en `convertidas\_audiveris\<nombre>.log`.

Prueba con 7 (9 min en total con el PC ocupado; ~1–2 min por página):

| Partitura | Resultado |
|---|---|
| «La melodía del corazón», Piano (CTO, ordenador) | **Bien**: acordes y notas iguales al PDF (mirado compás a compás, c.1–4) |
| «El Huracán», Piano y Bandoneón 1 (CTO) | Bien en lo normal; los **trémolos** (redondas con rayas, c.1–3) salen como silencio |
| «El Huracán», Contrabajo (CTO) | Notas bien, pero el **compás** sale 3/8 (la partitura de Ireland no lo escribe) y MuseScore no pudo sacar el .mid |
| «Mi serenata», partitura general (CTO, 16 partes) | Sale entera, pero **las partes se llaman todas «Voice»** (falta el OCR de texto, ver abajo) |
| «La rayuela», Contrabajo (Editorial, **escaneo**) | **Mal**: clave mal leída (registro imposible), tonalidades raras, partida en 2 trozos |
| «Julián», Bandoneón 1 (Editorial, **jpg** 850×1169) | **No lo lee**: poca resolución (hace falta ~300 ppp, el doble o más) |

Arreglado: algunas páginas fallaban con «Comparison method violates its general contract» (fallo de Java) →
el script lanza Audiveris con `-Djava.util.Arrays.useLegacyMergeSort=true`. Y el tiempo máximo por paso se sube
de 2 a 20 min (`-constant org.audiveris.omr.Main.sheetStepTimeOut=1200`): con el PC ocupado se cortaba.

Conclusión: **vale para los ~830 PDF hechos con ordenador** (Community Tango Orchestra), tango a tango, revisando
trémolos y compás. Los escaneos de Editorial y los jpg de los .zip/.rar: casi no valen.

Idiomas del OCR de texto (Tesseract `eng` + `spa`, 41 MB, de github.com/tesseract-ocr/tessdata) bajados el
18-11-2026 a `audiveris\tessdata\`; el script los pasa con `TESSDATA_PREFIX`. Ya los usa, pero **los títulos con letra
de adorno salen ilegibles** («DONATO (30'3) _ |NSTRU|V|ENTAL») y **los nombres de las partes siguen sin salir** en la
partitura general de «Mi serenata» (Voice/Piano). Apaño: si sale una sola parte, el script le pone el instrumento del
nombre del archivo («El Huracán OT - Contrabass» → «Contrabass»).

**«El Huracán» (Donato, CTO) entero, 11 partes** (18-11-2026): `convertidas\El Huracán OT - <parte>_audiveris.mxl`.
Notas y tonalidad (Sol menor) bien en general, pero **cada parte sale con distinto nº de compases (81–92)**: los
trémolos, silencios largos y casillas se pierden o se duplican, y el compás se lo inventa (la partitura no lo escribe:
salen 3/8, 3/4, 4/4 sueltos). La viola baja a Mib2 (imposible: clave de do mal leída en algún trozo).

**Cuadradas y juntas** (18-11-2026) con `cuadrar_partes.py <carpeta de los PDF> --nombre "El Huracán"` →
`convertidas\El_Huracán_general.mxl` + `.mid`: **12 partes × 92 compases, 4/4**. Cómo: los PDF hechos con ordenador
llevan el nº del primer compás de cada línea; por cada línea, si Audiveris vio menos compases se añaden compases de
silencio (detrás del último silencio de la línea, porque casi siempre es un silencio de varios compases leído como
uno; si no, al final), y si vio más se juntan los dos más cortos. Las líneas sin número (empiezan con silencio largo)
se notan por el hueco doble y se cuentan con la anterior. Así todas coinciden al principio de cada línea; dentro de
una línea el error puede ser de 1 compás. Comprobado: c.7 y c.59 dan el mismo acorde en las 12 partes.
Arreglos que hicieron falta para que MuseScore lo abra: duración de los compases añadidos en las «divisiones» de ese
punto (Audiveris las cambia a mitad), silencios sin figura, y grupillos imposibles (6 notas que no caben) quitados.
Limitaciones: Audiveris pierde notas sueltas (el contrabajo del c.7 tiene 2 negras de 4; el violín 1 pierde la
primera corchea); «Flute (1)» es casi toda silencio (la flauta de verdad es «Flute (2)»); los trémolos del
principio salen como silencio.

## Partituras generales de las milongas de Edmundo (19-11-2026)

22 hechas con `cuadrar_partes.py` desde lo que dejó `convertir_todas.py`, revisadas a ojo (primera página en
MuseScore). Cada una deja `convertidas\X_general.mxl` + `.mid` + `.txt` (informe: partes dentro, fuera y por qué).
Desde esta carpeta, con `A="D:\Dropbox\TDJ\Partituras\pdf\coleccion\Community Tango Orchestra"`:

| Nombre | Carpeta (dentro de A) | --quitar |
|---|---|---|
| Recuerdo | Arrangements\Recuerdo | TOL3(KB),TOL2 (VLA) |
| Humillación | Arrangements\Humillacion - Instrumental | |
| Tigre viejo | Arrangements\Tigre Viejo - Parts | |
| Ventarrón | Arrangements\Ventarron | |
| Buscándote | Arrangements\Buscandote | |
| Mariposita | Arrangements\Mariposita - parts | |
| Yuyo verde | Arrangements\Yuyo Verde - F Vocal | |
| El Huracán | Arrangements\Huracan - Donato | |
| Coqueta | Arrangements\Coqueta | |
| Mi serenata | Arrangements\Mi Serenata - Parts | |
| La melodía del corazón | Arrangements\La Melodia del Corazon (Instrumental) | |
| Quejas de bandoneón | Arrangements\Quejas de Bandoneon -OT | |
| Poema | Arrangements\Poema - Parts-SFTX | Poema2,cue |
| Invierno | koreys_stash\Invierno | |
| A la gran muñeca | Arrangements\A la Gran Muneca | |
| A la gran muñeca (sexteto) | Arrangements\_Sextet Parts\A La Gran Muneca - Sextet | |
| Cuartito azul | Arrangements\Cuartito Azul - Inst parts | |
| Cuartito azul (con voz) | Arrangements\Cuartito Azul - vocal | Clarinet in A |
| Cacareando | Arrangements\Cacareando | |
| La yumba | Arrangements\La Yumba BCTO Parts | BCTO2 - Cello |
| Malena | Arrangements\Malena - Dm Vocal | |
| Derecho viejo | Arrangements\Derecho Viejo | TOL3(KB),TOL2 (VLA) |

`python -I -X utf8 cuadrar_partes.py "<A>\<carpeta>" --nombre "<Nombre>" [--quitar "..."]`.
Siguen faltando notas donde pone «compás recortado» (tresillos que Audiveris no leyó) y «compás añadido».

## Piano escaneado de las milongas (19-11-2026) · `piano_escaneado.py`

35 hechas → `Partituras\convertidas\piano\`. Calidad (compases que ya medían bien antes de arreglar):
- **Buenas (10):** Como se pianta la vida 97 %, La puñalada 94 %, Santa milonguita 94 %, Tierrita 87 %,
  Canto de amor 86 %, La pulpera de Santa Lucía 80 %, Desde el alma 71 % (con voz y letra), Loca de amor 64 %
  (arreglo para bandoneón), No le digas que la quiero 61 %, Julián 60 % (edición Donato, `--paginas 5-7`).
- **Regulares (8):** Bélgica, Alma en pena (falta 1 página), Cantando, Casas viejas, El abrojito, Lágrimas y sonrisas,
  Por la vuelta, Rondando tu esquina.
- **Malas (17), no fiarse:** Al compás del corazón, Catamarca, Chiqué (`--paginas 1-3`), Como dos extraños,
  Corazón de artista, El porteñito, El recodo, El pillete, El tamango (falta 1 página), La gayola, Madreselva,
  Mala junta, María, Patético, Tomo y obligo, Torrente, Una noche de garufa.
Lista de trabajos (archivo y páginas): copiar de la tabla de arriba o mirar cada `X_piano.txt`.
Falta (si se quiere): rehacer a mano en MuseScore las malas que importen, mirando `X_original.pdf`.

## Falta

1. Convertir según haga falta, tango a tango (nunca los 2.500 de golpe). Mejor las partes sueltas que la general
   (en las sueltas el instrumento va en el nombre del archivo).
2. Si un tango importa mucho y solo hay escaneo: abrir el PDF en Audiveris con ventanas (`audiveris\Audiveris\Audiveris.exe`, sin `-batch`)
   y corregir a mano, o rehacerlo en MuseScore.

## TODAS las partituras (en marcha desde el 18-11-2026, ~21:50)

Edmundo pidió «todas las de tango», así que ya no es «tango a tango». Script: `convertir_todas.py`.
Funciona como el OCR de la biblioteca:
- Se corta y sigue: `convertidas\todas\_estado.json` (no borrar), lista en `_lista.json` (`--relistar` la rehace:
  tarda 6 min porque mira dentro de 554 zip/rar).
- Prioridad baja; solo en un PC a la vez (`_EN_MARCHA.txt` con el nombre del PC; si otro lo tocó hace < 15 min, no arranca).
- Procesos a la vez: `convertidas\todas\PROCESOS.txt` (lo relee solo; 0 = parar al acabar los que están en marcha).
- Estado cada 3 min: `Partituras\ESTADO_PARTITURAS.txt` (porcentaje, ritmo, hora de fin, «TERMINADO»).
- Orden: 829 PDF hechos con ordenador (2.968 pág.) → 588 escaneados (832) → 502 imágenes sueltas → 1.723 imágenes
  de los .zip/.rar. Total ~5.400 páginas, ~45 s por página y proceso: **~34 h con 2 procesos, ~17 h con 4**.
  Fuera también el cancionero de Satorre (411 pág.) y «Conditioning for dance» (248): son texto, no partituras.
  Tiempo máximo por archivo: 40 min o 4 min por página si es más (hay libros de 112 y 244 páginas).
- Imágenes de menos de 2000 px de alto: se agrandan ×2 o ×3 antes (el jpg de «Julián», 850×1169, tal cual no se
  leía; agrandado ×2 sí, hasta el título).
- Salida: `convertidas\todas\<misma ruta que el original>.mxl` + `.mid`.
- Cada resultado pasa por `comprobar_mxl.py`: «bien» o «dudosa» (compases de largos distintos, notas imposibles,
  instrumento grave demasiado agudo o agudo demasiado grave = clave mal leída, muchos cambios de tonalidad, sin .mid).
  Las dudosas y las que fallan van a `convertidas\todas\REVISAR.txt`. Son señales, no pruebas.
- Audiveris con `-Xmx4G` (cambiado en `audiveris\Audiveris\app\Audiveris.cfg`; venía con 8G, y con 2–4 procesos y
  16 GB de RAM no cabía).
- Fuera: `.sib` (Edmundo mira si consigue Sibelius First), lo de Chopin.
- Claude lo lanza con Bash en segundo plano (lanzarlo suelto con Start-Process lo bloquea el modo automático).
  Si se para al cerrar la sesión, relanzar: `python -I -X utf8 convertir_todas.py` desde esta carpeta.
