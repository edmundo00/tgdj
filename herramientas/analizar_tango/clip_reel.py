r"""CLIP PARA UN REEL desde la página de ritmo (19-11-2026).

En la página: elige un trozo (arrastrando o «repetir de N a M»), y en «Herramientas → El trozo elegido» pulsa
«💾 Guardar el trozo». Baja un tramo_<canción>_<segundo>.json a Descargas. Luego:

    clip_reel.bat  (arrastrar el .json encima)           o
    python clip_reel.py "tramo_….json" [--lento 0.5] [--video ruta.mp4] [--salida x.mp4]
    python clip_reel.py --ultimo                          el tramo_*.json más reciente de Descargas

Hace un MP4 vertical 1080×1920 a 30 fps con el vídeo de los bailarines (si la página tenía uno) cuadrado con el
DISCO (el sonido bueno, no el del móvil), a la velocidad a la que se estaba escuchando (o la de --lento, con el mismo
tono). Sin vídeo, saca solo el sonido (.m4a). Salida: Instagram\borradores\_clips\.
Para un vídeo subido desde la página (no está en Dropbox), lo busca por su nombre en Descargas, Vídeos y Escritorio;
si no, --video ruta.
"""
import os, sys, json, glob, shutil, argparse, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas
FF, FP = rutas.preparar_ffmpeg()
SALIDA = os.path.join(rutas.TDJ, "Instagram", "borradores", "_clips")
CASA = os.path.expanduser("~")


def ruta_audio(a):
    r = rutas.buscar_audio(a)
    if r:
        return r
    raise SystemExit(f"No encuentro la grabación: {a}")


def busca_video(v, dado):
    if dado:
        return dado
    if not v:
        return None
    if v.get("origen") and os.path.exists(v["origen"]):
        return v["origen"]
    if v.get("nombre"):
        for d in ("Downloads", "Descargas", "Videos", "Vídeos", "Desktop", "Escritorio"):
            for r in glob.glob(os.path.join(CASA, d, "**", v["nombre"]), recursive=True):
                return r
    raise SystemExit(f"No encuentro el vídeo «{v.get('nombre') or v.get('id')}»: dímelo con --video ruta.mp4")


def duracion(f):
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def atempo(x):
    """atempo solo admite 0,5–2: se encadena."""
    out = []
    while x < 0.5:
        out.append("atempo=0.5"); x /= 0.5
    out.append(f"atempo={x:.5f}")
    return ",".join(out)


def main():
    ap = argparse.ArgumentParser(description="Clip para un reel con el trozo elegido en la página de ritmo")
    ap.add_argument("tramo", nargs="?")
    ap.add_argument("--ultimo", action="store_true")
    ap.add_argument("--lento", type=float)
    ap.add_argument("--video")
    ap.add_argument("--sin-video", action="store_true")
    ap.add_argument("--salida")
    a = ap.parse_args()
    if a.ultimo or not a.tramo:
        cand = glob.glob(os.path.join(CASA, "Downloads", "tramo_*.json"))
        if not cand:
            raise SystemExit("No hay ningún tramo_*.json en Descargas: guárdalo antes desde la página («💾 Guardar el trozo»)")
        a.tramo = max(cand, key=os.path.getmtime)
    d = json.load(open(a.tramo, encoding="utf-8"))
    t0, t1 = float(d["desde_seg"]), float(d["hasta_seg"])
    lento = a.lento or float(d.get("velocidad_escucha") or 1)
    audio = ruta_audio(d["audio"])
    v = None if a.sin_video else d.get("video")
    vid = None if a.sin_video else busca_video(v, a.video)
    os.makedirs(SALIDA, exist_ok=True)
    nombre = f"{d.get('carpeta') or d['cancion']}_c{d.get('compas_inicio', 0)}" + (f"_{int(round(lento * 100))}pc" if lento != 1 else "")
    nombre = "".join(ch if ch.isalnum() or ch in " -_.()," else "_" for ch in nombre)
    out = a.salida or os.path.join(SALIDA, nombre + (".mp4" if vid else ".m4a"))
    af = f"[1:a]{atempo(lento)}[a]" if vid else f"[0:a]{atempo(lento)}[a]"
    if vid:
        vel = float(v.get("velocidad") or 1) if v else 1.0
        ini = float(v["inicio"]) if v else 0.0
        v0, dv = (t0 - ini) / vel, (t1 - t0) / vel
        dur = duracion(vid)
        if v0 < -0.05 or v0 + dv > dur + 0.05:
            raise SystemExit(f"El trozo ({t0:.2f}–{t1:.2f} s) no está dentro del vídeo, que va de {ini:.2f} a {ini + dur * vel:.2f} s de la grabación")
        v0 = max(0.0, v0)
        k = vel / lento          # el vídeo se estira para durar lo que el trozo de disco, y luego lo de la cámara lenta
        vf = (f"[0:v]setpts=(PTS-STARTPTS)*{k:.6f},scale=1080:1920:force_original_aspect_ratio=decrease,"
              f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,format=yuv420p[v]")
        cmd = [FF, "-v", "error", "-y", "-ss", f"{v0:.3f}", "-t", f"{dv:.3f}", "-i", vid, "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", audio,
               "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out]
    else:
        cmd = [FF, "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", audio, "-filter_complex", af, "-map", "[a]",
               "-c:a", "aac", "-b:a", "192k", out]
    subprocess.run(cmd, check=True)
    import pathlib
    print(f"Trozo {t0:.2f}–{t1:.2f} s (compás {d.get('compas_inicio')}) a {lento:.0%}" + ("" if vid else " · sin vídeo: solo sonido"))
    print("LISTO: " + pathlib.Path(out).as_uri())


if __name__ == "__main__":
    main()
