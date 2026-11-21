r"""VÍDEO DE BAILARINES en la página de ritmo («mega visor», fase 2, 19-11-2026).

    python video.py "<carpeta de _ritmo\canción>" "<vídeo.mp4 | carpeta marcar_…>" [opciones]
    python video.py "<carpeta de _ritmo\canción>"            rehace video_datos.js con lo que hay en video.json
                                                              (p. ej. después de pegar pisadas nuevas)
    python video.py --todas                                   lo mismo con todas las canciones que tengan vídeo

Deja en la carpeta de la canción:
  video_<id>.mp4   copia ligera del vídeo (720 px de ancho, con su sonido (para «🔊 sonido del vídeo»), un fotograma clave cada 1/3 s para que
                   saltar a cualquier sitio sea instantáneo). La página la enlaza; no va dentro del .js.
  video.json       los vídeos de la canción: de dónde salen, dónde empiezan en la grabación, bailarines, pisadas.
  video_datos.js   lo mismo para la página (window.VIDEO), con las pisadas pasadas a segundos de la grabación.

Cuadre: si se le da una carpeta marcar_… (de bailarines\marcar_pisadas.py) usa su config.json (ya alineado) y sus
pisadas (pisadas.txt = texto «Copiar para Claude», o pisadas.json). Si se le da un vídeo suelto lo alinea con
bailarines\alinear.py (golpes y croma, probando velocidades 0,94–1,06). La página deja corregirlo a mano y da un texto
«VIDEO <id> inicio=…» → se pasa aquí con --inicio.

Opciones:
  --inicio 53.696          segundo de la grabación donde empieza el vídeo (no alinea)
  --velocidad 1.0          1 s de vídeo = velocidad s de grabación (lo da alinear.py)
  --id nombre              nombre corto del vídeo (por defecto, el del archivo)
  --bailarines "Sol:follower,London:leader"
  --pisadas pisadas.txt    otras pisadas (texto «PISADAS …» o .json)
  --quitar <id>            quita ese vídeo de la canción
"""
import os, sys, json, glob, shutil, argparse, subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "bailarines"))
RAIZ = r"D:\Dropbox\TDJ\Analisis tangos"
FF = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"
FP = shutil.which("ffprobe") or r"C:\ffmpeg\bin\ffprobe.exe"
COLORES = {"follower": ["#f0c05a", "#f08a4b"], "leader": ["#5ad1f0", "#5af0c0"]}   # follower cálidos, leader fríos (como marcar_pisadas)


def sondear(video):
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,width,height,duration",
                        "-of", "json", video], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return float(a) / float(b), float(s.get("duration") or 0), int(s["width"]), int(s["height"])


def leer_pisadas(ruta):
    """texto «PISADAS <id> · Sol,London · N» + «fotograma bailarín I|D a|o x y», o pisadas.json (botón Guardar)."""
    txt = open(ruta, encoding="utf-8-sig").read().strip()
    if not txt.startswith("PISADAS"):
        d = json.loads(txt)
        return d.get("bailarines"), [(int(p["n"]), int(p["b"]), p["pie"], "o" if p.get("tipo") == "adorno" else "a",
                                      int(p.get("x") or 0), int(p.get("y") or 0)) for p in d["pisadas"]]
    lineas = txt.splitlines()
    cab = lineas[0].split("·")
    nombres = [n.strip() for n in cab[1].split(",")] if len(cab) > 1 else None
    pis = []
    for l in lineas[1:]:
        p = l.split()
        if len(p) >= 4:
            xy = (int(float(p[4])), int(float(p[5]))) if len(p) >= 6 else (0, 0)
            pis.append((int(p[0]), int(p[1]), p[2].upper(), "o" if p[3] == "o" else "a", *xy))
    return nombres, pis


def pisadas_de_carpeta(car):
    cand = [p for p in (os.path.join(car, "pisadas.txt"), os.path.join(car, "pisadas.json")) if os.path.isfile(p)]
    return max(cand, key=os.path.getmtime) if cand else None


def bailarines_de(texto):
    """«Sol:follower,London:leader» (sin papel: el 1.º follower, el 2.º leader)."""
    out = []
    for k, t in enumerate([t.strip() for t in texto.split(",") if t.strip()][:4]):
        nom, _, rol = t.partition(":")
        rol = (rol.strip() or ("follower" if k == 0 else "leader")).lower()
        out.append({"nombre": nom.strip(), "rol": rol})
    return out


