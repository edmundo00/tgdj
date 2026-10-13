import datetime
import json
import os
import tempfile
import unittest
import urllib.request

import pandas as pd

from src.diapos import proyectar, web
from src.diapos.generador import agrupar_tandas
from tests.utils.revision_test import Base

DATOS = {"milonga": "Milonga Mia", "fecha": datetime.date(2026, 10, 13), "inicio": "21:00", "fin": "00:00"}


class WebTest(Base):
    def noche(self):
        filas = (self.tanda("Juan D'Arienzo", titulos=["Uno", "Dos", "Tres"]) + [self.cortina("Clandestina")]
                 + self.tanda("Orquesta Sin Foto Ninguna", genero="tango vals")
                 + [self.cancion("Juan D'Arienzo", "La cumparsita", 1951)])
        return agrupar_tandas(pd.DataFrame(filas))

    def test_una_diapo_por_tema_y_la_cortina_anuncia_la_proxima(self):
        lista, _ = web.diapos(self.noche(), DATOS)
        tipos = [d["tipo"] for d in lista]
        self.assertEqual(tipos, ["portada", "tema", "tema", "tema", "cortina", "tema", "tema", "tema", "cumparsita"])
        self.assertEqual([d["actual"] for d in lista[1:4]], [0, 1, 2])
        self.assertEqual(lista[2]["clave"], "Juan D'Arienzo - Dos")
        self.assertEqual(lista[4]["proxima"]["genero"], "vals")
        self.assertIsNone(lista[5]["foto"])                       # sin foto: emblema con iniciales
        self.assertEqual(lista[5]["iniciales"], "SN")
        self.assertEqual(lista[0]["tandas"][1]["genero"], "vals")

    def test_archivo_html_y_modo_en_vivo(self):
        dir_ = tempfile.mkdtemp()
        html = web.crear_web(self.noche(), DATOS, os.path.join(dir_, "milonga.html"))
        contenido = open(html, encoding="utf-8").read()
        self.assertIn('"clave": "Juan D\'Arienzo - Tres"', contenido)
        self.assertNotIn("__DIAPOS__", contenido)
        self.assertNotIn("__HUELLAS__", contenido)
        self.assertIn("const HUELLAS = {", contenido)
        tracklist = os.path.join(dir_, "tracklist.txt")
        with open(tracklist, "w", encoding="utf-8") as f:
            f.write("21:00 : Juan D'Arienzo - Uno\n21:03 : Juan D'Arienzo - Dos\n\n")
        sin_mixxx = os.path.join(dir_, "sin_mixxx.sqlite")
        self.assertEqual(proyectar.cancion_que_suena(tracklist, sin_mixxx), "Juan D'Arienzo - Dos")
        self.assertEqual(proyectar.cancion_que_suena(os.path.join(dir_, "no_existe.txt"), sin_mixxx), "")
        p = proyectar.Proyector(html, tracklist=tracklist, puerto=8811, mixxx=sin_mixxx).arrancar()
        try:
            base = p.direcciones()[0]
            self.assertEqual(json.load(urllib.request.urlopen(base + "/ahora"))["texto"], "Juan D'Arienzo - Dos")
            self.assertIn(b"Milonga Mia", urllib.request.urlopen(base + "/").read())
        finally:
            p.parar()


class ListaYQrTest(Base):
    def test_lista_ligera_y_qr(self):
        filas = (self.tanda("Juan D'Arienzo", titulos=["Uno", "Dos", "Tres"]) + [self.cortina("Clandestina")]
                 + self.tanda("Carlos di Sarli", genero="tango vals"))
        tandas = agrupar_tandas(pd.DataFrame(filas))
        datos = dict(DATOS, milonga="Milonga Mía")
        self.assertEqual(web.nombre_web(datos), "261013-milonga-mia.html")
        self.assertEqual(web.nombre_lista(datos), "261013-milonga-mia-lista.html")
        dir_ = tempfile.mkdtemp()
        lista = open(web.crear_lista(tandas, datos, os.path.join(dir_, "lista.html")), encoding="utf-8").read()
        self.assertIn("Dos", lista)
        self.assertIn("Cortina · <b>Clandestina</b>", lista)   # las cortinas también salen
        self.assertLess(len(lista), 20000)
        html = open(web.crear_web(tandas, datos, os.path.join(dir_, "p.html"), reconocer=False,
                                  url_lista="https://ejemplo.org/lista.html"), encoding="utf-8").read()
        self.assertIn('id="qr"', html)
        self.assertIn("<svg", html)
        self.assertNotIn("__QR__", html)
        self.assertIn("mírala en casa", html)                   # en el sótano no hay internet
        for cosa in ('id="listo"', 'id="b-ensayo"', 'id="tinte"', "getBattery", "PLANTILLAS", "data-punto"):
            self.assertIn(cosa, html)


