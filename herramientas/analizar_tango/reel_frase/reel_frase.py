"""REEL «BAILAR LA FRASE» para cualquier tango y cualquier pareja (21-11-2026).

Hecho a partir del reel de El Taller Tango con «Vieja calesita» (Instagram\\publicados\\2026-11-21_bailar-la-frase, v14).
Todo sale de un guion.json (ejemplo: guion_calesita.json, al lado de este archivo):
  gancho (dos pasos · ¡CHAN! ¡CHAN! · ¡QUIETOS!, imagen congelada) → diapo «¿Por qué se han parado?» →
  «LAS FRASES EN EL TANGO» → la frase SOLO CON MÚSICA (esquema EL RITMO / VIOLINES / CANTOR, barra de 8 compases,
  contador, acordes, recuadro con ellos) → «Así termina la frase…» → con ellos a cámara lenta → remate y gracias.

Uso (python del venv analizar_tango; ffmpeg y Node como siempre):
  reel_frase.py guion.json                 prepara, monta, renderiza, comprueba y exporta
  reel_frase.py guion.json --sin-render    solo prepara y monta el proyecto (para mirarlo o tocar la plantilla)

Lo que necesita el guion (lo demás tiene valores por defecto, ver DEFECTO y TEXTOS más abajo):
  "cancion":  carpeta de Analisis tangos\\_ritmo (ritmo.ritmo.json + video.json de video.py)
  "video":    el vídeo de los bailarines (el mismo que se cuadró con video.py)   "pisadas": pisadas.txt de Edmundo
  "frase":    el compás que suena como «1 del compás 1» de la frase (¡preguntárselo a Edmundo!, lección de la calesita)
  "anacrusa": [compás, tiempo] en que entra el cantor antes de la frase
  "proyecto": carpeta de trabajo de HyperFrames (fuera de Dropbox)   "salida": carpeta del borrador del reel
  "nombre", "version", "pareja", "cuenta", y los textos que se quieran cambiar en "textos".
La frase es de 8 compases: compás 7 = tensión, compás 8 = llega en su 1 y la orquesta calla en 2-3-4.
Los tramos salen solos de "frase" (se pueden cambiar en "tramos").
Pruebas que hace solo: sonido del MP4 = el preparado (±15 ms) y <reel>_clic.mp4 (clic agudo en cada 1 DIBUJADO:
que lo escuche Edmundo; si no cae en el 1 que oye, el dibujo está mal).
"""
import os, sys, json, subprocess, shutil, argparse, html
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RITMO = r"D:\Dropbox\TDJ\Analisis tangos\_ritmo"
DATOS = r"D:\Dropbox\TDJ\Analisis tangos\_datos"
NODE = r"C:\Users\edmun\herramientas\node"
SR = 48000

