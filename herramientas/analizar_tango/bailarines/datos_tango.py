"""Datos del análisis de un tango (analizar_tango.py) puestos en el tiempo de un vídeo de baile.

    d = DatosTango(cancion_flac, inicio)      # inicio = segundo de la canción donde empieza el vídeo
    d.pulsos  -> [(t_video, compás, tiempo)]
    d.golpes  -> {"piano": [(t_video, fuerza_db)], "contrabajo": [...], ...}
    d.semicorchea(t) -> (compás, tiempo, 0-3)   0 = número, 1 = e, 2 = y, 3 = a
"""
import os, sys, csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rutas
ANALISIS = rutas.ANALISIS
HERR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # ...\analizar_tango
PY = rutas.python_de("analizar_tango")
NOM = ["", "e", "y", "a"]


def carpeta_datos(cancion):
    """donde analizar_tango.py guarda (o guardaría) el análisis de esa canción."""
    nombre = os.path.splitext(os.path.basename(cancion))[0]
    antigua = os.path.join(ANALISIS, nombre)
    return antigua if os.path.isdir(antigua) else os.path.join(ANALISIS, "_datos", nombre)


def leer(carpeta, nombre):
    with open(os.path.join(carpeta, nombre), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


class DatosTango:
    def __init__(self, cancion, inicio):
        self.cancion, self.inicio = cancion, inicio
        self.carpeta = carpeta_datos(cancion)
        self.pulsos = [(float(r["seg"]) - inicio, int(r["compas"]), int(r["tiempo"])) for r in leer(self.carpeta, "pulsos.csv")]
        self.golpes = {}
        for r in leer(self.carpeta, "golpes.csv"):
            self.golpes.setdefault(r["pista"], []).append((float(r["seg"]) - inicio, float(r["fuerza_db"])))

    def semicorchea(self, t):
        P = self.pulsos
        for i in range(len(P) - 1):
            t0, c, k = P[i]
            t1 = P[i + 1][0]
            if t0 - 0.06 <= t < t1 - 0.06:
                s = round((t - t0) / (t1 - t0) * 4)
                if s == 4:
                    return P[i + 1][1], P[i + 1][2], 0
                return c, k, max(0, s)
        return None

    def donde(self, t):
        """(compás, casilla 0-7 de «1 y 2 y 3 y 4 y») para la rejilla de los reels."""
        P = self.pulsos
        for i in range(len(P) - 1):
            t0, c, k = P[i]
            t1 = P[i + 1][0]
            if t0 <= t < t1:
                return c, (k - 1) * 2 + min(int((t - t0) / (t1 - t0) * 2), 1)
        return None

    def compases(self, desde, hasta):
        """(t_inicio, t_fin) en el vídeo del compás 'desde' al final del compás 'hasta'."""
        ini = [t for t, c, k in self.pulsos if c == desde and k == 1]
        fin = [t for t, c, k in self.pulsos if c == hasta + 1 and k == 1]
        if not ini:
            raise SystemExit(f"No encuentro el compás {desde} en el análisis")
        return ini[0], (fin[0] if fin else self.pulsos[-1][0])
