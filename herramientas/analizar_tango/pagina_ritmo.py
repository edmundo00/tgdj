"""Página para escuchar y comprobar el análisis de ritmo (paso 2 del plan).

Genera ritmo.html junto a ritmo.json con TODO dentro (datos y audio en Opus), para abrirla con doble clic, sin servidor.
Lleva la mezcla y, si hay pistas separadas, contrabajo, piano y bandoneones para escucharlas solas.
"""
import os, json, base64, subprocess, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
PLANTILLA = os.path.join(AQUI, "ritmo_plantilla.html")


def _opus_b64(ruta, kbps):
    with tempfile.TemporaryDirectory() as d:
        o = os.path.join(d, "a.ogg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", ruta, "-ac", "1", "-ar", "48000",
                        "-c:a", "libopus", "-b:a", f"{kbps}k", o], check=True)
        return "data:audio/ogg;base64," + base64.b64encode(open(o, "rb").read()).decode()


def pistas_de(salida_def, nombre):
    for base in (os.path.join(salida_def, nombre), os.path.join(salida_def, "_datos", nombre)):
        p = os.path.join(base, "pistas")
        if all(os.path.exists(os.path.join(p, f"{n}.flac")) for n in ("contrabajo", "piano", "resto")):
            return {"contrabajo": os.path.join(p, "contrabajo.flac"), "piano": os.path.join(p, "piano.flac"),
                    "bandoneones": os.path.join(p, "resto.flac")}
    return {}


def generar(dir_out, datos, audio, salida_def):
    audios = {"mezcla": _opus_b64(audio, 64)}
    for n, r in pistas_de(salida_def, datos["meta"]["cancion"]).items():
        audios[n] = _opus_b64(r, 40)
    html = open(PLANTILLA, encoding="utf-8").read()
    html = html.replace("/*DATOS*/null", json.dumps(datos, ensure_ascii=False))
    html = html.replace("/*AUDIOS*/null", json.dumps(audios))
    html = html.replace("<!--TITULO-->", datos["meta"]["cancion"])
    ruta = os.path.join(dir_out, "ritmo.html")
    open(ruta, "w", encoding="utf-8").write(html)
    return ruta



def actualizar_indice(raiz):
    """INICIO.html en «Analisis tangos»: la puerta de entrada a todo lo nuevo (ritmo de cada canción y canciones juntas)."""
    import glob, html as H
    filas = []
    for f in sorted(glob.glob(os.path.join(raiz, "_ritmo", "*", "ritmo.json"))):
        try:
            m = json.load(open(f, encoding="utf-8"))["meta"]
        except Exception:
            continue
        c = os.path.basename(os.path.dirname(f))
        if os.path.exists(os.path.join(os.path.dirname(f), "ritmo.html")):
            filas.append(f'<a class="c" href="_ritmo/{c}/ritmo.html"><b>{H.escape(c)}</b><span>{m["compas"]} · {m["bpm"]:.0f} pulsos/min · {H.escape(m["fuentes"])}</span></a>')
    juntas = [f'<a class="c" href="_juntar/{os.path.basename(os.path.dirname(f))}/juntar.html"><b>{H.escape(os.path.basename(os.path.dirname(f)))}</b></a>'
              for f in sorted(glob.glob(os.path.join(raiz, "_juntar", "*", "juntar.html")))]
    pag = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Análisis de ritmo</title><style>
body{{margin:0;background:#17130f;color:#efe6d8;font:16px/1.45 "Segoe UI",system-ui,sans-serif}} main{{max-width:900px;margin:0 auto;padding:20px 18px 40px}}
h1{{color:#f0c05a;margin:0 0 6px}} h2{{color:#f0c05a;font-size:17px;margin:26px 0 8px}} p{{color:#cbbda9}}
.c{{display:block;background:#221c16;border:1px solid #3a3026;border-radius:9px;padding:10px 14px;margin:6px 0;color:#efe6d8;text-decoration:none}}
.c:hover{{border-color:#f0c05a}} .c span{{display:block;color:#a8998a;font-size:13.5px}} code{{background:#120e0b;color:#f0c05a;padding:2px 6px;border-radius:5px}}
.paso{{background:#221c16;border-left:4px solid #f0c05a;padding:8px 12px;border-radius:6px;margin:6px 0}}
</style></head><body><main>
<h1>Análisis de ritmo</h1>
<p>Aquí está todo lo nuevo. El visor antiguo (gráficas por instrumento) sigue en <a href="visor.html" style="color:#f0c05a">visor.html</a>.</p>
<div class="paso"><b>Analizar una canción:</b> arrastra el audio encima de <code>ritmo.bat</code> (en la carpeta del programa). Al terminar se abre su página y aparece aquí.</div>
<div class="paso"><b>Juntar 2, 3 o 4 canciones</b> (compararlas o alternarlas como Carmen y Canaro): arrastra los audios a la vez encima de <code>juntar.bat</code>.</div>
<h2>Canciones analizadas ({len(filas)})</h2>{"".join(filas) or "<p>Todavía ninguna.</p>"}
<h2>Canciones juntas ({len(juntas)})</h2>{"".join(juntas) or "<p>Todavía ninguna.</p>"}
</main></body></html>"""
    open(os.path.join(raiz, "INICIO.html"), "w", encoding="utf-8").write(pag)


if __name__ == "__main__":
    # Rehace la página de los análisis ya hechos (sin volver a analizar): python pagina_ritmo.py [carpeta de _ritmo …]
    import sys, glob
    raiz = r"D:\Dropbox\TDJ\Analisis tangos"
    carpetas = sys.argv[1:] or glob.glob(os.path.join(raiz, "_ritmo", "*"))
    for c in carpetas:
        f = os.path.join(c, "ritmo.json")
        if os.path.exists(f):
            d = json.load(open(f, encoding="utf-8"))
            print(generar(c, d, d["meta"]["audio"], raiz))
    actualizar_indice(raiz)