DEFECTO = {
    "version": "v1",
    "subir_violines": 0.7,      # en el 2-3-4 del compás 8 (+0,7 × la pista separada ≈ +4 dB); 0 = no
    "corte_camara": None,       # segundo de la canción en que el vídeo cambia de cámara (el recuadro se congela ahí)
    "fundido_final": 0.8,
    "acordes": ["", ""],        # [tensión, casa], p. ej. ["RE 7", "SOL MENOR"]; vacío = no se ponen
}
# Textos por defecto (los de la calesita, v14). {pareja} y {cuenta} se rellenan con el guion.
TEXTOS = {
    "pies_a": "Mira sus", "pies_b": "PIES 👣", "chan": "¡CHAN!", "quietos": "¡QUIETOS!", "quien": "{PAREJA} · {cuenta}",
    "dp1": "¿Por qué se han parado?", "dp2": "¿Por qué dejan de bailar?", "lasfrases_a": "LAS FRASES", "lasfrases_b": "EN EL TANGO",
    "empieza_a": "La frase empieza…", "empieza_b": "EN EL 1", "e_empieza": "EL CANTOR ENTRA ANTES…",
    "ocho_a": "Una frase dura", "ocho_b": "8 COMPASES", "tension_a": "Compás 7:", "tension_b": "TENSIÓN", "e_tension": "LA MÚSICA PIDE VOLVER",
    "casa_a": "Compás 8, en el 1…", "casa_b": "¡LLEGA A CASA!", "silencio_a": "Compás 8: todo se calla…", "silencio_b": "menos los violines",
    "e_arrastra": "Y EL CANTOR ARRASTRA LAS NOTAS", "asi_a": "Así termina la frase:", "asi_b": "un silencio para que\nempiece la siguiente",
    "c7_a": "Caminan en el", "c7_b": "1 y el 3", "e_c7": "CASI HASTA EL FINAL", "c8_a": "Compás 7, la tensión:", "c8_b": "¡TODOS!",
    "e_c8": "PISAN LOS 4 TIEMPOS", "c1_a": "Compás 8: llega la frase…", "c1_b": "¡Y PARAN!", "e_c1": "EN EL SILENCIO",
    "porque_a": "No se paran porque sí:", "porque_b": "la frase\nha llegado", "gracias_a": "Gracias,", "gracias_b": "{pareja} ❤",
    "g1": "POR TANTO TANGO", "g2": "POR LA PRECISIÓN EN LA PISADA", "g3": "Y LO MÁS IMPORTANTE:", "g4": "POR SER AÚN MEJORES FUERA DE LA PISTA ❤",
    "manda_a": "Manda esto a", "manda_b": "tu pareja\nde baile", "chip_solo": "SOLO LA MÚSICA", "chip_ellos": "AHORA, CON ELLOS",
    "lenta": "CÁMARA LENTA ×0,5", "llave": "UNA FRASE = 8 COMPASES", "cuenta": "COMPÁS DE LA FRASE", "de8": "de 8", "pip": "{PAREJA}",
    "cred_q": "{pareja}", "cred_d": "{cuenta} · ¡síguelos!", "cred_d2": "Bailan precioso", "cred_p": "", "firma": "TDJ EDMUNDO FRAGA",
    "fila_ritmo": "EL RITMO", "fila_violines": "VIOLINES", "fila_cantor": "CANTOR", "fila_pisan": "PISAN 👣",
    "et_empieza": "EMPIEZA", "et_tension": "TENSIÓN", "et_llega": "LLEGA", "et_silencio": "SILENCIO", "et_caminan": "1 · 3",
    "et_todos": "TODOS", "et_paran": "¡PARAN!", "de_llega": "compás 8: llega a casa", "de_silencio": "todo calla menos los violines",
    "acorde_tension": "{acorde_tension} · TENSIÓN", "acorde_casa": "{acorde_casa} · CASA",
}


def tramos_de(F):
    """Tramos del reel a partir del compás 1 de la frase F: (nombre, desde, hasta, velocidad, con vídeo)."""
    return [
        ("real", [F + 6, 3, -0.25], [F + 8, 1], 1.0, True),    # gancho: 2 pasos, ¡chan! ¡chan!, ¡quietos!
        ("musica", [F - 4, 3], [F + 8, 1], 1.0, False),        # diapo + la frase solo con música
        ("mapa", [F + 8, 1], [F + 11, 1], 1.0, False),         # «Así termina la frase…» (la música sigue)
        ("lento", [F + 5, 1], [F + 7, 3], 0.5, True),          # con ellos, a cámara lenta
        ("final", [F + 7, 3], [F + 13, 3], 1.0, True),         # remate y gracias
    ]


