r"""MARCAR PISADAS · prepara la página para marcar a mano las pisadas de bailarines sobre la música.

    marcar_pisadas.bat "video.mp4" "cancion.flac" [opciones]

Hace todo solo:
  1. Alinea el vídeo con la grabación (en qué segundo de la canción empieza). Si pasas varias grabaciones
     de la misma canción, se queda con la que mejor encaja (sirve para saber qué versión bailan).
  2. Si la canción no está analizada, lanza analizar_tango.py (pistas separadas, golpes, compases): tarda minutos.
  3. Saca los fotogramas del tramo pedido, la música alineada (la grabación buena, no la del vídeo)
     y los cambios de plano del vídeo.
  4. Deja en la carpeta de salida index.html + datos.js: se abre con doble clic en Chrome.

Opciones:
  --compases 26-30       tramo por compases de la canción (lo normal)
  --segundos 0-8.5       o por segundos del vídeo
  --bailarines "Sol:follower,London:leader"   nombres y papel (sin papel: el 1.º follower, el 2.º leader).
                         Follower en tonos cálidos (oro/naranja), leader en fríos (azul/turquesa). Teclas: Q W y O P.
  --salida carpeta       por defecto: <carpeta del vídeo>\marcar_<nombre del vídeo>
  --inicio 53.696        segundo de la canción donde empieza el vídeo (si ya lo sabes, no alinea)
Las pisadas se guardan en esa carpeta (pisadas.json) con el botón Guardar de la página.
Después: video_pisadas.bat "<carpeta>"  → vídeo con destellos en cada pisada y la rejilla del compás.
"""
import os, sys, json, shutil, argparse, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import datos_tango as DT

AQUI = os.path.dirname(os.path.abspath(__file__))
FF = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"
FP = shutil.which("ffprobe") or r"C:\ffmpeg\bin\ffprobe.exe"
COLORES = ["240,192,90", "90,209,240", "240,120,170", "120,220,130"]
ANCHO = 720                                   # ancho de los fotogramas de la página


def vaciar(carpeta):
    """deja la carpeta vacía (Dropbox a veces bloquea el borrado de la carpeta entera)."""
    os.makedirs(carpeta, exist_ok=True)
    for f in os.listdir(carpeta):
        try:
            os.remove(os.path.join(carpeta, f))
        except OSError:
            pass


def fps_de(video):
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,nb_frames,duration",
                        "-of", "json", video], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return float(a) / float(b), float(s.get("duration", 0))


