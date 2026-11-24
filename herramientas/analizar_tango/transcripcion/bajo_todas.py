"""Pasa el bajo de YourMT3+ (bajo_lupa.py) a TODAS las canciones con página de ritmo que aún no lo tienen.

Uso (python de venvs\\analizar_tango):  python bajo_todas.py
- ~10 min por canción en el procesador, con prioridad baja (se puede seguir usando el PC).
- Se puede cortar cuando se quiera: al relanzarlo sigue con las que faltan (las hechas tienen bajo_datos.js).
- Cómo va: Analisis tangos\\_ritmo\\_BAJO_ESTADO.txt (hechas, faltan, hora estimada de fin, fallos).
- Solo en un PC a la vez (las dos copias escribirían en las mismas carpetas por Dropbox).
"""
import os, sys, json, time, subprocess, datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rutas
RAIZ = rutas.ANALISIS
RITMO = os.path.join(RAIZ, "_ritmo")
ESTADO = os.path.join(RITMO, "_BAJO_ESTADO.txt")
BAJA = 0x00004000   # BELOW_NORMAL_PRIORITY_CLASS


def audio_de(a):
    # algunos análisis guardaron la ruta relativa (a MUSICA o a TDJ), como en pagina_ritmo.py
    for r in (a, os.path.join(rutas.MUSICA, a), os.path.join(rutas.TDJ, a)):
        if r and os.path.exists(r):
            return r
    return None


def pendientes():
    out, sin_audio = [], []
    for c in sorted(os.listdir(RITMO)):
        d = os.path.join(RITMO, c)
        if not os.path.isdir(d) or os.path.exists(os.path.join(d, "bajo_datos.js")):
            continue
        try:
            a = audio_de(json.load(open(os.path.join(d, "ritmo.json"), encoding="utf-8"))["meta"]["audio"])
        except Exception:
            a = None
        (out if a else sin_audio).append((c, a))
    return out, sin_audio


def escribir_estado(hechas, total, fallos, sin_audio, t0, ahora_con, fin=False):
    falta = total - hechas - len(fallos)
    media = (time.time() - t0) / max(1, hechas + len(fallos))
    eta = datetime.datetime.now() + datetime.timedelta(seconds=media * falta)
    txt = [("TERMINADO" if fin else "EN MARCHA (se puede cortar: al relanzar sigue con las que faltan)"),
           f"Bajo de YourMT3+ para la página de ritmo · {datetime.datetime.now():%d-%m-%Y %H:%M}",
           "", f"Hechas en esta tanda: {hechas} de {total} · fallan: {len(fallos)} · faltan: {falta}",
           f"Media: {media / 60:.1f} min por canción" + ("" if fin or not hechas else f" · fin estimado: {eta:%A %d-%m %H:%M}")]
    if ahora_con and not fin:
        txt += ["", f"Ahora: {ahora_con}"]
    if fallos:
        txt += ["", "Fallan (mirar log_bajo.txt en su carpeta):"] + [f"  {c}" for c in fallos]
    if sin_audio:
        txt += ["", "Sin audio en este PC (no se pueden hacer aquí):"] + [f"  {c}" for c, _ in sin_audio]
    open(ESTADO, "w", encoding="utf-8").write("\n".join(txt) + "\n")


def main():
    lista, sin_audio = pendientes()
    print(f"{len(lista)} canciones sin bajo · {len(sin_audio)} sin audio en este PC", flush=True)
    t0, hechas, fallos = time.time(), 0, []
    for c, a in lista:
        escribir_estado(hechas, len(lista), fallos, sin_audio, t0, c)
        log = os.path.join(RITMO, c, "log_bajo.txt")
        t = time.time()
        with open(log, "w", encoding="utf-8") as f:
            r = subprocess.run([sys.executable, "-X", "utf8", "-W", "ignore", os.path.join(AQUI, "bajo_lupa.py"), a, "--ritmo", c],
                               stdout=f, stderr=subprocess.STDOUT, creationflags=BAJA if os.name == "nt" else 0)
        if r.returncode == 0 and os.path.exists(os.path.join(RITMO, c, "bajo_datos.js")):
            hechas += 1
            print(f"[{hechas + len(fallos)}/{len(lista)}] {c}: {time.time() - t:.0f} s", flush=True)
        else:
            fallos.append(c)
            print(f"[{hechas + len(fallos)}/{len(lista)}] {c}: FALLA (ver {log})", flush=True)
    escribir_estado(hechas, len(lista), fallos, sin_audio, t0, None, fin=True)
    print("TERMINADO", flush=True)


if __name__ == "__main__":
    main()
