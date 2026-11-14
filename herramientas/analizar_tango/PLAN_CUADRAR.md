# Plan · Cuadrar golpes (fase 1)

Objetivo: que la herramienta que usamos a mano con la habanera (encontrar el 1, buscar un dibujo de golpes,
empalmar audios al golpe y comprobarlo) sea **fiable, automática y comprobable de oído**, y que funcione
para el tango de verdad: contrabajo, piano, bandoneones y violines (no bombo y caja).

Se construye **dentro de `analizar_tango`**, reutilizando lo que ya hay: separación en pistas (`separar.py`),
pulso y compases (`pulso.py`, con Beat This! como opción) y golpes por instrumento (`golpes.py`).

## Lo que aprendimos con la habanera (lo que hay que evitar)
- El 1 salió **3 semicorcheas desplazado**: se eligió con un ajuste que no comprobaba alternativas.
- Luego quedaron **55 ms** de desfase: no se midió el resultado final hasta que el usuario lo oyó.
- Los números (tiempos de cada golpe) se **copiaban a mano** al vídeo.

## Piezas

### 1. El «1» seguro (`fase.py`)
- Parte del pulso que ya da `pulso.py` y prueba **todas las posiciones posibles del 1** (las 4 de los tiempos y, dentro, las semicorcheas).
- Puntúa cada posición **por separado con el contrabajo y con el piano** (sus pistas separadas).
- Si contrabajo y piano coinciden → «seguro». Si no → avisa y enseña las dos opciones con su nota.
- Para música sin separar (p. ej. un reguetón) usa bandas de frecuencia de la mezcla.

### 2. Buscar un dibujo de golpes (`patrones.py`)
- Los dibujos se escriben en texto sencillo, sobre las casillas del compás (8 corcheas; 16 semicorcheas cuando haga falta):
  - `milonga 3+3+2 · contrabajo · 1 4 5 7`
  - `síncopa · bandoneones · …`  ·  `pianitos · piano · …`
- Por cada compás y cada instrumento: nota de parecido (golpes que caen en sus casillas, menos los que sobran fuera).
- Resultado: lista de **tramos** (compases seguidos que lo tocan limpio), ordenados de mejor a peor, en texto y en tabla.

### 3. La lupa de frecuencias (en la página)
- Dos deslizadores para elegir una banda (p. ej. 40–200 Hz para el contrabajo) y ver **la onda de esa banda compás a compás**, con las casillas debajo y los golpes marcados.
- Bandas guardadas por instrumento (y por orquesta, si alguna graba distinto).
- Se calcula en el propio navegador: no hace falta Python para mover los deslizadores.
- Sirve para grabaciones viejas donde la separación falla y para comprobar lo que dice la herramienta.

### 4. Empalmar y comprobar solo (`empalmar.py`)
- «Pon la canción B para que el 1 de su compás N caiga en el segundo X de A», con corte seco o fundido, y ajuste de tempo opcional.
- Después **mide el archivo final** y da el desvío de cada golpe en milisegundos. Si la media pasa de **15 ms**, avisa y no da por bueno el empalme.

### 5. Mapa de golpes (`mapa_golpes.json`)
- Compases, tiempos, cada golpe por instrumento (casilla, adelanto/retraso en ms, fuerza) y los tramos encontrados.
- Los vídeos (HyperFrames) **leen este archivo**: la rejilla, los BUM–PA y los cortes salen de la medida, no de números copiados.

### 6. Página para comprobarlo de oído (`cuadrar.html`)
- La canción con un **clic en cada golpe** (se puede elegir el instrumento: contrabajo, piano…) y la rejilla encendiéndose.
- Marcar un tramo con el ratón; afinar ±1 / 5 / 10 / 50 ms como en la página de alinear a Callas; botón grande de parar y barra espaciadora.
- Los tramos que encuentra la búsqueda, pintados encima de la onda.
- Guarda lo elegido en un archivo para que lo use `empalmar.py` o el vídeo.

### 7. Una sola herramienta: también dos canciones juntas (pedido el 13-11)
Todo en una página, sin herramientas sueltas: lo de alinear a Callas con Canaro (`borradores\habanera\scripts\alinear_fino.py`)
pasa a ser un modo de esta misma página.
- **Comparar dos canciones**: se cargan dos análisis de `_ritmo` y se ven sus rejillas una encima de otra, compás a compás.
- **Alinear**: «Juntas» (una por cada oído), «Alternando» compás a compás, solo una, lupa de 2 compases con sus casillas,
  ±1/5/10/50 ms y «Afinar solo» (correlación de golpes). Como en la página de Callas, que funcionó.
- **Ajuste de tempo** opcional (estirar una para que vaya al tempo de la otra), con el desvío medido al final.
- Sale un archivo con el empalme elegido para el vídeo.

## Usos que ya tiene esperando
- Reels a mejorar (en sesiones aparte): síncopa 3/3 de Tanturi, pianitos, tresillos de D'Arienzo.
- Comparar versiones: «El llorón» de Hugo Díaz (armónica) con otras; Carmen con la Milonga del 900.

## Banco de pruebas (para dar cada paso por bueno)
| Grabación | Qué sabemos | Qué tiene que salir |
|---|---|---|
| Habanera de Carmen (MIDI) | bajo en 1 4 5 7 | ese dibujo, el 1 en su sitio |
| Canaro · Milonga del 900 | compás de 1,53 s, 1 medido a mano | el mismo 1 (± 15 ms) y el 1 4 5 7 en el contrabajo |
| «Hasta el suelo» (reguetón) | compases 19–25 limpios, 1 en 0,0372 + k·1,2528 s | esos compases arriba de la lista, sin el error de 3 semicorcheas |
| D'Arienzo · El Flete | pianitos conocidos | los pianitos encontrados en el piano |

## Orden y paradas para revisar
1. **Fase segura + búsqueda de dibujos** (línea de comandos, resultado en texto). Se prueba con el banco → **revisión del usuario**.
2. **Página** con clic, rejilla, lupa de frecuencias y elección de tramo → **el usuario la prueba de oído**.
3. **Empalmar + medir + mapa de golpes**. Prueba final: rehacer el empalme del final de la habanera solo con la herramienta y comparar con lo hecho a mano → **revisión**.

Fases siguientes (no en esta): buscar dibujos en toda la biblioteca de DJ (fase 2) y letra con tiempos para subtítulos (fase 3, necesita descargar un modelo de voz: preguntar antes).

## Antes de empezar
- Hay cambios sin guardar en git en `analizar_tango.py`, `golpes.py` y `visor.html` (la fila «Orquesta entera» y el modo rápido). Conviene hacer commit primero para partir de algo limpio.
