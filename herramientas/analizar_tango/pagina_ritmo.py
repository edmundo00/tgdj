r"""Página para escuchar y comprobar el análisis de ritmo (paso 2 del plan).

UNA sola página para todas las canciones (18-11-2026): «Analisis tangos
itmo.html?c=<carpeta de _ritmo>».
Cada análisis deja junto a ritmo.json un ritmo_datos.js (datos + audio en Opus) que la página carga con <script>,
así funciona abriendo con doble clic, sin servidor. Lleva la mezcla y, si hay pistas separadas, contrabajo, piano y
bandoneones para escucharlas solas. Lo mismo para «juntar»: juntar.html?c=<carpeta de _juntar> + juntar_datos.js.
La entrada a todo es «TDJ\HERRAMIENTAS.html».
"""
import os, json, base64, subprocess, tempfile, shutil, urllib.parse

AQUI = os.path.dirname(os.path.abspath(__file__))
PLANTILLA = os.path.join(AQUI, "ritmo_plantilla.html")


def _opus_b64(ruta, kbps):
    with tempfile.TemporaryDirectory() as d:
        o = os.path.join(d, "a.ogg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", ruta, "-ac", "1", "-ar", "48000",
                        "-c:a", "libopus", "-b:a", f"{kbps}k", o], check=True)
        return "data:audio/ogg;base64," + base64.b64encode(open(o, "rb").read()).decode()


def _en_silencio(ruta, umbral=0.003):
    """¿La pista está (casi) en silencio? (la voz separada de un tango instrumental). Mira 30 trozos de 1 s."""
    try:
        import soundfile as sf
        info = sf.info(ruta); sr, n = info.samplerate, info.frames
        picos = []
        for k in range(30):
            x, _ = sf.read(ruta, frames=sr, start=int((n - sr) * k / 29) if n > sr else 0, dtype="float32", always_2d=True)
            picos.append(float(abs(x).max()) if len(x) else 0.0)
        return max(picos) < umbral
    except Exception:
        return False


def pistas_de(salida_def, nombre):
    for base in (os.path.join(salida_def, nombre), os.path.join(salida_def, "_datos", nombre)):
        p = os.path.join(base, "pistas")
        if all(os.path.exists(os.path.join(p, f"{n}.flac")) for n in ("contrabajo", "piano", "resto")):
            r = {"contrabajo": os.path.join(p, "contrabajo.flac"), "piano": os.path.join(p, "piano.flac"),
                 "bandoneones": os.path.join(p, "resto.flac")}
            v = os.path.join(p, "voz.flac")   # la voz: fila con su onda en la lupa (19-11-2026)
            if os.path.exists(v) and not _en_silencio(v):   # en un tango instrumental la pista sale vacía: sin fila «Voz»
                r["voz"] = v
            return r
    return {}


def generar(dir_out, datos, audio, salida_def):
    """Escribe <carpeta>/ritmo_datos.js y devuelve la dirección file:/// de la página con esa canción."""
    audios = {"mezcla": _opus_b64(audio, 64)}
    for n, r in pistas_de(salida_def, datos["meta"]["cancion"]).items():
        audios[n] = _opus_b64(r, 40)
    escribir_js(os.path.join(dir_out, "ritmo_datos.js"), "RITMO", dict(datos=datos, audios=audios))
    viejo = os.path.join(dir_out, "ritmo.html")      # antes había una página por canción
    if os.path.exists(viejo):
        os.remove(viejo)
    return url_cancion(salida_def, "ritmo", os.path.basename(dir_out))


def escribir_js(ruta, variable, valor):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(f"window.{variable} = ")
        json.dump(valor, f, ensure_ascii=False)
        f.write(";\n")


def url_cancion(raiz, pagina, carpeta):
    return f"{pathlib_uri(os.path.join(raiz, pagina + '.html'))}?c={urllib.parse.quote(carpeta)}"


def pathlib_uri(ruta):
    import pathlib
    return pathlib.Path(ruta).resolve().as_uri()


def abrir(url):
    """Abre una dirección con ?c=… (Windows pierde el «?» al abrir un file:/// directamente: se pasa por una página puente)."""
    puente = os.path.join(tempfile.gettempdir(), "tdj_abrir.html")
    open(puente, "w", encoding="utf-8").write(f'<meta charset="utf-8"><script>location.replace({json.dumps(url)})</script>')
    os.startfile(puente)


