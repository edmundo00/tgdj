r"""VÍDEO DE PISADAS · el tramo marcado con un destello en cada pisada y la rejilla del compás encima (estilo El Flete).

    video_pisadas.bat "<carpeta de marcar>" [opciones]

Lee config.json (de marcar_pisadas.py) y las pisadas: pisadas.txt (botón «Copiar para Claude», pegado en el chat)
o pisadas.json (botón Guardar); si no hay en la carpeta, el pisadas*.json más reciente de Descargas.
Opciones:
  --lento 0.5            cámara lenta (la música se frena sin cambiar el tono)
  --compases 28-29       solo ese tramo (o --segundos 4-8)
  --rejilla rejilla.json filas de la rejilla para explicar (ver abajo). Sin él: --filas piano + una fila por bailarín
  --filas piano          (sin --rejilla) filas de instrumentos: piano,contrabajo,bandoneones,orquesta o «ninguna»
  --sin-rejilla          solo destellos
  --destellos 0          de quién salen destellos (índices de bailarín, «0,1»; por defecto todos)
  --clics                un clic sonoro en cada pisada (útil en la cámara lenta para oír pisada contra música)
  --rotulos rotulos.json {"27": ["español", "english", "FILA A RESALTAR"]}: texto bajo la rejilla en cada compás;
                         la fila nombrada se enmarca en oro y las demás se apagan
  --titulo "es|en"       texto fijo en todo el tramo · --final "es|en" últimos 2,5 s · --creditos "..." línea abajo
  --salida video.mp4     por defecto: <carpeta>\pisadas[_lento50].mp4

rejilla.json (las filas, en el orden de la explicación):
  {"filas": [
     {"nombre": "TIEMPOS", "tipo": "tiempos"},                                  1 2 3 4
     {"nombre": "FUERTE · DÉBIL", "tipo": "acentos", "pistas": ["contrabajo", "orquesta"]},   brillo = fuerza del tiempo
     {"nombre": "SÍNCOPA", "tipo": "golpes", "pistas": ["piano", "orquesta"], "compases": [27], "umbral": -3, "fuera_de_tiempo": true},
     {"nombre": "PIANITOS", "tipo": "golpes", "pistas": ["piano"], "compases": [28], "umbral": -6},
     {"nombre": "PISAN", "tipo": "pisadas", "bailarines": [0, 1]}],            una fila para la pareja si pisan juntos
   "parados": [27, 29]}                                                          «PARADOS» en la fila de pisadas
  Tipos que NO dependen de la detección (lo que dice el oído de Edmundo; mejor para explicar):
     {"nombre": "SÍNCOPA", "tipo": "patron", "compases": [27], "casillas": [0, 1, 3, 4, 6]}    1 · 1y · 2y · 3 · 4
     {"nombre": "FUERTE · DÉBIL", "tipo": "fuerte_debil", "compases": [26, 29]}               FUERTE/débil escrito
  ("fijo": el dibujo entero se ve desde que empieza el compás y cada casilla da un fogonazo al sonar.)
  Con "mostrar_en": [27] una fila solo sale en esos compases. LO MÁS CLARO (Edmundo, 17-11-2026): UNA fila de música
  que cambia en cada compás (lo que se explica ahí) + la fila PISAN. Muchas filas a la vez = no se sabe dónde mirar.
"""
import os, sys, json, glob, shutil, argparse, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import datos_tango as DT

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rutas
FF = rutas.preparar_ffmpeg()[0]
ORO, CREMA, ROSA = (240, 192, 90), (248, 241, 228), (214, 190, 180)
FONDO, CASILLA = (30, 6, 12, 205), (66, 20, 28, 255)
COLORES = [(240, 192, 90), (80, 160, 250), (240, 110, 170), (120, 220, 130)]          # color de cada bailarín (fila)
PALETA = [[(240, 192, 90), (250, 140, 60)], [(80, 160, 250), (70, 225, 205)],          # [izq, der] por bailarín,
          [(240, 110, 170), (190, 120, 250)], [(120, 220, 130), (210, 235, 90)]]       # igual que en la página
