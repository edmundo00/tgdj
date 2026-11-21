"""Analiza un tango entero: separa instrumentos, encuentra pulso y compases, mide cada golpe y su fuerza.

Uso:
    analizar_tango.bat "D:\\Dropbox\\TDJ\\MUSICA\\...\\Juan D'arienzo - El Flete.flac"
    (opcional) --salida "carpeta"

Para verlo: al terminar se le pasa solo ritmo.py (que aprovecha las pistas separadas) y sale en
HERRAMIENTAS.html con su botón «▶ Ritmo». El visor viejo con gráficas se quitó el 19-11-2026.
Los datos de cada tango se guardan en Analisis tangos\\_datos\\<canción> (las carpetas antiguas de la raíz se respetan):
    resumen.txt      compás a compás: dibujo de golpes de cada instrumento y sucesos (pianitos, silencios, síncopas…)
    compases.csv     lo mismo en tabla (se abre con Excel)
    golpes.csv       cada golpe: instrumento, segundo, compás, tiempo, semicorchea, adelanto/retraso en ms, fuerza en dB
    pulsos.csv       segundo de cada tiempo, con su compás
    articulacion.txt cortado o ligado: cuánto baja el sonido entre golpes, compás a compás (articulacion.py)
    pistas\\         contrabajo, piano, voz, bandoneones, violines, resto y mezcla
"""
import os, sys, argparse, time
import numpy as np, librosa, soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ffmpeg: si no está en el PATH (p. ej. el PC del trabajo), buscarlo en las carpetas de siempre (como ritmo.py)
import shutil
if not shutil.which("ffmpeg"):
    for _d in (r"C:\ffmpeg\bin", os.path.expandvars(r"%USERPROFILE%\herramientas\ffmpeg\bin")):
        if os.path.isfile(os.path.join(_d, "ffmpeg.exe")):
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            break

import separar, pulso, golpes as golpes_mod, informe, articulacion

SALIDA_DEF = r"D:\Dropbox\TDJ\Analisis tangos"
MODELOS = os.path.join(os.path.expanduser("~"), "venvs", "modelos_separador")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Analiza un tango por instrumentos y golpes")
    ap.add_argument("audio", nargs="+", help="uno o varios archivos de audio")
    ap.add_argument("--salida", help="carpeta de salida (solo con un archivo)")
    ap.add_argument("--rapido", action="store_true",
                    help="sin separar instrumentos: solo pulso, compases y grandes golpes de la orquesta entera (segundos por tango)")
    a = ap.parse_args()
    for i, f in enumerate(a.audio, 1):
        if len(a.audio) > 1:
            print(f"\n=== {i}/{len(a.audio)}: {os.path.basename(f)}", flush=True)
        try:
            (analizar_rapido if a.rapido else analizar_uno)(f, a.salida if len(a.audio) == 1 else None)
        except Exception as e:
            print(f"ERROR con {f}: {e}", flush=True)
    if not a.salida:
        # la página para verlo: ritmo.py, que aprovecha las pistas recién separadas (19-11-2026)
        import subprocess
        ritmo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ritmo.py")
        for f in a.audio:
            print(f"\nPágina de ritmo de {os.path.basename(f)}…", flush=True)
            subprocess.run([sys.executable, ritmo, f])