def cortes_de_plano(video, umbral=0.25):
    r = subprocess.run([FF, "-v", "info", "-i", video, "-vf", f"select='gt(scene,{umbral})',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(l.split("pts_time:")[1].split()[0]) for l in r.stderr.splitlines() if "pts_time:" in l]


def main():
    ap = argparse.ArgumentParser(description="Prepara la página para marcar pisadas de bailarines")
    ap.add_argument("video")
    ap.add_argument("cancion", nargs="+", help="grabación (o varias candidatas) de la canción que bailan")
    ap.add_argument("--compases")
    ap.add_argument("--segundos")
    ap.add_argument("--bailarines", default="Ella,Él")
    ap.add_argument("--salida")
    ap.add_argument("--inicio", type=float)
    a = ap.parse_args()

    video = os.path.abspath(a.video)
    base = os.path.splitext(os.path.basename(video))[0]
    out = os.path.abspath(a.salida or os.path.join(os.path.dirname(video), "marcar_" + base))
    os.makedirs(out, exist_ok=True)
    fps, dur = fps_de(video)
    print(f"Vídeo: {base} · {fps:.2f} fps · {dur:.1f} s")

    # 1. alinear (o reutilizar lo que ya había)
    conf_p = os.path.join(out, "config.json")
    viejo = json.load(open(conf_p, encoding="utf-8")) if os.path.isfile(conf_p) else {}
    if a.inicio is not None:
        cancion, inicio = os.path.abspath(a.cancion[0]), a.inicio
    elif viejo.get("cancion") in [os.path.abspath(c) for c in a.cancion] and "inicio" in viejo:
        cancion, inicio = viejo["cancion"], viejo["inicio"]
        print(f"Alineado de antes: empieza en {inicio:.3f} s de la canción")
    else:
        import alinear
        wav = os.path.join(out, "_audio_video.wav")
        subprocess.run([FF, "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "44100", wav], check=True)
        print("Alineando con la grabación…")
        ov, cv = alinear.rasgos(wav)
        res = []
        for c in a.cancion:
            r = alinear.alinear(ov, cv, *alinear.rasgos(c)); r["cancion"] = os.path.abspath(c); res.append(r)
            print(f"  parecido {r['parecido']:.2f} · empieza en {r['inicio_en_cancion']:.2f} s · velocidad {r['velocidad']:.3f} · {os.path.basename(c)}")
        mejor = max(res, key=lambda r: r["parecido"])
        if abs(mejor["velocidad"] - 1) > 0.004:
            print(f"  OJO: el vídeo va a velocidad {mejor['velocidad']:.3f} respecto a la grabación (los tiempos se corrigen solo en el inicio)")
        if mejor["parecido"] < 1.0:
            print("  OJO: el parecido es bajo: ¿seguro que es esta grabación?")
        cancion, inicio = mejor["cancion"], mejor["inicio_en_cancion"]
        os.remove(wav)

    # 2. análisis de la canción
    carpeta = DT.carpeta_datos(cancion)
    if not os.path.isfile(os.path.join(carpeta, "golpes.csv")):
        print("La canción no está analizada: lanzo analizar_tango.py (tarda unos minutos)…")
        env = dict(os.environ, TDJ_SIN_PAUSA="1")
        subprocess.run([DT.PY, os.path.join(DT.HERR, "analizar_tango.py"), cancion], check=True, env=env)
    d = DT.DatosTango(cancion, inicio)

    # 3. tramo
    if a.compases:
        c0, c1 = [int(x) for x in a.compases.split("-")]
        t0, t1 = d.compases(c0, c1)
    elif a.segundos:
        t0, t1 = [float(x) for x in a.segundos.split("-")]
    else:
        t0, t1 = 0, dur
    t0, t1 = max(0.0, t0), min(dur - 1 / fps, t1)
    f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
    print(f"Tramo: fotogramas {f0}–{f1} ({t0:.2f}–{t1:.2f} s del vídeo)")

    # 4. fotogramas, música y cortes de plano
    fot = os.path.join(out, "fotogramas")
    vaciar(fot)
    subprocess.run([FF, "-v", "error", "-y", "-i", video, "-vf", f"select='between(n\\,{f0}\\,{f1})',scale={ANCHO}:-2", "-vsync", "0",
                    "-q:v", "3", "-start_number", str(f0), os.path.join(fot, "f%05d.jpg")], check=True)
    subprocess.run([FF, "-v", "error", "-y", "-i", cancion, "-af", f"atrim={inicio + f0 / fps}:{inicio + (f1 + 1) / fps},asetpts=PTS-STARTPTS",
                    "-c:a", "aac", "-b:a", "160k", os.path.join(out, "audio.m4a")], check=True)
    # vista «movimiento»: diferencia con el fotograma anterior (lo quieto, oscuro). Se calcula aquí porque
    # Chrome no deja leer píxeles de fotos abiertas desde el disco.
    import numpy as np
    from PIL import Image as _I
    mov = os.path.join(out, "fotogramas_mov")
    vaciar(mov)
    prev = None
    for n in range(f0, f1 + 1):
        a_ = np.asarray(_I.open(os.path.join(fot, f"f{n:05d}.jpg")).convert("RGB"), dtype=np.int16)
        b_ = a_ if prev is None else prev
        d_ = np.minimum(255, np.abs(a_ - b_).sum(axis=2) * 1.6)
        g_ = a_.mean(axis=2) * 0.25
        res = np.stack([g_ + d_, g_ + d_ * 0.85, g_ + d_ * 0.4], axis=2).clip(0, 255).astype(np.uint8)
        _I.fromarray(res).save(os.path.join(mov, f"f{n:05d}.jpg"), quality=80)
        prev = a_
    # onda de la música (energía cada medio fotograma) para dibujarla en la línea de tiempo
    raw = subprocess.run([FF, "-v", "error", "-i", os.path.join(out, "audio.m4a"), "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    y_ = np.frombuffer(raw, np.float32)
    paso = 8000 / (fps * 2)
    onda = [float(np.sqrt(np.mean(y_[int(k * paso):int((k + 1) * paso)] ** 2))) if int((k + 1) * paso) <= len(y_) else 0.0
            for k in range(int(len(y_) / paso))]
    tope = max(onda) or 1
    onda = [round((v / tope) ** 0.7, 2) for v in onda]
    cortes = [round(c * fps) for c in cortes_de_plano(video) if f0 < c * fps <= f1]
    alto = int(round(ANCHO * 1920 / 1080))
    from PIL import Image
    w, h = Image.open(os.path.join(fot, f"f{f0:05d}.jpg")).size

    # 5. datos para la página (todo en fotogramas, con decimales)
    # «Sol:follower,London:leader» (sin rol: el 1.º follower, el 2.º leader)
    nombres, roles = [], []
    for k, t in enumerate([t.strip() for t in a.bailarines.split(",") if t.strip()][:4]):
        nom, _, rol = t.partition(":")
        nombres.append(nom.strip())
        roles.append((rol.strip() or ("Follower" if k == 0 else "Leader" if k == 1 else f"Bailarín {k + 1}")).capitalize())
    pul = [[round(t * fps, 2), c, k] for t, c, k in d.pulsos if f0 - 3 * fps <= t * fps <= f1 + 3 * fps]
    golpes = {p: [[round(t * fps, 2), round(db, 1)] for t, db in g if f0 - 2 <= t * fps <= f1 + 2] for p, g in d.golpes.items()}
    datos = {
        "id": base, "video": video, "cancion": os.path.splitext(os.path.basename(cancion))[0], "inicio": inicio,
        "fps": fps, "f0": f0, "f1": f1, "ancho": w, "alto": h, "anchoVideo": 1080, "altoVideo": 1920,
        "pulsos": pul, "golpes": golpes, "cortes": cortes, "onda": onda,
        "bailarines": [{"nombre": n, "rol": roles[i], "color": COLORES[i]} for i, n in enumerate(nombres)],
    }
    # tamaño real del vídeo (las pisadas se guardan en píxeles del vídeo original)
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", video],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    datos["anchoVideo"], datos["altoVideo"] = s["width"], s["height"]
    with open(os.path.join(out, "datos.js"), "w", encoding="utf-8") as f:
        f.write("window.DATOS = " + json.dumps(datos, ensure_ascii=False) + ";\n")
    shutil.copy(os.path.join(AQUI, "plantilla_marcar.html"), os.path.join(out, "index.html"))
    conf = {"video": video, "cancion": cancion, "inicio": inicio, "fps": fps, "f0": f0, "f1": f1, "bailarines": nombres,
            "anchoVideo": datos["anchoVideo"], "altoVideo": datos["altoVideo"]}
    json.dump(conf, open(conf_p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    import pathlib
    print("\nLISTO. Abre en Chrome:\n  " + pathlib.Path(out, "index.html").as_uri())


if __name__ == "__main__":
    main()