F = r"C:\Windows\Fonts"
GB = ImageFont.truetype(os.path.join(F, "georgiab.ttf"), 42)
GI = ImageFont.truetype(os.path.join(F, "georgiai.ttf"), 36)
SB = ImageFont.truetype(os.path.join(F, "segoeuib.ttf"), 30)
SBp = ImageFont.truetype(os.path.join(F, "segoeuib.ttf"), 24)
SBg = ImageFont.truetype(os.path.join(F, "segoeuib.ttf"), 34)
GR = ImageFont.truetype(os.path.join(F, "georgiab.ttf"), 60)
SBen = ImageFont.truetype(os.path.join(F, "segoeuib.ttf"), 36)
SBcr = ImageFont.truetype(os.path.join(F, "segoeuib.ttf"), 30)
ETQ = ["1", "y", "2", "y", "3", "y", "4", "y"]
NOMINST = {"piano": "PIANO", "contrabajo": "CONTRABAJO", "bandoneones": "BANDONEONES", "orquesta": "ORQUESTA"}
W, X0, CW, CWD, CH = 1040, 32, 122, 110, 74
SBw = ImageFont.truetype(os.path.join(F, "segoeuib.ttf"), 21)     # palabra dentro de la casilla (FUERTE, débil)
ALTO_FILA = CH + 34


def panel(d, tv, ts, filas, resaltar=None, parados=()):
    """rejilla «1 y 2 y 3 y 4 y». filas = [{"nombre", "color", "notas": [(t_salida, compás, casilla, peso)], "tipo"}]."""
    y0 = 62
    pos = d.donde(tv)
    comp = pos[0] if pos else None
    # filas con "mostrar_en": solo en esos compases (una fila de música que cambia según lo que se explica)
    filas = [f for f in filas if not f.get("mostrar") or comp in f["mostrar"]]
    alto = y0 + ALTO_FILA * len(filas) + 6
    img = Image.new("RGBA", (W, alto), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((0, 0, W, alto), 28, fill=FONDO)
    dr.text((40, 14), "EL COMPÁS", font=SB, fill=ROSA)
    if comp:
        t = f"COMPÁS {comp}"
        dr.text((W - 40 - dr.textlength(t, font=SB), 14), t, font=SB, fill=ORO)
    luz = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(luz)
    brillos = []
    for f, fila in enumerate(filas):
        cy = y0 + f * ALTO_FILA + 28
        b = [0.0] * 8
        for t_on, c, cas, peso in fila["notas"]:
            if c != comp:
                continue
            if fila.get("fijo"):                       # el dibujo entero se ve desde que empieza el compás
                b[cas] = max(b[cas], peso * 0.6)
            if ts >= t_on:                             # y cada casilla da un fogonazo cuando suena
                b[cas] = max(b[cas], peso * (0.6 + 0.4 * max(0.0, 1 - (ts - t_on) / 0.42) ** 2) if fila.get("fijo")
                             else peso * (0.45 + 0.55 * max(0.0, 1 - (ts - t_on) / 0.42) ** 2))
        brillos.append(b)
        dr.text((46, cy - 27), fila["nombre"], font=SBp, fill=fila["color"])
        for k in range(8):
            x = X0 + k * CW + 6
            dr.rounded_rectangle((x, cy, x + CWD, cy + CH), 14, fill=CASILLA)
            if b[k] > 0:
                dl.rounded_rectangle((x, cy, x + CWD, cy + CH), 14, fill=fila["color"] + (int(255 * min(1, b[k])),))
    img = Image.alpha_composite(img, luz.filter(ImageFilter.GaussianBlur(12)))
    img = Image.alpha_composite(img, luz)
    dr = ImageDraw.Draw(img)
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sombra)
    for f, fila in enumerate(filas):
        cy = y0 + f * ALTO_FILA + 28
        for k in range(8):
            x = X0 + k * CW + 6
            aqui = pos and pos[0] == comp and pos[1] == k
            num = ETQ[k] != "y"
            fuente = GB if num else GI
            color = (60, 14, 20) if brillos[f][k] > 0.5 else (CREMA if (num or aqui) else ROSA)
            tw = dr.textlength(ETQ[k], font=fuente)
            palabra = fila.get("palabras", {}).get(k) if comp in fila.get("compases_palabras", {comp}) else None
            dr.text((x + CWD / 2 - tw / 2, cy + CH / 2 - (36 if palabra else 26)), ETQ[k], font=fuente, fill=color)
            if palabra:                                # FUERTE / débil escrito en la casilla
                pw = dr.textlength(palabra, font=SBw)
                dr.text((x + CWD / 2 - pw / 2, cy + CH - 28), palabra, font=SBw, fill=color)
            if aqui:
                dr.rounded_rectangle((x - 4, cy - 4, x + CWD + 4, cy + CH + 4), 18, outline=CREMA, width=5)
        # «PARADOS» a lo largo de la fila de pisadas, desde el 2 (cuando ya han pisado el 1 y no se mueven)
        if fila["tipo"] == "pisadas" and comp in parados and pos and pos[1] >= 2:
            xa, xb = X0 + 2 * CW + 6, X0 + 7 * CW + 6 + CWD
            dr.rounded_rectangle((xa, cy + 6, xb, cy + CH - 6), 14, fill=(30, 6, 12, 230), outline=fila["color"], width=3)
            t = "PARADOS · STILL"
            dr.text(((xa + xb) / 2 - dr.textlength(t, font=SBg) / 2, cy + CH / 2 - 22), t, font=SBg, fill=fila["color"])
        # la fila de la que habla el rótulo: marco de oro; las demás, apagadas
        if resaltar:
            if fila["nombre"] == resaltar:
                dr.rounded_rectangle((14, cy - 32, W - 14, cy + CH + 6), 16, outline=ORO, width=5)
            else:
                ds.rectangle((16, cy - 30, W - 16, cy + CH + 4), fill=(20, 3, 10, 150))
    return Image.alpha_composite(img, sombra)


