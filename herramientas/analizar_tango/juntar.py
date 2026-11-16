"""Juntar 2, 3 o 4 canciones para compararlas y alternarlas (como Carmen y la Milonga del 900 en el reel de la habanera).

Uso:
    juntar.bat "cancion1.flac" "cancion2.flac" [cancion3] [cancion4]
Si alguna canción no tiene análisis de ritmo, se hace antes (como ritmo.bat).
Mide la tónica y la afinación de cada una (para el botón «sincronizar tiempo y tónica»)
y crea Analisis tangos\\_juntar\\<nombres>\\juntar.html con todo dentro, que se abre sola.
"""
import os, sys, json, argparse
import numpy as np, librosa

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ritmo, pagina_ritmo

AQUI = os.path.dirname(os.path.abspath(__file__))
NOTAS = ["Do", "Do#", "Re", "Mib", "Mi", "Fa", "Fa#", "Sol", "Lab", "La", "Sib", "Si"]
# perfiles de Krumhansl-Kessler
MAY = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MEN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def tonalidad(audio):
    sr = 22050
    y = ritmo.cargar_audio(audio, sr)
    afin = float(librosa.estimate_tuning(y=y, sr=sr))           # en fracción de semitono
    c = librosa.feature.chroma_cqt(y=y, sr=sr, tuning=afin).mean(axis=1)
    mejor = None
    for t in range(12):
        for modo, perfil in (("mayor", MAY), ("menor", MEN)):
            r = float(np.corrcoef(np.roll(perfil, t), c)[0, 1])
            if mejor is None or r > mejor[0]:
                mejor = (r, t, modo)
    r, t, modo = mejor
    croma = (c / (np.linalg.norm(c) + 1e-9)).round(4).tolist()
    # notas cada medio segundo, para comparar solo los trozos que se juntan
    cf = librosa.feature.chroma_cqt(y=y, sr=sr, tuning=afin, hop_length=11025)
    croma_t = [[round(float(v), 3) for v in col] for col in cf.T]
    return dict(tonica=NOTAS[t], indice=t, modo=modo, afinacion_cents=round(afin * 100), seguridad=round(r, 2), croma=croma, croma_t=croma_t, croma_paso=0.5)


def preparar(audio):
    nombre = os.path.splitext(os.path.basename(audio))[0]
    f = os.path.join(ritmo.SALIDA_DEF, "_ritmo", nombre, "ritmo.json")
    if not os.path.exists(f):
        print(f"· Analizando el ritmo de {nombre}…", flush=True)
        ritmo.analizar(audio, dict(abrir=False))
    d = json.load(open(f, encoding="utf-8"))
    print(f"· Tónica de {nombre}…", flush=True)
    ton = tonalidad(audio)
    unos = [p["seg"] for p in d["pulsos"] if p["tiempo"] == 1]
    return dict(nombre=nombre, audio=audio, meta=d["meta"], tonalidad=ton,
                compas_seg=float(np.median(np.diff(unos))) if len(unos) > 2 else 2.0,
                pulsos=d["pulsos"], golpes=d["golpes"],
                dibujos=[dict(nombre=x["nombre"], tramos=x["tramos"][:6]) for x in d["dibujos"] if x["tramos"]],
                sonido=pagina_ritmo._opus_b64(audio, 64))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Juntar 2-4 canciones")
    ap.add_argument("audio", nargs="+")
    ap.add_argument("--abrir", action="store_true", help="abrir la página al terminar (solo lo pone el .bat; Claude nunca)")
    ap.add_argument("--no-abrir", action="store_true", help="(obsoleto: ya no se abre salvo con --abrir)")
    a = ap.parse_args()
    if not 2 <= len(a.audio) <= 4:
        sys.exit("Hacen falta entre 2 y 4 canciones.")
    canciones = [preparar(f) for f in a.audio]
    titulo = " + ".join(c["nombre"] for c in canciones)
    carpeta = os.path.join(ritmo.SALIDA_DEF, "_juntar", " + ".join(c["nombre"][:40] for c in canciones))
    os.makedirs(carpeta, exist_ok=True)
    html = open(os.path.join(AQUI, "juntar_plantilla.html"), encoding="utf-8").read()
    html = html.replace("/*CANCIONES*/null", json.dumps(canciones, ensure_ascii=False)).replace("<!--TITULO-->", titulo)
    ruta = os.path.join(carpeta, "juntar.html")
    open(ruta, "w", encoding="utf-8").write(html)
    for c in canciones:
        t = c["tonalidad"]
        print(f"  {c['nombre']}: {c['meta']['compas']}, compás de {c['compas_seg']:.3f} s, {t['tonica']} {t['modo']} ({t['afinacion_cents']:+d} cents)")
    pagina_ritmo.actualizar_indice(ritmo.SALIDA_DEF)
    print(f"Hecho → {ruta}")
    if a.abrir and os.name == "nt":
        os.startfile(ruta)


if __name__ == "__main__":
    main()
