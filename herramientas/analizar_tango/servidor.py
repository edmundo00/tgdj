"""Visor de tangos con análisis desde la página.

    abrir_visor.bat            (o: python servidor.py [--puerto 8765] [--sin-abrir])

Sirve la carpeta de los análisis (rutas.ANALISIS) en http://127.0.0.1:8765/ y abre ritmo.html en el navegador.
La página ve que hay servidor y enseña los botones para:
  - analizar una canción nueva (se arrastra el audio a la página; se guarda en Analisis tangos\\_canciones\\)
  - volver a analizar con el compás / el 1 corregidos
  - poner una partitura (.mxl / .musicxml)
Por dentro lanza ritmo.py y partitura.py, igual que a mano. Solo escucha en este ordenador (127.0.0.1).
"""
import os, sys, json, time, threading, subprocess, argparse, re, urllib.parse, urllib.request, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import rutas

RAIZ = rutas.ANALISIS
SUBIDAS = os.path.join(RAIZ, "_canciones")
AUDIO = (".flac", ".mp3", ".wav", ".m4a", ".ogg", ".opus", ".aif", ".aiff", ".aac", ".wma")
PARTI = (".mxl", ".musicxml", ".xml")
VERSION = 1

TRABAJOS = {}          # id -> dict(estado, lineas, carpeta, error, tipo, inicio)
CERROJO = threading.Lock()
EN_MARCHA = threading.Lock()   # un análisis cada vez (gastan mucha CPU)


def limpio(nombre):
    n = os.path.basename(nombre.replace("\\", "/"))
    n = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", n).strip(" .")
    return n or "cancion"