def estrella(capa, x, y, t, col):
    """t de 0 a 1: estrella de 5 puntas que crece, gira un poco y se apaga, con halo de su color y centro blanco."""
    import math
    a = (1 - t) ** 0.8
    R = 34 + 70 * t ** 0.6                     # radio de las puntas
    tam = int(R * 2 + 120)
    c = tam // 2
    giro = -math.pi / 2 + t * 0.6

    def puntos(radio, interior):
        return [(c + (radio if k % 2 == 0 else radio * interior) * math.cos(giro + k * math.pi / 5),
                 c + (radio if k % 2 == 0 else radio * interior) * math.sin(giro + k * math.pi / 5)) for k in range(10)]

    halo = Image.new("L", (tam, tam), 0)
    ImageDraw.Draw(halo).polygon(puntos(R * 1.25, 0.5), fill=int(200 * a))
    g = Image.new("RGBA", (tam, tam), col + (0,))
    g.putalpha(halo.filter(ImageFilter.GaussianBlur(R * 0.35)))
    cuerpo = Image.new("L", (tam, tam), 0)
    ImageDraw.Draw(cuerpo).polygon(puntos(R, 0.42), fill=int(255 * a))
    capa_col = Image.new("RGBA", (tam, tam), col + (0,))
    capa_col.putalpha(cuerpo.filter(ImageFilter.GaussianBlur(1.2)))
    g.alpha_composite(capa_col)
    nucleo = Image.new("L", (tam, tam), 0)
    ImageDraw.Draw(nucleo).polygon(puntos(R * 0.5, 0.45), fill=int(255 * a))
    blanco = Image.new("RGBA", (tam, tam), (255, 252, 235, 0))
    blanco.putalpha(nucleo.filter(ImageFilter.GaussianBlur(2.5)))
    g.alpha_composite(blanco)
    capa.alpha_composite(g, (int(x - c), int(y - c)))