# ------------------------------------------------------------------------------------------------------------------
class Reel:
    def __init__(self, g):
        self.g = g
        self.carp = os.path.join(RITMO, g["cancion"])
        self.pistas = os.path.join(DATOS, g["cancion"], "pistas")
        self.D = json.load(open(os.path.join(self.carp, "ritmo.json"), encoding="utf-8"))
        vids = json.load(open(os.path.join(self.carp, "video.json"), encoding="utf-8"))["videos"]
        self.V = next((v for v in vids if v.get("id") == g.get("video_id")), vids[0])
        self.proy = g["proyecto"]
        self.F = g["frase"]

    def seg(self, c, t, mas=0.0):
        for p in self.D["pulsos"]:
            if p["compas"] == c and p["tiempo"] == t:
                return p["seg"] + mas
        raise SystemExit(f"no hay pulso {c}.{t} en ritmo.json")

    def ff(self, *args, entrada=None):
        return subprocess.run(["ffmpeg", "-v", "error", *args], input=entrada, capture_output=True, check=True).stdout

    # ---- sonido ----
    def leer(self, a, b, vel, archivo=None):
        af = f"atrim={a}:{b},asetpts=PTS-STARTPTS"
        if vel != 1.0:
            af += f",rubberband=tempo={vel}:pitchq=quality"
        x = self.ff("-i", archivo or self.D["meta"]["audio"], "-af", af, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-")
        return np.frombuffer(x, np.float32).reshape(-1, 2).copy()

    def violines_arriba(self, x, a, b):
        """en el 2-3-4 del compás 8 suben un poco los violines (su pista separada), con rampas de 0,15 s."""
        k = self.g["subir_violines"]
        vio = os.path.join(self.pistas, "violines.flac")
        d0, d1 = self.seg(self.F + 7, 2), self.seg(self.F + 8, 1)
        if not k or not os.path.exists(vio) or d1 <= a or d0 >= b:
            return x
        v = self.leer(a, b, 1.0, vio)[:len(x)]
        t = np.arange(len(v)) / SR + a
        gan = np.clip(np.minimum((t - (d0 - 0.05)) / 0.15, (d1 + 0.1 - t) / 0.15), 0, 1) * k
        x[:len(v)] += v * gan[:, None]
        return x

    # ---- vídeo ----
    def clip(self, sal, a, b, vel, escala, congelar_en=None, extra=0.0, crf=16):
        V = self.V
        v0 = (a - V["inicio"]) / V["velocidad"]
        fin = b if congelar_en is None or not (a < congelar_en < b) else congelar_en
        congela = (b - fin) / vel + extra
        vf = (f"setpts=(PTS-STARTPTS)*{V['velocidad'] / vel:.6f},scale={escala}:flags=lanczos,"
              "eq=contrast=1.08:brightness=0.03:gamma=1.12" + (",unsharp=5:5:0.6" if escala.startswith("1080") else "") + ",fps=30")
        if congela > 0:
            vf += f",tpad=stop_mode=clone:stop_duration={congela:.3f}"
        cola = 0.0 if fin < b else 0.2                    # si se congela, cortar JUSTO ahí (si no, se cuela el plano siguiente)
        self.ff("-y", "-ss", f"{v0:.3f}", "-t", f"{(fin - a) / V['velocidad'] + cola:.3f}", "-i", self.g["video"], "-vf", vf,
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", sal)

    # ---- esquema: lo que suena en cada tiempo ----
    def esquema(self):
        import librosa
        P, out = self.D["pulsos"], {}

        def por_tiempo(pista, entero=False):
            y, sr = librosa.load(pista, sr=22050, mono=True)
            r = librosa.feature.rms(y=y, frame_length=1024, hop_length=220)[0]
            t = np.arange(len(r)) * 220 / sr
            d = {}
            for p, q in zip(P, P[1:]):
                m = (t >= p["seg"] - (0 if entero else 0.03)) & (t < (q["seg"] if entero else p["seg"] + (q["seg"] - p["seg"]) * 0.5))
                if m.any():
                    d[f'{p["compas"]}.{p["tiempo"]}'] = (r[m].mean() if entero else r[m].max())
            return d, np.percentile(r, 95)

        for k, nom in (("bandoneones", "band"), ("contrabajo", "bajo"), ("voz", "voz")):
            f = os.path.join(self.pistas, k + ".flac")
            if os.path.exists(f):
                d, ref = por_tiempo(f)
                out[nom] = {c: round(float(np.clip((20 * np.log10(v / ref + 1e-9) + 15) / 15, 0, 1)), 2) for c, v in d.items()}
        f = os.path.join(self.pistas, "violines.flac")
        if os.path.exists(f):   # los violines suenan flojitos siempre: escala de −25 a −5 dB
            d, _ = por_tiempo(f, entero=True)
            db = {c: 20 * np.log10(v + 1e-9) for c, v in d.items()}
            ref = np.percentile(list(db.values()), 95)
            out["vio"] = {c: round(float(np.clip((v - ref + 25) / 20, 0, 1)), 2) for c, v in db.items()}
        band, bajo = out.get("band", {}), out.get("bajo", {})
        out["marc"] = {c: round((band.get(c, 0) + bajo.get(c, 0)) / 2, 2) for c in set(band) | set(bajo)}   # EL RITMO
        return out

    # ---- todo ----
    def preparar(self):
        g, V, F = self.g, self.V, self.F
        assets = os.path.join(self.proy, "assets")
        os.makedirs(assets, exist_ok=True)
        pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width",
                                 "-of", "csv=p=0", g["video"]], capture_output=True, text=True)
        ancho = int(pr.stdout.strip().split()[0])          # las pisadas van en píxeles del vídeo original
        esc = 1080 / ancho
        pis = []
        for l in open(g["pisadas"], encoding="utf-8").read().splitlines()[1:]:
            if l.strip():
                fr, b, pie, tipo, x, y = l.split()
                pis.append((V["inicio"] + int(fr) / V["fps"] * V["velocidad"], int(b), pie, float(x) * esc, float(y) * esc))
        congelar = self.seg(*(g.get("congelar") or [F + 7, 2]))
        corte = g.get("corte_camara") or 1e9
        trozos, T, PUL, PIS, FR = [], {}, {}, {}, {}
        t = 0
        tramos = g.get("tramos") or tramos_de(F)
        for nombre, c0, c1, vel, con_video in tramos:
            a, b = self.seg(*c0), self.seg(*c1)
            x = self.leer(a, b, vel)
            if nombre == "musica":
                x = self.violines_arriba(x, a, b)
                self.clip(os.path.join(assets, "v_pip.mp4"), a, b, 1.0, "324:576", congelar_en=min(corte, b - 0.01), extra=3.0, crf=18)
            if nombre == tramos[-1][0]:
                n = int(g["fundido_final"] * SR); x[-n:] *= np.linspace(1, 0, n)[:, None]
            t0 = t / SR
            T[nombre] = dict(inicio=round(t0, 4), desde=round(a, 3), hasta=round(b, 3), vel=vel, dur=round(len(x) / SR, 4), video=con_video)
            PUL[nombre] = [[round(t0 + (p["seg"] - a) / vel, 4), p["compas"], p["tiempo"]] for p in self.D["pulsos"] if a - 0.02 <= p["seg"] < b - 0.02]
            PIS[nombre] = [[round(t0 + (s - a) / vel, 4), bb, pie, round(xx), round(yy)] for s, bb, pie, xx, yy in pis if a - 0.02 <= s < b - 0.02]
            FR[nombre] = [[round(t0 + (self.seg(F - 1 + k, 1) - a) / vel, 4), round(t0 + (self.seg(F + k, 1) - a) / vel, 4)] for k in range(1, 10)]
            if con_video:
                self.clip(os.path.join(assets, f"v_{nombre}.mp4"), a, b, vel, "1080:1920",
                          congelar_en=congelar if nombre == "real" else (corte if nombre != "final" else None), extra=0.3)
            n = int(SR * 0.006); r = np.linspace(0, 1, n)[:, None]; x[:n] *= r; x[-n:] *= r[::-1]
            trozos.append(x); t += len(x)
            print(f"{nombre:6s} {a:7.3f}-{b:7.3f} s ×{vel} · en el reel {t0:6.2f}-{t / SR:6.2f} · {len(PUL[nombre])} pulsos · {len(PIS[nombre])} pisadas")
        T["FIN"] = round(t / SR, 4)
        # foto congelada para la diapo = último fotograma del gancho
        self.ff("-y", "-sseof", "-0.2", "-i", os.path.join(assets, "v_real.mp4"), "-frames:v", "1", "-q:v", "2", os.path.join(assets, "congelado.jpg"))
        wav = os.path.join(self.proy, "audio.wav")
        self.ff("-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-ar", str(SR), wav,
                entrada=np.concatenate(trozos).astype(np.float32).tobytes())
        self.ff("-y", "-i", wav, "-c:a", "aac", "-b:a", "256k", os.path.join(assets, "audio.m4a"))
        tx = dict(TEXTOS)
        tx.update(g.get("textos", {}))
        rell = dict(pareja=g["pareja"], PAREJA=g["pareja"].upper(), cuenta=g["cuenta"],
                    acorde_tension=g["acordes"][0], acorde_casa=g["acordes"][1])
        tx = {k: v.format(**rell) for k, v in tx.items()}
        if not g["acordes"][0]:
            tx["acorde_tension"] = tx["acorde_casa"] = ""
        guion = dict(frase=F, anacrusa=g["anacrusa"], textos=tx)
        with open(os.path.join(self.proy, "tiempos.js"), "w", encoding="utf-8") as f:
            f.write("// generado por reel_frase.py: no tocar a mano\n")
            for k, v in [("TRAMOS", T), ("PULSOS", PUL), ("PISADAS", PIS), ("ESQUEMA", self.esquema()), ("FRASE", FR), ("GUION", guion)]:
                f.write(f"window.{k} = {json.dumps(v, ensure_ascii=False)};\n")
        self.T = T
        print("FIN", T["FIN"], "s")

    def montar(self):
        T = self.T
        s = open(os.path.join(AQUI, "plantilla.html"), encoding="utf-8").read()
        rep = {"__FIN__": T["FIN"], "__musica_ini__": T["musica"]["inicio"], "__pip_dur__": round(T["musica"]["dur"] + 2.9, 3)}
        for k in ("real", "lento", "final"):
            rep[f"__{k}_ini__"], rep[f"__{k}_dur__"] = T[k]["inicio"], T[k]["dur"]
        for k, v in rep.items():
            s = s.replace(k, str(v))
        open(os.path.join(self.proy, "index.html"), "w", encoding="utf-8").write(s)
        for b in ("package.json", "hyperframes.json", "meta.json"):
            if not os.path.exists(os.path.join(self.proy, b)):
                shutil.copy(os.path.join(AQUI, "base", b), self.proy)

    def hyperframes(self, *args):
        env = dict(os.environ, DO_NOT_TRACK="1", PATH=NODE + os.pathsep + r"C:\ffmpeg\bin" + os.pathsep + os.environ["PATH"])
        r = subprocess.run([os.path.join(NODE, "npx.cmd"), "--yes", "hyperframes@0.9.41", *args], cwd=self.proy, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        return r.stdout + r.stderr

    def renderizar(self):
        g = self.g
        sal = g["salida"]
        os.makedirs(os.path.join(sal, "fuente"), exist_ok=True)
        chk = self.hyperframes("check")
        avisos = [l for l in chk.splitlines() if "✗" in l or "⚠" in l]
        print("check:", "BIEN" if "Check passed" in chk else "MAL", *avisos[:6], sep="\n  ")
        if "Check passed" not in chk:
            raise SystemExit("hyperframes check falla: mirar el informe en .hyperframes\\artifacts\\checks")
        mp4 = os.path.join(self.proy, "render.mp4")
        self.hyperframes("render", "-o", "render.mp4", ".")
        base = os.path.join(sal, f'{g["nombre"]}_{g["version"]}')
        shutil.move(mp4, base + ".mp4")
        self.comprobar(base + ".mp4")
        self.ff("-y", "-i", base + ".mp4", "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-b:a", "192k", "-movflags", "+faststart", base + "-instagram.mp4")
        self.ff("-y", "-i", base + ".mp4", "-vf", "scale=720:-2", "-c:v", "libx264", "-preset", "slow", "-crf", "28", "-pix_fmt",
                "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", base + "_whatsapp.mp4")
        self.ff("-y", "-ss", "0.05", "-i", base + ".mp4", "-frames:v", "1", os.path.join(sal, f'portada_{g["version"]}.jpg'))
        for f in ("index.html", "tiempos.js"):
            shutil.copy(os.path.join(self.proy, f), os.path.join(sal, "fuente", f))
        json.dump(g, open(os.path.join(sal, "fuente", "guion.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Listo:", base + ".mp4")

    def comprobar(self, mp4):
        """1) el sonido del MP4 = el preparado (±15 ms) · 2) <reel>_clic.mp4: clic agudo en cada 1 DIBUJADO."""
        def leer(f, sr):
            return np.frombuffer(self.ff("-i", f, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"), np.float32)
        ref, vid = leer(os.path.join(self.proy, "audio.wav"), 8000), leer(mp4, 8000)
        peor = 0
        for t in [v["inicio"] for k, v in self.T.items() if k != "FIN"] + [ref.size / 8000 - 3]:
            a, n, m = int((t + 0.5) * 8000), 16000, 800
            x, y = ref[a:a + n], vid[a - m:a + n + m]
            if len(y) < n + 2 * m or len(x) < n:
                continue
            k = int(np.argmax(np.correlate(y, x, "valid"))) - m
            peor = max(peor, abs(1000 * k / 8000))
        print("sonido:", "BIEN" if peor <= 15 else "MAL", f"(peor {peor:.1f} ms)")
        js = open(os.path.join(self.proy, "tiempos.js"), encoding="utf-8").read()
        import re
        P = json.loads(re.search(r"window\.PULSOS = (.*);", js).group(1))
        a = np.frombuffer(self.ff("-i", mp4, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"), np.float32).reshape(-1, 2).copy()

        def clic(f, dur, vol):
            tt = np.arange(int(dur * SR)) / SR
            return (np.sin(2 * np.pi * f * tt) * np.exp(-tt / (dur / 4)) * vol).astype(np.float32)
        agudo, suave = clic(2000, 0.06, 0.55), clic(900, 0.04, 0.25)
        for lista in P.values():
            for t, c, k in lista:
                x = agudo if k == 1 else suave
                i = int(t * SR)
                if 0 <= i < len(a) - len(x):
                    a[i:i + len(x)] += x[:, None]
        sal = os.path.splitext(mp4)[0] + "_clic.mp4"
        self.ff("-y", "-i", mp4, "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", sal, entrada=np.clip(a, -1, 1).tobytes())
        print("prueba de clic (que la escuche Edmundo; agudo = el 1 del dibujo):", sal)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("guion")
    ap.add_argument("--sin-render", action="store_true")
    a = ap.parse_args()
    g = dict(DEFECTO)
    g.update(json.load(open(a.guion, encoding="utf-8")))
    falta = [k for k in ("cancion", "video", "pisadas", "frase", "anacrusa", "proyecto", "salida", "nombre", "pareja", "cuenta") if k not in g]
    if falta:
        raise SystemExit("faltan en el guion: " + ", ".join(falta))
    if shutil.which("ffmpeg") is None:
        os.environ["PATH"] = r"C:\ffmpeg\bin" + os.pathsep + os.environ["PATH"]
    r = Reel(g)
    r.preparar()
    r.montar()
    if not a.sin_render:
        r.renderizar()


if __name__ == "__main__":
    main()