def copia_ligera(video, destino):
    """720 px de ancho, con sonido, fotograma clave cada 10: saltar es instantáneo en el navegador."""
    if os.path.isfile(destino) and os.path.getmtime(destino) >= os.path.getmtime(video):
        return
    tmp = destino + ".tmp.mp4"
    subprocess.run([FF, "-v", "error", "-y", "-i", video, "-vf", "scale='min(720,iw)':-2", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "24", "-g", "10", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, destino)


def audio_de_cancion(carpeta):
    a = json.load(open(os.path.join(carpeta, "ritmo.json"), encoding="utf-8"))["meta"]["audio"]
    for r in (a, os.path.join(r"D:\Dropbox\TDJ\MUSICA", a), os.path.join(r"D:\Dropbox\TDJ", a)):
        if os.path.exists(r):
            return r
    raise SystemExit(f"No encuentro el audio de la canción: {a}")


def escribir(carpeta, videos):
    """video.json (lo que se guarda) y video_datos.js (lo que lee la página)."""
    json.dump({"videos": videos}, open(os.path.join(carpeta, "video.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    pag = []
    for v in videos:
        pis = []
        if v.get("pisadas_de") and os.path.isfile(v["pisadas_de"]):
            _, crudas = leer_pisadas(v["pisadas_de"])
            for n, b, pie, tipo, x, y in crudas:
                # el fotograma n del vídeo original → segundo de la grabación; x y = dónde está el pie (0 0 = no se sabe)
                pis.append([round(v["inicio"] + n / v["fps"] * v["velocidad"], 3), b, pie, tipo, x, y])
            pis.sort()
        bai = []
        cuenta = {"follower": 0, "leader": 0}
        for i, b in enumerate(v["bailarines"]):
            rol = b["rol"] if b["rol"] in COLORES else ("follower" if i % 2 == 0 else "leader")
            bai.append({"nombre": b["nombre"], "rol": rol, "color": COLORES[rol][cuenta[rol] % 2]}); cuenta[rol] += 1
        pag.append({"id": v["id"], "src": "_ritmo/" + os.path.basename(carpeta) + "/" + v["archivo"], "inicio": v["inicio"],
                    "velocidad": v["velocidad"], "fps": v["fps"], "dur": v["dur"], "ancho": v["ancho"], "alto": v["alto"],
                    "bailarines": bai, "pisadas": pis, "origen": v["origen"]})
    with open(os.path.join(carpeta, "video_datos.js"), "w", encoding="utf-8") as f:
        f.write("window.VIDEO = " + json.dumps({"videos": pag}, ensure_ascii=False) + ";\n")
    return pag


def main():
    ap = argparse.ArgumentParser(description="Vídeo de bailarines en la página de ritmo")
    ap.add_argument("carpeta", nargs="?")
    ap.add_argument("fuente", nargs="?", help="vídeo .mp4 o carpeta marcar_… de marcar_pisadas.py")
    ap.add_argument("--inicio", type=float)
    ap.add_argument("--velocidad", type=float)
    ap.add_argument("--id")
    ap.add_argument("--bailarines")
    ap.add_argument("--pisadas")
    ap.add_argument("--quitar")
    ap.add_argument("--todas", action="store_true")
    a = ap.parse_args()

    if a.todas:
        for j in sorted(glob.glob(os.path.join(RAIZ, "_ritmo", "*", "video.json"))):
            c = os.path.dirname(j)
            print(f"{os.path.basename(c)}: {len(escribir(c, json.load(open(j, encoding='utf-8'))['videos']))} vídeo(s)")
        return
    if not a.carpeta:
        ap.error("falta la carpeta de _ritmo de la canción")
    carpeta = os.path.abspath(a.carpeta)
    if not os.path.isfile(os.path.join(carpeta, "ritmo.json")):
        raise SystemExit(f"No es una carpeta de _ritmo (falta ritmo.json): {carpeta}")
    vj = os.path.join(carpeta, "video.json")
    videos = json.load(open(vj, encoding="utf-8"))["videos"] if os.path.isfile(vj) else []

    if a.quitar:
        videos = [v for v in videos if v["id"] != a.quitar]
    elif not a.fuente and (a.inicio is not None or a.velocidad or a.bailarines or a.pisadas):
        # corregir un vídeo que ya está (lo normal: el texto «VIDEO <id> inicio=…» de la página)
        vid = a.id or (videos[0]["id"] if len(videos) == 1 else None)
        v = next((v for v in videos if v["id"] == vid), None)
        if not v:
            raise SystemExit(f"¿Qué vídeo? Di cuál con --id ({', '.join(x['id'] for x in videos) or 'esta canción no tiene vídeos'})")
        if a.inicio is not None: v["inicio"] = round(a.inicio, 3)
        if a.velocidad: v["velocidad"] = a.velocidad
        if a.bailarines: v["bailarines"] = bailarines_de(a.bailarines)
        if a.pisadas: v["pisadas_de"] = os.path.abspath(a.pisadas)
    elif a.fuente:
        fuente = os.path.abspath(a.fuente)
        conf, pis_ruta = {}, None
        if os.path.isdir(fuente):                       # carpeta marcar_… (ya alineada por marcar_pisadas.py)
            conf = json.load(open(os.path.join(fuente, "config.json"), encoding="utf-8"))
            video = conf["video"]; pis_ruta = pisadas_de_carpeta(fuente)
        else:
            video = fuente
        vid = a.id or os.path.splitext(os.path.basename(video))[0]
        viejo = next((v for v in videos if v["id"] == vid), {})
        fps, dur, w, h = sondear(video)
        inicio = a.inicio if a.inicio is not None else conf.get("inicio", viejo.get("inicio"))
        vel = a.velocidad or viejo.get("velocidad") or 1.0
        if inicio is None:                              # alinear con la grabación de la página
            import alinear
            wav = os.path.join(carpeta, "_audio_video.wav")
            subprocess.run([FF, "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "44100", wav], check=True)
            print("Alineando el vídeo con la grabación…", flush=True)
            r = alinear.alinear(*alinear.rasgos(wav), *alinear.rasgos(audio_de_cancion(carpeta)))
            os.remove(wav)
            inicio, vel = r["inicio_en_cancion"], (a.velocidad or r["velocidad"])
            fino = (f" · afinado con {r['trozos_buenos']} trozos de 10 s, error {r['error_ms']} ms"
                    if "trozos_buenos" in r else " · SIN afinar (pocos trozos se parecen)")
            dudoso = r.get("correlacion_trozos", 0) < 0.6 and r["parecido"] < 1.0
            print(f"  empieza en {inicio:.3f} s · velocidad {vel:.5f} · parecido {r['parecido']:.2f}{fino}"
                  + ("  OJO: se parece poco, ¿es esta grabación? Comprobarlo en la página" if dudoso else ""))
        if a.bailarines:
            bai = bailarines_de(a.bailarines)
        elif viejo.get("bailarines"):
            bai = viejo["bailarines"]
        else:
            nombres = conf.get("bailarines") or (leer_pisadas(pis_ruta)[0] if pis_ruta else None) or ["Ella", "Él"]
            bai = bailarines_de(",".join(nombres))
        if a.pisadas:
            pis_ruta = os.path.abspath(a.pisadas)
        archivo = "video_" + "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in vid) + ".mp4"
        print("Copia ligera del vídeo…", flush=True)
        copia_ligera(video, os.path.join(carpeta, archivo))
        nuevo = {"id": vid, "origen": video, "archivo": archivo, "inicio": round(float(inicio), 3), "velocidad": float(vel),
                 "fps": fps, "dur": round(dur, 3), "ancho": w, "alto": h, "bailarines": bai,
                 "pisadas_de": pis_ruta or viejo.get("pisadas_de")}
        videos = [v for v in videos if v["id"] != vid] + [nuevo]

    pag = escribir(carpeta, videos)
    for v in pag:
        print(f"{v['id']}: empieza en {v['inicio']:.3f} s de la grabación · {v['dur']:.1f} s · {len(v['pisadas'])} pisadas · "
              + ", ".join(b["nombre"] for b in v["bailarines"]))
    import pathlib, urllib.parse
    sys.path.insert(0, AQUI)
    import pagina_ritmo
    pagina_ritmo.actualizar_indice(RAIZ)
    print("Página: " + pathlib.Path(RAIZ, "ritmo.html").as_uri() + "?c=" + urllib.parse.quote(os.path.basename(carpeta)))


if __name__ == "__main__":
    main()
