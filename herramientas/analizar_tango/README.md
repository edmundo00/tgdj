# Analizar tangos · visor de ritmo

Herramientas para estudiar la música de un tango: unos programas en Python analizan la grabación
(pulso, compás, dónde cae el 1, golpes de cada instrumento, cambios de nota…) y una página web
(`ritmo.html`) lo enseña todo sincronizado con el audio. Se le puede añadir la partitura (MusicXML)
y un vídeo de bailarines, y todo va a la vez.

Hecho por Edmundo (@tdj.edmundo), DJ de tango, para preparar sus milongas y sus reels.

## Qué se ve en la página

- La canción entera arriba (clic = ir, arrastrar = repetir un trozo), ⏮ ⏭, «ir al compás N».
- Velocidad 100 / 75 / 60 / 50 / 25 % **sin cambiar el tono** (teclas ↑ ↓).
- La **lupa**: compases y tiempos, una fila por instrumento (contrabajo, piano, bandoneones, voz…)
  con sus golpes, cambios de nota y su onda. Clic en el nombre de una fila = oírla sola.
- Metrónomo y clic de comprobación (corcheas, semicorcheas, tresillos) encima de la música.
- **Partitura** (si se la das) cuadrada compás a compás con la grabación.
- **Vídeo** de bailarines cuadrado con la música (se puede subir desde la misma página) y marcar las pisadas.

Funciona con doble clic, sin servidor: los datos de cada canción van en un `.js` junto a la página.

## Instalar (Windows)

1. **Python 3.11 o más nuevo** (probado con 3.13).
2. **ffmpeg**: bájalo de https://ffmpeg.org y deja `ffmpeg.exe` y `ffprobe.exe` en el PATH
   o en `C:\ffmpeg\bin`.
3. Un entorno para las herramientas (los `.bat` lo buscan ahí; si no existe, usan el `python` del PATH):

   ```powershell
   python -m venv $env:USERPROFILE\venvs\analizar_tango
   & $env:USERPROFILE\venvs\analizar_tango\Scripts\python.exe -m pip install -r requirements.txt
   ```

   Es pesado (PyTorch). Sin tarjeta gráfica funciona igual, solo que más despacio.

4. **Dónde se guardan los análisis.** Por defecto en `<tu carpeta de usuario>\TDJ\Analisis tangos\`.
   Para cambiarlo, crea `rutas_local.json` junto a estos archivos:

   ```json
   {"tdj": "D:/Musica/Tango", "analisis": "D:/Musica/Tango/Analisis tangos"}
   ```

   (o la variable de entorno `TDJ_DIR`). `python rutas.py` enseña qué carpetas está usando.

## Usar

**Analizar el ritmo de una canción** (unos minutos):

```powershell
.\ritmo.bat "C:\ruta\a\El Flete.flac"
```

Al terminar abre la página. Si el compás o el 1 salen mal, se le ayuda y lo recuerda la próxima vez:

```powershell
.\ritmo.bat "El Flete.flac" --compas 3/4 --uno 12.34
```

(`--uno` = un segundo donde cae un 1; también `--pulso doble|mitad`.)

**Separar los instrumentos** (más lento, mucho más fino: golpes y notas por instrumento):

```powershell
.\ritmo.bat "El Flete.flac" --separar
```

o el análisis completo, que además escribe un informe: `.\analizar_tango.bat "El Flete.flac"`.

**Ver lo analizado:** abre `Analisis tangos\ritmo.html` y elige la canción en su buscador.

**Añadir la partitura** (MusicXML `.mxl`):

```powershell
python partitura.py "Analisis tangos\_ritmo\El Flete" "El Flete.mxl"
```

Si queda corrida, en la página se arrastran las rayas azules «P…» hasta su sitio.

**Añadir un vídeo de baile:** desde la página («🎬 Vídeo», se cuadra solo y queda en ese navegador),
o fijo con `python video.py "Analisis tangos\_ritmo\El Flete" "baile.mp4"`.

**Comparar 2–4 versiones del mismo tango:** `.\juntar.bat "a.flac" "b.flac"` → `juntar.html`.

## Carpetas

```
Analisis tangos\
  ritmo.html, juntar.html, lib\      la página (la copia pagina_ritmo.py desde ritmo_plantilla.html)
  _ritmo\<canción>\                 ritmo.txt (resumen), ritmo.json, ritmo_datos.js (datos + audio de la página)
  _datos\<canción>\pistas\          instrumentos separados
```

Tras cambiar `ritmo_plantilla.html`: `python pagina_ritmo.py` rehace la página y los datos de todas las
canciones sin volver a analizar. `python probar_ritmo.py "Analisis tangos\_ritmo\<canción>"` la prueba
con Edge o Chrome sin ventana (debe decir TODO BIEN).

## Lo que no es tan fiable

- Sin separar instrumentos, los golpes por instrumento son ruido (la página lo avisa y los esconde).
- El 1 a veces sale corrido un tiempo aunque diga «probable»: comprobarlo de oído y corregir con `--uno`.
- El nombre de las notas con la orquesta entera es aproximado; el instante del cambio sí es bueno.
- Sin separar no distingue tresillos de verdad de «ta-ka-ta» de semicorcheas.

## Más

- `PLAN_*.md`: planes y pruebas hechas (cuadrar golpes, transcripción a notas, el visor).
- `transcripcion\`: audio a notas (bajo con YourMT3+, en su propio entorno `venvs\yourmt3`).
- `bailarines\`: marcar pisadas en un vídeo y hacer vídeos con destellos (`bailarines\INSTRUCCIONES.md`).
- `reel_frase\`: monta un reel de Instagram (necesita Node y HyperFrames).

El pulso lo saca [Beat This!](https://github.com/CPJKU/beat_this) (CPJKU) y la separación
[audio-separator](https://github.com/nomadkaraoke/python-audio-separator); la partitura se dibuja con
[Verovio](https://www.verovio.org).
