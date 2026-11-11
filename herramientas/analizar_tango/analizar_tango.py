"""Analiza un tango entero: separa instrumentos, encuentra pulso y compases, mide cada golpe y su fuerza.

Uso:
    analizar_tango.bat "D:\\Dropbox\\TDJ\\MUSICA\\...\\Juan D'arienzo - El Flete.flac"
    (opcional) --salida "carpeta"

Para ver los análisis: abre D:\\Dropbox\\TDJ\\Analisis tangos\\visor.html y busca el tango.
Los datos de cada tango se guardan en Analisis tangos\\_datos\\<canción> (las carpetas antiguas de la raíz se respetan):
    resumen.txt      compás a compás: dibujo de golpes de cada instrumento y sucesos (pianitos, silencios, síncopas…)
    compases.csv     lo mismo en tabla (se abre con Excel)
    golpes.csv       cada golpe: instrumento, segundo, compás, tiempo, semicorchea, adelanto/retraso en ms, fuerza en dB
    pulsos.csv       segundo de cada tiempo, con su compás
    graficas\\       una imagen cada 8 compases
    datos.js         lo que lee el visor
    escuchar\\       copias ligeras (OGG) de las pistas para el visor
    pistas\\         contrabajo, piano, voz, bandoneones, violines, resto y mezcla
"""
import os, sys, argparse, time
import numpy as np, librosa, soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import separar, pulso, golpes as golpes_mod, informe

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
    a = ap.parse_args()
    for i, f in enumerate(a.audio, 1):
        if len(a.audio) > 1:
            print(f"\n=== {i}/{len(a.audio)}: {os.path.basename(f)}", flush=True)
        try:
            analizar_uno(f, a.salida if len(a.audio) == 1 else None)
        except Exception as e:
            print(f"ERROR con {f}: {e}", flush=True)
    n = informe.actualizar_visor(SALIDA_DEF)
    print(f"\nVisor: {os.path.join(SALIDA_DEF, 'visor.html')} ({n} tangos analizados)", flush=True)


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

    print("4/4 Escribiendo resultados…", flush=True)
    # copias ligeras en OGG para la página (el navegador salta mejor en OGG que en FLAC grandes)
    dir_e = os.path.join(out, "escuchar")
    os.makedirs(dir_e, exist_ok=True)
    rel = []
    for etiqueta, n in [("Mezcla completa", "mezcla"), ("Contrabajo", "contrabajo"), ("Piano", "piano"),
                        ("Marcato (sobre todo bandoneones)", "bandoneones"), ("Ligado (violines y bandoneones)", "violines"), ("Voz", "voz")]:
        f = os.path.join(dir_e, f"{n}.ogg")
        if not os.path.exists(f) or os.path.getsize(f) < 10000:
            y = np.clip(pistas[n], -1, 1).astype("float32")
            with sf.SoundFile(f, "w", sr, 1, format="OGG", subtype="VORBIS") as o:
                for i in range(0, len(y), sr):  # por trozos: de una vez libsndfile falla con archivos largos
                    o.write(y[i:i + sr])
        rel.append([etiqueta, f"escuchar/{n}.ogg"])
    informe.guardar_todo(out, nombre, P, g, niveles, filas, rel)
    print(f"Hecho en {time.time() - t0:.0f} s → {out}")


if __name__ == "__main__":
    main()