def lanzar(tipo, orden, carpeta=None):
    tid = f"{int(time.time() * 1000)}"
    T = dict(id=tid, tipo=tipo, estado="esperando", lineas=[], carpeta=carpeta, error=None, inicio=time.time())
    with CERROJO:
        TRABAJOS[tid] = T

    def correr():
        with EN_MARCHA:
            T["estado"] = "trabajando"
            env = dict(os.environ, TDJ_SIN_PAUSA="1", PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", PYTHONWARNINGS="ignore")
            try:
                p = subprocess.Popen([sys.executable, "-u", "-X", "utf8", *orden], cwd=AQUI, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                for l in p.stdout:
                    l = l.rstrip()
                    if not l:
                        continue
                    T["lineas"].append(l)
                    print("   ", l, flush=True)
                    m = re.search(r"→ (.+)$", l)
                    if l.startswith("Hecho en") and m:
                        T["carpeta"] = os.path.basename(m.group(1).strip().rstrip("\\/"))
                p.wait()
                if p.returncode == 0:
                    if tipo == "partitura":          # que la lista de canciones diga «con partitura»
                        try:
                            import pagina_ritmo
                            pagina_ritmo.actualizar_indice(RAIZ)
                        except Exception as e:
                            print("    (no se pudo poner al día la lista:", e, ")")
                    T["estado"] = "hecho"
                else:
                    T["estado"] = "error"
                    T["error"] = next((l for l in reversed(T["lineas"]) if l.strip()), f"salió con el código {p.returncode}")
            except Exception as e:
                T["estado"], T["error"] = "error", str(e)
    threading.Thread(target=correr, daemon=True).start()
    return T


def carpeta_ritmo(c):
    c = limpio(c)
    d = os.path.join(RAIZ, "_ritmo", c)
    if not os.path.isfile(os.path.join(d, "ritmo.json")):
        raise ValueError(f"No encuentro el análisis de «{c}»")
    return c, d


class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=RAIZ, **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    # --- respuestas
    def json(self, d, code=200):
        b = json.dumps(d, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/":
            self.send_response(302); self.send_header("Location", "/ritmo.html"); self.end_headers(); return
        if u.path == "/api/estado":
            return self.json(dict(ok=True, version=VERSION, carpeta=RAIZ, ocupado=EN_MARCHA.locked()))
        if u.path == "/api/trabajo":
            T = TRABAJOS.get(urllib.parse.parse_qs(u.query).get("id", [""])[0])
            if not T:
                return self.json(dict(error="no existe"), 404)
            return self.json(dict(T, lineas=T["lineas"][-14:], segundos=round(time.time() - T["inicio"])))
        if "Range" in self.headers:
            return self.rango()
        return super().do_GET()

    def rango(self):
        """Vídeos: el navegador pide trozos (Range) para poder saltar a cualquier punto."""
        ruta = self.translate_path(self.path)
        if not os.path.isfile(ruta):
            return super().do_GET()
        tam = os.path.getsize(ruta)
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers["Range"])
        a = int(m.group(1)) if m and m.group(1) else 0
        b = int(m.group(2)) if m and m.group(2) else tam - 1
        b = min(b, tam - 1)
        if a > b:
            self.send_response(416); self.send_header("Content-Range", f"bytes */{tam}"); self.end_headers(); return
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(ruta))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {a}-{b}/{tam}")
        self.send_header("Content-Length", str(b - a + 1))
        self.end_headers()
        with open(ruta, "rb") as f:
            f.seek(a)
            falta = b - a + 1
            try:
                while falta > 0:
                    trozo = f.read(min(1 << 20, falta))
                    if not trozo:
                        break
                    self.wfile.write(trozo)
                    falta -= len(trozo)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                pass

    def do_POST(self):
        # cabecera propia: otra web no puede mandarla sin permiso (CORS), así que solo vale la página del visor
        if self.headers.get("X-TDJ") != "1":
            return self.json(dict(error="no permitido"), 403)
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path == "/api/analizar":
                return self.analizar(q)
            if u.path == "/api/reanalizar":
                return self.reanalizar(q)
            if u.path == "/api/partitura":
                return self.partitura(q)
        except ValueError as e:
            return self.json(dict(error=str(e)), 400)
        return self.json(dict(error="no existe"), 404)

    def guardar_cuerpo(self, destino):
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            raise ValueError("No ha llegado ningún archivo")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        tmp = destino + ".subiendo"
        with open(tmp, "wb") as f:
            while n > 0:
                t = self.rfile.read(min(1 << 20, n))
                if not t:
                    break
                f.write(t); n -= len(t)
        if n:
            os.remove(tmp)
            raise ValueError("El archivo no ha llegado entero")
        os.replace(tmp, destino)

    def opciones(self, q):
        o = []
        if q.get("compas") in ("2/4", "3/4", "4/4"):
            o += ["--compas", q["compas"]]
        if q.get("uno"):
            o += ["--uno", f"{float(q['uno']):.3f}"]
        if q.get("pulso") in ("doble", "mitad"):
            o += ["--pulso", q["pulso"]]
        if q.get("separar") == "1":
            o += ["--separar"]
        return o

    def analizar(self, q):
        nombre = limpio(q.get("nombre", ""))
        if not nombre.lower().endswith(AUDIO):
            raise ValueError("Eso no parece un audio (flac, mp3, wav, m4a, ogg…)")
        destino = os.path.join(SUBIDAS, nombre)
        self.guardar_cuerpo(destino)
        T = lanzar("analizar", [os.path.join(AQUI, "ritmo.py"), destino, *self.opciones(q)],
                   carpeta=os.path.splitext(nombre)[0])
        self.json(dict(id=T["id"], carpeta=T["carpeta"]))

    def reanalizar(self, q):
        c, d = carpeta_ritmo(q.get("c", ""))
        a = json.load(open(os.path.join(d, "ritmo.json"), encoding="utf-8"))["meta"]["audio"]
        audio = rutas.buscar_audio(a)
        if not audio and os.path.isdir(SUBIDAS):       # el paquete se movió de carpeta: buscarla entre las subidas
            audio = next((os.path.join(SUBIDAS, f) for f in os.listdir(SUBIDAS) if os.path.splitext(f)[0] == c), None)
        if not audio:
            raise ValueError(f"No encuentro el audio de esta canción ({a})")
        T = lanzar("reanalizar", [os.path.join(AQUI, "ritmo.py"), audio, *self.opciones(q)], carpeta=c)
        self.json(dict(id=T["id"], carpeta=c))

    def partitura(self, q):
        c, d = carpeta_ritmo(q.get("c", ""))
        nombre = limpio(q.get("nombre", ""))
        if not nombre.lower().endswith(PARTI):
            raise ValueError("La partitura tiene que ser MusicXML (.mxl o .musicxml). Desde MuseScore: Exportar → MusicXML.")
        destino = os.path.join(d, "partitura_" + nombre)
        self.guardar_cuerpo(destino)
        T = lanzar("partitura", [os.path.join(AQUI, "partitura.py"), d, destino], carpeta=c)
        self.json(dict(id=T["id"], carpeta=c))


def ya_abierto(puerto):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/estado", timeout=1) as r:
            return json.load(r).get("ok")
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--sin-abrir", action="store_true", help="no abrir el navegador")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    rutas.preparar_ffmpeg()
    url = f"http://127.0.0.1:{a.puerto}/ritmo.html"
    if ya_abierto(a.puerto):
        print("El visor ya estaba abierto:", url)
        if not a.sin_abrir:
            webbrowser.open(url)
        return
    os.makedirs(os.path.join(RAIZ, "_ritmo"), exist_ok=True)
    if not os.path.exists(os.path.join(RAIZ, "ritmo.html")):
        import pagina_ritmo
        pagina_ritmo.actualizar_indice(RAIZ)
    srv = ThreadingHTTPServer(("127.0.0.1", a.puerto), Manejador)
    print("=" * 64)
    print(" Visor de tangos abierto en", url)
    print(" Análisis en:", RAIZ)
    print(" NO CIERRES ESTA VENTANA mientras uses el visor (al cerrarla se apaga).")
    print("=" * 64, flush=True)
    if not a.sin_abrir:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