def destello(capa, x, y, t, col):
    """t de 0 a 1: círculo de luz que se abre y se apaga (como en la página)."""
    a = (1 - t) ** 0.7
    r = 46 + 110 * t                           # halo del color del bailarín
    rn = 22 + 30 * t                           # núcleo blanco
    ra = 34 + 170 * t                          # anillo que se abre
    tam = int(max(r, ra) * 2 + 80)
    c = tam // 2

    def mancha(radio, alfa, blur):
        """máscara de luz: círculo difuminado (se difumina la máscara, no el color, para que no se ensucie)."""
        m = Image.new("L", (tam, tam), 0)
        ImageDraw.Draw(m).ellipse((c - radio, c - radio, c + radio, c + radio), fill=int(255 * alfa))
        return m.filter(ImageFilter.GaussianBlur(blur))

    g = Image.new("RGBA", (tam, tam), col + (0,))
    g.putalpha(mancha(r, 0.85 * a, r * 0.45))
    nucleo = Image.new("RGBA", (tam, tam), (255, 250, 230, 0))
    nucleo.putalpha(mancha(rn, 0.95 * a, rn * 0.5))
    g.alpha_composite(nucleo)
    anillo = Image.new("RGBA", (tam, tam), (255, 240, 190, 0))
    m = Image.new("L", (tam, tam), 0)
    ImageDraw.Draw(m).ellipse((c - ra, c - ra, c + ra, c + ra), outline=int(255 * a), width=7)
    anillo.putalpha(m.filter(ImageFilter.GaussianBlur(1.5)))
    g.alpha_composite(anillo)
    capa.alpha_composite(g, (int(x - c), int(y - c)))


def rotulo(capa, es, en, y, color=CREMA):
    """texto grande (español) + línea en inglés debajo, centrado, sobre caja oscura. Devuelve la altura usada."""
    dr = ImageDraw.Draw(capa)
    lineas = []
    for txt, fuente, col in ((es, GR, color), (en, SBen, ORO)):
        if not txt:
            continue
        palabras, linea = txt.split(), ""
        for p in palabras:                      # partir en líneas que quepan en 980 px
            prueba = (linea + " " + p).strip()
            if dr.textlength(prueba, font=fuente) > 980 and linea:
                lineas.append((linea, fuente, col)); linea = p
            else:
                linea = prueba
        lineas.append((linea, fuente, col))
    alto = sum(f.size + 14 for _, f, _ in lineas) + 24
    ancho = max(dr.textlength(t, font=f) for t, f, _ in lineas) + 60
    caja = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    ImageDraw.Draw(caja).rounded_rectangle(((1080 - ancho) / 2, y, (1080 + ancho) / 2, y + alto), 24, fill=(30, 6, 12, 200))
    capa.alpha_composite(caja)
    yy = y + 12
    for t, f, col in lineas:
        dr.text((540 - dr.textlength(t, font=f) / 2, yy), t, font=f, fill=col)
        yy += f.size + 14
    return alto


def leer_pisadas(ruta):
    """pisadas.json (botón Guardar) o el texto del botón «Copiar para Claude»:
    PISADAS <id> · Sol,London · 12
    <fotograma> <bailarín 0/1> <I|D> <a=apoyo|o=adorno> <x> <y>"""
    txt = open(ruta, encoding="utf-8-sig").read().strip()
    if not txt.startswith("PISADAS"):
        return json.loads(txt)
    lineas = txt.splitlines()
    cab = lineas[0].split("·")
    nombres = [n.strip() for n in cab[1].split(",")] if len(cab) > 1 else None
    pis = []
    for l in lineas[1:]:
        p = l.split()
        if len(p) >= 6:
            pis.append({"n": int(p[0]), "b": int(p[1]), "pie": p[2], "tipo": "adorno" if p[3] == "o" else "apoyo", "x": int(float(p[4])), "y": int(float(p[5]))})
    return {"bailarines": nombres, "pisadas": pis}


