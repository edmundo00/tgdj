"""Pasa ritmo.py a TODAS las canciones de las milongas de Edmundo que aún no tienen página de ritmo.

Uso (python de venvs\\analizar_tango):
    python ritmo_todas.py              analiza las que faltan
    python ritmo_todas.py --lista      solo dice cuántas faltan (no analiza nada)
    python ritmo_todas.py --y-bajo     al acabar, pasa también transcripcion\\bajo_todas.py (~9 min por canción)
- Canciones = las de las listas de milonga (TDJ\\playlists\\AAMMDD_*.m3u) y el historial de VirtualDJ, sin cortinas.
- Prioridad baja, sin ventanas, no abre nada. Se puede cortar: al relanzarlo sigue con las que faltan
  (hecha = tiene _ritmo\\<canción>\\ritmo.json).
- Cómo va: Analisis tangos\\_ritmo\\_RITMO_ESTADO.txt. Log de cada una: _ritmo\\<canción>\\log_ritmo.txt.
- Solo en un PC a la vez (las dos copias escribirían en las mismas carpetas por Dropbox).
"""
import os, sys, glob, time, datetime, subprocess, argparse

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas
TDJ = rutas.TDJ
RITMO = os.path.join(TDJ, "Analisis tangos", "_ritmo")
ESTADO = os.path.join(RITMO, "_RITMO_ESTADO.txt")
BAJA = 0x00004000 | 0x08000000   # BELOW_NORMAL_PRIORITY_CLASS | CREATE_NO_WINDOW
EXT = (".flac", ".mp3", ".wav", ".m4a", ".ogg", ".opus", ".aif", ".aiff")


def listas():
    fs = sorted(glob.glob(os.path.join(TDJ, "playlists", "[0-9]*.m3u")))
    for h in (os.path.expandvars(r"%USERPROFILE%\Documents\VirtualDJ\History"),
              os.path.expandvars(r"%LOCALAPPDATA%\VirtualDJ\History")):
        fs += glob.glob(os.path.join(h, "**", "*.m3u"), recursive=True)
    return fs


def canciones():
    """{ruta: veces pinchada}, sin cortinas, en orden de más a menos pinchada."""
    veces = {}
    for f in listas():
        txt = None
        for enc in ("utf-8-sig", "cp1252"):
            try:
                txt = open(f, encoding=enc).read()
                break
            except UnicodeDecodeError:
                pass
        for l in (txt or "").splitlines():
            l = l.strip()
            if not l or l.startswith("#") or "cortina" in l.lower() or not l.lower().endswith(EXT):
                continue
            veces[l] = veces.get(l, 0) + 1
    return dict(sorted(veces.items(), key=lambda kv: -kv[1]))


def _clave(s):
    import re, unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


_HECHAS = None


def hecha(ruta, releer=False):
    """¿Tiene ya ritmo.json? Compara sin acentos, espacios ni signos (algunas carpetas se llaman un poco distinto)."""
    global _HECHAS
    if _HECHAS is None or releer:
        _HECHAS = {_clave(c) for c in os.listdir(RITMO) if os.path.exists(os.path.join(RITMO, c, "ritmo.json"))}
    return _clave(os.path.splitext(os.path.basename(ruta))[0]) in _HECHAS


def escribir_estado(hechas, total, fallos, sin_audio, t0, ahora, fin=False):
    falta = total - hechas - len(fallos)
    media = (time.time() - t0) / max(1, hechas + len(fallos))
    eta = datetime.datetime.now() + datetime.timedelta(seconds=media * falta)
    txt = [("TERMINADO" if fin else "EN MARCHA (se puede cortar: al relanzar sigue con las que faltan)"),
           f"Ritmo de las canciones de las milongas · {datetime.datetime.now():%d-%m-%Y %H:%M}",
           "", f"Hechas en esta tanda: {hechas} de {total} · fallan: {len(fallos)} · faltan: {falta}",
           f"Media: {media / 60:.1f} min por canción" + ("" if fin or not hechas else f" · fin estimado: {eta:%A %d-%m %H:%M}")]
    if ahora and not fin:
        txt += ["", f"Ahora: {ahora}"]
    if fallos:
        txt += ["", "Fallan (mirar log_ritmo.txt en su carpeta de _ritmo):"] + [f"  {c}" for c in fallos]
    if sin_audio:
        txt += ["", "Sin audio en este PC (no se pueden hacer aquí):"] + [f"  {c}" for c in sin_audio]
    open(ESTADO, "w", encoding="utf-8").write("\n".join(txt) + "\n")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="ritmo.py para todas las canciones de las milongas")
    ap.add_argument("--lista", action="store_true", help="solo contar")
    ap.add_argument("--y-bajo", action="store_true", help="al acabar, pasar bajo_todas.py")
    a = ap.parse_args()

    todas = canciones()
    faltan = [r for r in todas if not hecha(r)]
    lista, vistos = [], set()   # la misma canción puede estar en dos carpetas: una sola vez
    for r in faltan:
        k = os.path.splitext(os.path.basename(r))[0].strip().lower()
        if os.path.exists(r) and k not in vistos:
            vistos.add(k)
            lista.append(r)
    sin_audio = [os.path.basename(r) for r in faltan if not os.path.exists(r)]
    print(f"{len(todas)} canciones en las milongas · {len(todas) - len(faltan)} ya con ritmo · "
          f"faltan {len(lista)} · {len(sin_audio)} sin audio en este PC", flush=True)
    if a.lista:
        for r in lista:
            print(f"  {todas[r]:3d}  {os.path.basename(r)}")
        return

    env = dict(os.environ, TDJ_SIN_PAUSA="1", PYTHONIOENCODING="utf-8")
    t0, hechas, fallos = time.time(), 0, []
    for r in lista:
        nombre = os.path.splitext(os.path.basename(r))[0]
        escribir_estado(hechas, len(lista), fallos, sin_audio, t0, nombre)
        os.makedirs(os.path.join(RITMO, nombre), exist_ok=True)
        log = os.path.join(RITMO, nombre, "log_ritmo.txt")
        t = time.time()
        with open(log, "w", encoding="utf-8") as f:
            p = subprocess.run([sys.executable, "-X", "utf8", "-W", "ignore", os.path.join(AQUI, "ritmo.py"), r],
                               stdout=f, stderr=subprocess.STDOUT, env=env,
                               creationflags=BAJA if os.name == "nt" else 0)
        if p.returncode == 0 and hecha(r, releer=True):
            hechas += 1
            print(f"[{hechas + len(fallos)}/{len(lista)}] {nombre}: {time.time() - t:.0f} s", flush=True)
        else:
            fallos.append(nombre)
            print(f"[{hechas + len(fallos)}/{len(lista)}] {nombre}: FALLA (ver {log})", flush=True)
    escribir_estado(hechas, len(lista), fallos, sin_audio, t0, None, fin=True)
    print("TERMINADO", flush=True)

    if a.y_bajo:
        print("Ahora el bajo (bajo_todas.py)…", flush=True)
        subprocess.run([sys.executable, "-X", "utf8", os.path.join(AQUI, "transcripcion", "bajo_todas.py")],
                       creationflags=BAJA if os.name == "nt" else 0)


if __name__ == "__main__":
    main()
