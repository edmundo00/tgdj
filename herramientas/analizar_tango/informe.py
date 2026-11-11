"""Paso 4: lo que se entrega por cada tango: tablas, resumen en texto, gráficas y página para escuchar."""
import os, csv, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"contrabajo": "#c98a3a", "piano": "#f1d58a", "bandoneones": "#d9a441", "violines": "#9fb8c9", "voz": "#c99ab5"}
FONDO = "#17130f"


def _csv(ruta, filas):
    if not filas:
        return
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), delimiter=";")
        w.writeheader(); w.writerows(filas)


def resumen_txt(ruta, titulo, P, filas):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(f"{titulo}\n{len(filas)} compases · {P['bpm']:.0f} pulsos por minuto\n")
        if P.get("contrabajo_aprox"):
            f.write("OJO: el separador no sacó el contrabajo (grabación con pocos graves); se ha sacado filtrando los graves y es aproximado.\n")
        f.write("\n")
        f.write("Cada compás: 1 e y a | 2 e y a | 3 e y a | 4 e y a    X fuerte  x medio  - flojo  · nada\n")
        f.write("marcato = golpes cortados y acentuados (sobre todo bandoneones)\n")
        f.write("ligado  = lo sostenido (violines, y bandoneones cuando tocan ligado), por corchea: = fuerte  ~ suave  · nada\n\n")
        for r in filas:
            f.write(f"Compás {r['compas']:3d}  (seg. {r['seg']:6.2f}){'  · canta' if r['voz'] else ''}\n")
            for n, et in [("contrabajo", "contrabajo"), ("piano", "piano"), ("bandoneones", "marcato")]:
                f.write(f"   {et:<12} {r[n]}\n")
            v = r["violines"]
            f.write(f"   {'ligado':<12} {v[0:2]}   {v[2:4]}   {v[4:6]}   {v[6:8]}\n")
            if r["sucesos"]:
                f.write(f"   → {r['sucesos']}\n")
            f.write("\n")


def graficas(dir_out, golpes, niveles, P, por_imagen=8):
    beats, comp = P["beats"], P["compas"]
    orden = ["voz", "violines", "bandoneones", "piano", "contrabajo"]
    primeros = [i for i in range(len(beats)) if P["tiempo"][i] == 1 and comp[i] >= 1]
    rutas = []
    for g0 in range(0, len(primeros), por_imagen):
        i0 = primeros[g0]
        i1 = min(len(beats) - 1, i0 + 4 * por_imagen)
        fig, ax = plt.subplots(figsize=(18, 4.8), facecolor=FONDO)
        ax.set_facecolor(FONDO)
        for k in range(i0, i1 + 1):
            fuerte = P["tiempo"][k] == 1
            ax.axvline(k, color="#efe6d6" if fuerte else "#5a4d3e", lw=1.5 if fuerte else 0.7, zorder=0)
            for s in (0.25, 0.5, 0.75):
                ax.axvline(k + s, color="#2c251e", lw=0.5, zorder=0)
        for i, n in enumerate(orden):
            if n in ("violines", "voz"):
                for q in range(i0 * 2, min(i1 * 2, len(niveles[n]))):
                    nv = max(0, (niveles[n][q] + 30) / 30)
                    ax.barh(i, 0.5, left=q / 2, height=0.55 * nv + 0.02, color=COL[n], alpha=0.2 + 0.6 * nv)
                continue
            for g in golpes:
                if g["pista"] == n and i0 <= g["pos"] <= i1:
                    a = 10 ** (min(g["fuerza_db"], 0) / 20)
                    ax.scatter(g["pos"] + g["desvio_ms"] / 1000 / (60 / P["bpm"]), i, s=15 + 420 * a,
                               color=COL[n], alpha=0.35 + 0.65 * a, edgecolors="none")
        ax.set_yticks(range(len(orden)), [{"bandoneones": "MARCATO", "violines": "LIGADO"}.get(o, o.upper()) for o in orden], color="#efe6d6", fontsize=11)
        ax.set_xticks(range(i0, i1 + 1), [f"C{comp[k]}" if P["tiempo"][k] == 1 else str(P["tiempo"][k]) for k in range(i0, i1 + 1)],
                      color="#a89a85", fontsize=9)
        ax.set_xlim(i0 - 0.3, i1 + 0.1); ax.set_ylim(-0.7, len(orden) - 0.3)
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.set_title(f"Compases {comp[i0]}–{comp[min(i1, len(comp) - 1)] - (0 if i1 == len(beats) - 1 else 1)} · tamaño = fuerza · "
                     "ligado y voz: grosor = cuánto suenan", color="#d9a441", loc="left")
        plt.tight_layout()
        r = os.path.join(dir_out, f"compases_{comp[i0]:03d}.png")
        plt.savefig(r, dpi=100); plt.close(fig)
        rutas.append(r)
    return rutas


