"""
Modo en vivo de la presentación web: un pequeño servidor en el portátil de la milonga (sin internet).

    servidor = Proyector(ruta_html).arrancar()     # http://localhost:8765 y http://<ip del portátil>:8765
    servidor.parar()

- Sirve la presentación (.html de web.py) y /ahora con la canción que suena: el historial de Mixxx (su base de
  datos, %LOCALAPPDATA%\\Mixxx\\mixxxdb.sqlite) o el tracklist de VirtualDJ, lo más reciente
  (%LOCALAPPDATA%\\VirtualDJ\\History\\tracklist.txt, última línea "hora : Artista - Título").
- La presentación pregunta cada 1,5 s y salta sola a la diapo de esa canción.
- Se puede abrir en el mismo portátil (proyector) o en otro aparato de la misma red: la tablet, otro
  ordenador… conectados a la misma wifi o al «Zona con cobertura inalámbrica móvil» del portátil (no hace
  falta internet).

También se puede lanzar suelto:  python -m src.diapos.proyectar presentacion.html
"""
import json
import os
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TRACKLIST = os.path.expandvars(r"%LOCALAPPDATA%\VirtualDJ\History\tracklist.txt")
PUERTO = 8765


MIXXX = os.path.expandvars(r"%LOCALAPPDATA%\Mixxx\mixxxdb.sqlite")


def _virtualdj(ruta=TRACKLIST):
    """('Artista - Título', momento) de la última línea del tracklist de VirtualDJ, o None."""
    try:
        momento = os.path.getmtime(ruta)
        with open(ruta, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 4096))
            lineas = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for linea in reversed(lineas):
        linea = linea.strip()
        if " : " in linea:
            return linea.split(" : ", 1)[1].strip(), "", momento
    return None


def _mixxx(ruta=MIXXX):
    """('Artista - Título', ruta del archivo, momento) de lo último que entró en el historial de Mixxx, o None.
    Mixxx apunta cada tema que suena en sus playlists ocultas de historial (hidden = 2)."""
    if not os.path.exists(ruta):
        return None
    import sqlite3
    from datetime import datetime, timezone
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=2)
        try:
            fila = con.execute("""
                SELECT l.artist, l.title, tl.location, pt.pl_datetime_added
                FROM PlaylistTracks pt JOIN Playlists p ON p.id = pt.playlist_id
                JOIN library l ON l.id = pt.track_id LEFT JOIN track_locations tl ON tl.id = l.location
                WHERE p.hidden = 2 ORDER BY pt.pl_datetime_added DESC, pt.id DESC LIMIT 1""").fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return None
    if not fila:
        return None
    artista, titulo, archivo, cuando = fila
    try:            # Mixxx guarda la hora en UTC
        momento = datetime.strptime(cuando[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        momento = 0
    return f"{artista or ''} - {titulo or ''}", (archivo or "").replace("/", "\\"), momento


def que_suena(tracklist=TRACKLIST, mixxx=MIXXX):
    """{'texto': 'Artista - Título', 'ruta': archivo o ''} de lo más reciente entre Mixxx y VirtualDJ."""
    fuentes = [f for f in (_mixxx(mixxx), _virtualdj(tracklist)) if f]
    if not fuentes:
        return {"texto": "", "ruta": ""}
    texto, ruta, _ = max(fuentes, key=lambda f: f[2])
    return {"texto": texto, "ruta": ruta}


def cancion_que_suena(ruta=TRACKLIST, mixxx=MIXXX):
    """'Artista - Título' de lo que suena (Mixxx o VirtualDJ), o ''."""
    return que_suena(ruta, mixxx)["texto"]


def ips_locales():
    """IPs de este ordenador en la red local (para abrir la presentación desde la tablet)."""
    ips = set()
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass
    try:                                    # la IP con la que se sale a la red (sin enviar nada)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.168.1.1", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(ips)


class Proyector:
    def __init__(self, ruta_html, tracklist=TRACKLIST, puerto=PUERTO, mixxx=MIXXX):
        self.ruta_html, self.tracklist, self.puerto, self.mixxx = ruta_html, tracklist, puerto, mixxx
        self._servidor = None

    def _manejador(self):
        proyector = self

        class Manejador(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/ahora"):
                    cuerpo = json.dumps(que_suena(proyector.tracklist, proyector.mixxx)).encode()
                    tipo = "application/json"
                else:
                    try:
                        with open(proyector.ruta_html, "rb") as f:
                            cuerpo = f.read()
                    except OSError:
                        self.send_error(404)
                        return
                    tipo = "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", tipo)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def log_message(self, *args):
                pass

        return Manejador

    def arrancar(self):
        """Arranca en segundo plano. Si el puerto está ocupado, prueba los siguientes."""
        for puerto in range(self.puerto, self.puerto + 10):
            try:
                self._servidor = ThreadingHTTPServer(("0.0.0.0", puerto), self._manejador())
                self.puerto = puerto
                break
            except OSError:
                continue
        if self._servidor is None:
            raise OSError("No hay ningún puerto libre para proyectar")
        threading.Thread(target=self._servidor.serve_forever, daemon=True).start()
        return self

    def cambiar_html(self, ruta_html):
        self.ruta_html = ruta_html

    @property
    def activo(self):
        return self._servidor is not None

    def direcciones(self):
        return [f"http://localhost:{self.puerto}"] + [f"http://{ip}:{self.puerto}" for ip in ips_locales()]

    def parar(self):
        if self._servidor is not None:
            self._servidor.shutdown()
            self._servidor.server_close()
            self._servidor = None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python -m src.diapos.proyectar presentacion.html")
    p = Proyector(sys.argv[1]).arrancar()
    print("Proyectando. Abre en el navegador:")
    for d in p.direcciones():
        print("   ", d)
    print("Canción que suena ahora:", cancion_que_suena() or "(ninguna)")
    webbrowser.open(p.direcciones()[0])
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        p.parar()