def mixxx_falso(ruta, canciones):
    """Base de datos mínima de Mixxx con su historial: canciones = [(artista, título, archivo, 'AAAA-MM-DD hh:mm:ss')]."""
    import sqlite3
    con = sqlite3.connect(ruta)
    con.executescript("""
        CREATE TABLE Playlists (id INTEGER PRIMARY KEY, name TEXT, hidden INTEGER);
        CREATE TABLE PlaylistTracks (id INTEGER PRIMARY KEY, playlist_id INTEGER, track_id INTEGER,
                                     position INTEGER, pl_datetime_added TEXT);
        CREATE TABLE library (id INTEGER PRIMARY KEY, artist TEXT, title TEXT, location INTEGER);
        CREATE TABLE track_locations (id INTEGER PRIMARY KEY, location TEXT);
        INSERT INTO Playlists VALUES (1, 'una lista normal', 0), (2, '2026-10-13', 2);""")
    for n, (artista, titulo, archivo, cuando) in enumerate(canciones, 1):
        con.execute("INSERT INTO track_locations VALUES (?, ?)", (n, archivo))
        con.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (n, artista, titulo, n))
        con.execute("INSERT INTO PlaylistTracks VALUES (?, 2, ?, ?, ?)", (n, n, n, cuando))
    con.commit()
    con.close()


class MixxxTest(unittest.TestCase):
    def test_lo_ultimo_del_historial_de_mixxx(self):
        dir_ = tempfile.mkdtemp()
        db = os.path.join(dir_, "mixxxdb.sqlite")
        mixxx_falso(db, [("Juan D'Arienzo", "Uno", "D:/Dropbox/TDJ/MUSICA/Edmundo/uno.flac", "2026-10-13 19:01:00"),
                         ("Juan D'Arienzo", "Dos", "D:/Dropbox/TDJ/MUSICA/Edmundo/dos.flac", "2026-10-13 19:04:00")])
        r = proyectar.que_suena(tracklist=os.path.join(dir_, "no_hay.txt"), mixxx=db)
        self.assertEqual(r, {"texto": "Juan D'Arienzo - Dos", "ruta": r"D:\Dropbox\TDJ\MUSICA\Edmundo\dos.flac"})
        self.assertEqual(proyectar.que_suena(os.path.join(dir_, "a"), os.path.join(dir_, "b")),
                         {"texto": "", "ruta": ""})

    def test_historial_de_la_noche(self):
        dir_ = tempfile.mkdtemp()
        db = os.path.join(dir_, "mixxxdb.sqlite")
        # Mixxx guarda en UTC: en Barcelona en octubre (UTC+2) las 21:05 son las 19:05
        mixxx_falso(db, [("A", "Antes", "D:/m/antes.flac", "2026-10-13 15:00:00"),
                         ("A", "Uno", "D:/m/uno.flac", "2026-10-13 19:05:00"),
                         ("A", "Uno", "D:/m/uno.flac", "2026-10-13 19:05:30"),       # cargado dos veces
                         ("A", "Dos", "D:/m/dos.flac", "2026-10-13 19:08:00"),
                         ("A", "Uno", "D:/m/uno.flac", "2026-10-13 22:10:00")])      # después de medianoche
        utc = datetime.timezone.utc
        desde = datetime.datetime(2026, 10, 13, 18, 0, tzinfo=utc)
        hasta = datetime.datetime(2026, 10, 14, 0, 0, tzinfo=utc)
        self.assertEqual(proyectar.historial_mixxx(desde, hasta, db),
                         [r"D:\m\uno.flac", r"D:\m\dos.flac", r"D:\m\uno.flac"])


class PublicarTest(unittest.TestCase):
    def test_publicar_en_un_repositorio(self):
        import subprocess
        from src.diapos import publicar
        dir_ = tempfile.mkdtemp()
        quien = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                     GIT_COMMITTER_EMAIL="t@t")
        remoto = os.path.join(dir_, "remoto.git")
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", remoto], check=True)
        semilla = os.path.join(dir_, "semilla")
        subprocess.run(["git", "clone", "-q", remoto, semilla], check=True, capture_output=True)
        with open(os.path.join(semilla, "README.md"), "w") as f:
            f.write("x")
        for args in (["add", "."], ["commit", "-qm", "x"], ["push", "-q", "origin", "HEAD:main"]):
            subprocess.run(["git", *args], cwd=semilla, check=True, env=quien)
        noche = os.path.join(dir_, "261013-milonga-mia.html")
        lista = os.path.join(dir_, "261013-milonga-mia-lista.html")
        for ruta, titulo in ((noche, "Milonga Mia · 13 de octubre"), (lista, "lista")):
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(f"<title>{titulo}</title>")
        copia = os.path.join(dir_, "copia")
        antes = dict(os.environ)
        os.environ.update(quien)
        try:
            url = publicar.publicar([noche, lista], "prueba", carpeta=copia, remoto=remoto)
            publicar.publicar([noche], "otra vez, sin cambios", carpeta=copia, remoto=remoto)   # no falla
        finally:
            os.environ.clear()
            os.environ.update(antes)
        self.assertTrue(url.endswith("/261013-milonga-mia.html"))
        indice = open(os.path.join(copia, "index.html"), encoding="utf-8").read()
        self.assertIn("Milonga Mia · 13 de octubre", indice)
        self.assertIn('href="261013-milonga-mia-lista.html"', indice)
        subidos = subprocess.run(["git", "ls-tree", "--name-only", "main"], cwd=remoto, capture_output=True,
                                 text=True).stdout.split()
        self.assertEqual(sorted(subidos), ["261013-milonga-mia-lista.html", "261013-milonga-mia.html", "README.md",
                                           "index.html"])


if __name__ == "__main__":
    unittest.main()