def analizar_uno(audio, salida):
    class _A: pass
    a = _A(); a.audio, a.salida = audio, salida
    nombre = os.path.splitext(os.path.basename(a.audio))[0]
    antigua = os.path.join(SALIDA_DEF, nombre)          # análisis hechos antes de existir _datos
    out = a.salida or (antigua if os.path.isdir(antigua) else os.path.join(SALIDA_DEF, "_datos", nombre))
    dir_p = os.path.join(out, "pistas")
    os.makedirs(dir_p, exist_ok=True)
    t0 = time.time()

    print("1/4 Separando instrumentos (la primera vez tarda unos minutos)…", flush=True)
    pistas = separar.separar(a.audio, dir_p, MODELOS)
    sr = separar.SR
    mezcla, _ = librosa.load(a.audio, sr=sr, mono=True)
    pistas["mezcla"] = mezcla
    aprox = pistas.pop("_contrabajo_aprox", False)
    if not os.path.exists(os.path.join(dir_p, "mezcla.flac")):
        sf.write(os.path.join(dir_p, "mezcla.flac"), mezcla, sr)

    print("2/4 Buscando pulso y compases…", flush=True)
    P = pulso.compases(mezcla, pistas["contrabajo"], sr)
    P["contrabajo_aprox"] = aprox
    if aprox:
        print("    (el contrabajo no salía separado: se ha sacado filtrando los graves, es aproximado)", flush=True)
    print(f"    {P['bpm']:.0f} pulsos/min, {int(P['compas'].max())} compases", flush=True)

    print("3/4 Midiendo golpes…", flush=True)
    g, niveles = golpes_mod.analizar(pistas, sr, P)
    filas = golpes_mod.resumen_compases(g, niveles, P)
    g += golpes_mod.orquesta(mezcla, sr, P)   # fila «Orquesta entera» del visor (sobre la mezcla, sin separar)

    print("4/4 Escribiendo resultados…", flush=True)
    informe.guardar_todo(out, nombre, P, g, niveles, filas)
    articulacion.guardar(out, mezcla, sr, P["beats"], P["compas"])
    print(f"Hecho en {time.time() - t0:.0f} s → {out}")


def analizar_rapido(audio, salida):
    """Sin separar instrumentos: pulso, compases y grandes golpes de la orquesta entera.
    Para ver la síncopa basta (y no se cuela el error del separador). Si ya había un análisis
    completo de este tango, no se toca: se le añade la fila «Orquesta entera» volviendo a analizarlo entero."""
    nombre = os.path.splitext(os.path.basename(audio))[0]
    antigua = os.path.join(SALIDA_DEF, nombre)
    out = salida or (antigua if os.path.isdir(antigua) else os.path.join(SALIDA_DEF, "_datos", nombre))
    if os.path.exists(os.path.join(out, "resumen.txt")) and os.path.exists(os.path.join(out, "pistas", "contrabajo.flac")):
        print("    ya tiene análisis completo; lo rehago entero para añadir la fila de la orquesta", flush=True)
        return analizar_uno(audio, salida)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    sr = separar.SR
    mezcla, _ = librosa.load(audio, sr=sr, mono=True)
    print("1/3 Buscando pulso y compases…", flush=True)
    P = pulso.compases(mezcla, mezcla, sr)
    print(f"    {P['bpm']:.0f} pulsos/min, {int(P['compas'].max())} compases", flush=True)
    print("2/3 Midiendo los grandes golpes de la orquesta…", flush=True)
    g = golpes_mod.orquesta(mezcla, sr, P)
    print("3/3 Escribiendo resultados…", flush=True)
    dir_e = os.path.join(out, "escuchar")   # solo la mezcla: la usa articulacion.py cuando no hay pistas
    os.makedirs(dir_e, exist_ok=True)
    f = os.path.join(dir_e, "mezcla.ogg")
    if not os.path.exists(f) or os.path.getsize(f) < 10000:
        y = np.clip(mezcla, -1, 1).astype("float32")
        with sf.SoundFile(f, "w", sr, 1, format="OGG", subtype="VORBIS") as o:
            for i in range(0, len(y), sr):
                o.write(y[i:i + sr])
    informe._csv(os.path.join(out, "golpes.csv"), g)
    informe._csv(os.path.join(out, "pulsos.csv"), [dict(seg=round(float(b), 3), compas=int(c), tiempo=int(t))
                                                   for b, c, t in zip(P["beats"], P["compas"], P["tiempo"])])
    articulacion.guardar(out, mezcla, sr, P["beats"], P["compas"])
    print(f"Hecho en {time.time() - t0:.0f} s → {out}")


if __name__ == "__main__":
    main()