def filas_de(d, cfg, pis, nombres, fps, A, Bt, sal_ts, f0, f1):
    """notas de cada fila según rejilla.json (ver arriba)."""
    casilla = lambda s: (s[1] - 1) * 2 + s[2] // 2
    filas = []
    for fl in cfg["filas"]:
        tipo, notas = fl["tipo"], []
        comps = set(fl.get("compases", [])) or None
        color = tuple(fl["color"]) if "color" in fl else ORO
        if tipo == "tiempos":
            for t, c, k in d.pulsos:
                if A - 0.05 <= t <= Bt:
                    notas.append((sal_ts(t), c, (k - 1) * 2, 1.0))
            color = tuple(fl.get("color", CREMA))
        elif tipo in ("acentos", "golpes"):
            mejor = {}
            for p in fl.get("pistas", ["piano"]):
                for t, db in d.golpes.get(p, []):
                    if not (A - 0.05 <= t <= Bt):
                        continue
                    s = d.semicorchea(t)
                    if not s or (comps and s[0] not in comps):
                        continue
                    if tipo == "acentos":
                        if s[2] != 0:
                            continue                      # solo los tiempos
                        peso = min(1.0, max(0.12, (db + 22) / 22))
                    else:
                        if db < fl.get("umbral", -25) or (fl.get("fuera_de_tiempo") and s[2] == 0):
                            continue
                        peso = 1.0
                    clave = (s[0], casilla(s))
                    if clave not in mejor or mejor[clave][1] < peso:
                        mejor[clave] = (sal_ts(t), peso)
            notas = [(v[0], c, cas, v[1]) for (c, cas), v in mejor.items()]
        elif tipo in ("patron", "fuerte_debil"):
            # dibujo dicho por Edmundo (no detectado): "casillas" 0-7 de «1 y 2 y 3 y 4 y» en esos "compases".
            # fuerte_debil: 1 y 3 FUERTE (llenos), 2 y 4 débil (flojos), escrito en la casilla
            P = d.pulsos
            if tipo == "fuerte_debil":
                cas_peso = {0: 1.0, 2: 0.32, 4: 1.0, 6: 0.32}
                fl.setdefault("palabras", {"0": "FUERTE", "2": "débil", "4": "FUERTE", "6": "débil"})
            else:
                cas_peso = {int(c): 1.0 for c in fl["casillas"]}
            for j in range(len(P) - 1):
                t, c, k = P[j]
                t2 = P[j + 1][0]
                if comps and c not in comps or t2 < A or t > Bt:      # también el tiempo que empezó antes del vídeo
                    continue
                for cas, peso in cas_peso.items():
                    if cas // 2 == k - 1:
                        notas.append((sal_ts(t + (t2 - t) / 2 * (cas % 2)), c, cas, peso))
        elif tipo == "pisadas":
            quienes = fl.get("bailarines", list(range(len(nombres))))
            vistas = set()
            for p in sorted(pis, key=lambda p: p["n"]):
                if p.get("b", 0) in quienes and p.get("tipo", "apoyo") == "apoyo" and f0 <= p["n"] <= f1:
                    s = d.semicorchea(p["n"] / fps)
                    if s and (s[0], casilla(s)) not in vistas:
                        vistas.add((s[0], casilla(s)))
                        notas.append((sal_ts(p["n"] / fps), s[0], casilla(s), 1.0))
            if "color" not in fl:
                color = COLORES[quienes[0] % 4] if len(quienes) == 1 else (255, 214, 120)
        filas.append({"nombre": fl["nombre"], "color": color, "notas": notas, "tipo": tipo, "mostrar": set(fl.get("mostrar_en", [])),
                      "fijo": fl.get("fijo", tipo in ("patron", "fuerte_debil")),
                      "palabras": {int(k): v for k, v in fl.get("palabras", {}).items()}})
    return filas


def pista_clics(ruta, tiempos, dur, sr=48000):
    """WAV con un clic de madera (2,2 kHz, 25 ms) en cada instante."""
    y = np.zeros(int(dur * sr) + sr // 10, np.float32)
    n = int(0.025 * sr)
    clic = (np.sin(2 * np.pi * 2200 * np.arange(n) / sr) * np.exp(-np.arange(n) / (0.006 * sr))).astype(np.float32)
    for t in tiempos:
        k = int(t * sr)
        if 0 <= k < len(y) - n:
            y[k:k + n] += clic
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767 * 0.7).astype(np.int16).tobytes())