def actualizar_indice(raiz):
    r"""Pone al día lo que leen las páginas únicas: _ritmo/indice.js, _juntar/indice.js, ritmo.html y juntar.html.
    INICIO.html queda como atajo a TDJ\HERRAMIENTAS.html (la entrada a todas las herramientas)."""
    import glob
    lista = []
    for f in sorted(glob.glob(os.path.join(raiz, "_ritmo", "*", "ritmo.json")), key=lambda x: x.lower()):
        c = os.path.dirname(f)
        if not os.path.exists(os.path.join(c, "ritmo_datos.js")):
            continue
        try:
            m = json.load(open(f, encoding="utf-8"))["meta"]
        except Exception:
            continue
        x = dict(c=os.path.basename(c), compas=m["compas"], bpm=round(m["bpm"], 1), fuentes=m["fuentes"])
        if os.path.exists(os.path.join(c, "partitura_datos.js")):
            x["partitura"] = True
        if os.path.exists(os.path.join(c, "video_datos.js")):
            x["video"] = True       # vídeo de bailarines (video.py)
        lista.append(x)
    escribir_js(os.path.join(raiz, "_ritmo", "indice.js"), "RITMO_LISTA", lista)
    juntas = sorted((os.path.basename(os.path.dirname(f)) for f in glob.glob(os.path.join(raiz, "_juntar", "*", "juntar_datos.js"))),
                    key=str.lower)
    os.makedirs(os.path.join(raiz, "_juntar"), exist_ok=True)
    escribir_js(os.path.join(raiz, "_juntar", "indice.js"), "JUNTAR_LISTA", juntas)
    shutil.copyfile(PLANTILLA, os.path.join(raiz, "ritmo.html"))
    # bibliotecas que usan las páginas (Verovio para la partitura): se guardan en local, nada de internet
    os.makedirs(os.path.join(raiz, "lib"), exist_ok=True)
    for f in os.listdir(os.path.join(AQUI, "lib")):
        o, d = os.path.join(AQUI, "lib", f), os.path.join(raiz, "lib", f)
        if not os.path.exists(d) or os.path.getsize(d) != os.path.getsize(o):
            shutil.copyfile(o, d)
    shutil.copyfile(os.path.join(AQUI, "juntar_plantilla.html"), os.path.join(raiz, "juntar.html"))
    open(os.path.join(raiz, "INICIO.html"), "w", encoding="utf-8").write(
        '<!doctype html><meta charset="utf-8"><title>Herramientas</title>'
        '<script>location.replace("../HERRAMIENTAS.html")</script><a href="../HERRAMIENTAS.html">Herramientas</a>')


if __name__ == "__main__":
    # Rehace la página de los análisis ya hechos (sin volver a analizar): python pagina_ritmo.py [carpeta de _ritmo …]
    import sys, glob
    raiz = r"D:\Dropbox\TDJ\Analisis tangos"
    carpetas = sys.argv[1:] or glob.glob(os.path.join(raiz, "_ritmo", "*"))
    if os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe") and r"C:\ffmpeg\bin" not in os.environ["PATH"]:
        os.environ["PATH"] = r"C:\ffmpeg\bin;" + os.environ["PATH"]   # PC del trabajo
    def audio_de(a):
        # algunos análisis guardaron la ruta relativa (a MUSICA o a TDJ)
        for r in (a, os.path.join(r"D:\Dropbox\TDJ\MUSICA", a), os.path.join(r"D:\Dropbox\TDJ", a)):
            if os.path.exists(r): return r
        return None
    mal = []
    for c in carpetas:
        f = os.path.join(c, "ritmo.json")
        if not os.path.exists(f):
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
            a = audio_de(d["meta"]["audio"])
            if not a:
                raise FileNotFoundError(d["meta"]["audio"])
            print(generar(c, d, a, raiz), flush=True)  # rehace ritmo_datos.js
        except Exception as e:
            mal.append(f"{os.path.basename(c)}: {e}")
    actualizar_indice(raiz)
    if mal:
        print(f"\nNO SE PUDIERON REHACER ({len(mal)}):\n  " + "\n  ".join(mal))