def datos_visor(ruta, titulo, P, golpes, pistas_rel, niveles=None, filas=None):
    """datos.js: lo que lee el visor único (se carga con <script>, así funciona abriendo el .html sin servidor)."""
    niveles = niveles or {}
    datos = dict(titulo=titulo, bpm=round(float(P["bpm"])), beats=[round(float(b), 3) for b in P["beats"]],
                 compas=P["compas"].tolist(), tiempo=P["tiempo"].tolist(),
                 # [pista, segundo exacto, posición en pulsos redondeada a semicorchea, fuerza dB]
                 golpes=[[g["pista"], g["seg"], g["pos"], g["fuerza_db"]] for g in golpes],
                 violines=[round(float(v), 1) for v in niveles.get("violines", [])],
                 voz=[round(float(v), 1) for v in niveles.get("voz", [])],
                 sucesos={str(f["compas"]): f["sucesos"] for f in (filas or []) if f.get("sucesos")},
                 canta=[f["compas"] for f in (filas or []) if f.get("voz")],
                 contrabajo_aprox=bool(P.get("contrabajo_aprox")),
                 pistas=pistas_rel)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("ANALISIS(" + json.dumps(datos, ensure_ascii=False) + ");\n")


def actualizar_visor(raiz):
    """Copia el visor a la raíz y rehace indice.js con todos los análisis que tengan datos.js
    (los de _datos y las carpetas antiguas de la raíz)."""
    import glob, shutil
    tangos = []
    for f in sorted(glob.glob(os.path.join(raiz, "*", "datos.js")) + glob.glob(os.path.join(raiz, "_datos", "*", "datos.js"))):
        try:
            txt = open(f, encoding="utf-8").read()
            d = json.loads(txt[len("ANALISIS("):txt.rindex(")")])
        except Exception:
            continue
        carpeta = os.path.relpath(os.path.dirname(f), raiz).replace("\\", "/")
        tangos.append(dict(titulo=d["titulo"], carpeta=carpeta, bpm=d.get("bpm", 0),
                           compases=max([c for c in d["compas"]] or [0])))
    with open(os.path.join(raiz, "indice.js"), "w", encoding="utf-8") as f:
        f.write("window.TANGOS=" + json.dumps(tangos, ensure_ascii=False, indent=0) + ";\n")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "visor.html"), os.path.join(raiz, "visor.html"))
    return len(tangos)


def guardar_todo(dir_out, titulo, P, golpes, niveles, filas, pistas_rel):
    _csv(os.path.join(dir_out, "golpes.csv"), golpes)
    _csv(os.path.join(dir_out, "compases.csv"), filas)
    _csv(os.path.join(dir_out, "pulsos.csv"), [dict(seg=round(float(b), 3), compas=int(c), tiempo=int(t))
                                               for b, c, t in zip(P["beats"], P["compas"], P["tiempo"])])
    resumen_txt(os.path.join(dir_out, "resumen.txt"), titulo, P, filas)
    os.makedirs(os.path.join(dir_out, "graficas"), exist_ok=True)
    graficas(os.path.join(dir_out, "graficas"), golpes, niveles, P)
    datos_visor(os.path.join(dir_out, "datos.js"), titulo, P, golpes, pistas_rel, niveles, filas)