def main():
    ap = argparse.ArgumentParser(description="Vídeo con destellos en las pisadas y la rejilla del compás")
    ap.add_argument("carpeta")
    ap.add_argument("--pisadas")
    ap.add_argument("--lento", type=float, default=1.0)
    ap.add_argument("--compases"); ap.add_argument("--segundos")
    ap.add_argument("--rejilla")
    ap.add_argument("--filas", default="piano")
    ap.add_argument("--sin-rejilla", action="store_true")
    ap.add_argument("--destellos")
    ap.add_argument("--clics", action="store_true")
    ap.add_argument("--forma", default="estrella", choices=["estrella", "circulo"], help="forma del destello de cada pisada")
    ap.add_argument("--salida")
    ap.add_argument("--rotulos")
    ap.add_argument("--titulo"); ap.add_argument("--final"); ap.add_argument("--creditos")
    a = ap.parse_args()
    ROT = {int(k): v for k, v in json.load(open(a.rotulos, encoding="utf-8")).items()} if a.rotulos else {}
    TIT = (a.titulo.split("|") + [""])[:2] if a.titulo else None
    FIN = (a.final.split("|") + [""])[:2] if a.final else None
    car = os.path.abspath(a.carpeta)
    conf = json.load(open(os.path.join(car, "config.json"), encoding="utf-8"))
    fps, inicio = conf["fps"], conf["inicio"]
    d = DT.DatosTango(conf["cancion"], inicio)

    pp = a.pisadas
    if not pp:                                  # lo más reciente: pisadas.txt (copiado de la página) o pisadas.json (Guardar)
        cand = [p for p in (os.path.join(car, "pisadas.txt"), os.path.join(car, "pisadas.json")) if os.path.isfile(p)]
        cand += glob.glob(os.path.expandvars(r"%USERPROFILE%\Downloads\pisadas*.json"))
        if not cand:
            raise SystemExit("No encuentro las pisadas: pulsa «Copiar para Claude» en la página y pégalas en el chat (→ pisadas.txt)")
        pp = max(cand, key=os.path.getmtime)
    P = leer_pisadas(pp)
    pis = P["pisadas"]
    nombres = P.get("bailarines") or conf["bailarines"]
    print(f"{len(pis)} pisadas de {pp}")

    if a.compases:
        c0, c1 = [int(x) for x in a.compases.split("-")]
        t0, t1 = d.compases(c0, c1)
        f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
    elif a.segundos:
        t0, t1 = [float(x) for x in a.segundos.split("-")]
        f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
    else:
        f0, f1 = conf["f0"], conf["f1"]
    f0 = max(0, f0)                              # el compás puede empezar antes que el vídeo
    L = a.lento
    nfr = int(round((f1 - f0 + 1) / L))
    A, Bt = f0 / fps, (f1 + 1) / fps
    sal_ts = lambda tv: (tv - A) / L

    parados = ()
    filas = []
    if not a.sin_rejilla:
        if a.rejilla:
            cfg = json.load(open(a.rejilla, encoding="utf-8"))
            filas = filas_de(d, cfg, pis, nombres, fps, A, Bt, sal_ts, f0, f1)
            parados = tuple(cfg.get("parados", []))
        else:
            cfg = {"filas": [{"nombre": NOMINST.get(k, k.upper()), "tipo": "golpes", "pistas": [k]} for k in a.filas.split(",") if k and k != "ninguna"]
                   + [{"nombre": n.upper(), "tipo": "pisadas", "bailarines": [bi]} for bi, n in enumerate(nombres)]}
            filas = filas_de(d, cfg, pis, nombres, fps, A, Bt, sal_ts, f0, f1)

    con_destello = set(int(x) for x in a.destellos.split(",")) if a.destellos else None
    pd = [p for p in pis if f0 <= p["n"] <= f1 and (con_destello is None or p.get("b", 0) in con_destello)]
    esc = 1080 / conf.get("anchoVideo", 1080)          # pisadas en píxeles del vídeo original

    tmp = os.path.join(car, "_capas")
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp, exist_ok=True)
    DUR_FLASH = 0.30                              # segundos (de salida) que dura un destello
    for k in range(nfr):
        ts = k / fps
        tv = A + ts * L
        capa = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        for p in pd:
            tf = sal_ts(p["n"] / fps)
            if 0 <= ts - tf < DUR_FLASH:
                col = PALETA[p.get("b", 0) % 4][1 if p.get("pie") == "D" else 0] if p.get("tipo", "apoyo") == "apoyo" else ROSA
                (estrella if a.forma == "estrella" else destello)(capa, p["x"] * esc, p["y"] * esc, (ts - tf) / DUR_FLASH, col)
        pos = d.donde(tv)
        rot = None
        if FIN and ts > nfr / fps - 2.5:
            rot = FIN
        elif pos and pos[0] in ROT:
            rot = (ROT[pos[0]] + ["", ""])[:3]
        y_txt = 230
        if filas:
            pn = panel(d, tv, ts, filas, resaltar=(rot[2] if rot and len(rot) > 2 and rot is not FIN else None), parados=parados)
            capa.alpha_composite(pn, (20, 230))
            y_txt = 230 + pn.size[1] + 20
        if TIT:
            y_txt += rotulo(capa, TIT[0], TIT[1], y_txt, ORO) + 12
        if rot:
            rotulo(capa, rot[0], rot[1], y_txt)
        if a.creditos:
            dr = ImageDraw.Draw(capa)
            w = dr.textlength(a.creditos, font=SBcr)
            dr.rounded_rectangle((540 - w / 2 - 16, 1440, 540 + w / 2 + 16, 1486), 14, fill=(30, 6, 12, 170))
            dr.text((540 - w / 2, 1444), a.creditos, font=SBcr, fill=ROSA)
        capa.save(os.path.join(tmp, f"c{k:05d}.png"), compress_level=1)
        if k % 60 == 0:
            print(f"  capa {k}/{nfr}", flush=True)

    atempo = []
    x = L
    while x < 0.5:
        atempo.append("atempo=0.5"); x /= 0.5
    atempo.append(f"atempo={x:.4f}")
    entradas = ["-i", conf["video"], "-i", conf["cancion"], "-framerate", str(fps), "-i", os.path.join(tmp, "c%05d.png")]
    audio = f"[1:a]atrim={inicio + A}:{inicio + Bt},asetpts=PTS-STARTPTS,{','.join(atempo)},apad,atrim=0:{nfr / fps}"
    if a.clics:                                   # clic en cada pisada (sin repetir si pisan los dos a la vez)
        tiempos = sorted({round(sal_ts(p["n"] / fps), 3) for p in pis if f0 <= p["n"] <= f1 and p.get("tipo", "apoyo") == "apoyo"})
        wav = os.path.join(tmp, "clics.wav")
        pista_clics(wav, tiempos, nfr / fps)
        entradas += ["-i", wav]
        audio += "[m];[3:a]aresample=44100,volume=0.8[k];[m][k]amix=inputs=2:normalize=0:duration=first[a]"
    else:
        audio += "[a]"
    fc = (f"[0:v]trim=start_frame={f0}:end_frame={f1 + 1},setpts=(PTS-STARTPTS)/{L},fps={fps},scale=1080:1920[base];"
          f"[base][2:v]overlay=0:0:shortest=1,format=yuv420p[v];" + audio)
    salida = a.salida or os.path.join(car, "pisadas" + ("" if L == 1 else f"_lento{int(L * 100)}") + ".mp4")
    subprocess.run([FF, "-v", "error", "-y"] + entradas + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "19", "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", salida], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    import pathlib
    print("hecho:", pathlib.Path(salida).as_uri())


if __name__ == "__main__":
    main()
