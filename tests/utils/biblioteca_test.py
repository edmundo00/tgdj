import os
import shutil
import tempfile
import time
import unittest
from types import SimpleNamespace

from src.biblioteca.biblioteca import Biblioteca


def escribir(ruta, contenido):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(contenido)


def leer_falso(ruta):
    """Lector de tags de prueba: el título es el nombre del archivo."""
    if "roto" in ruta:
        raise ValueError("archivo dañado")
    return SimpleNamespace(title=os.path.splitext(os.path.basename(ruta))[0], artist="Roberto Firpo",
                           album="", year="1940", genre="tango", composer="")


class BibliotecaTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.musica = os.path.join(self.dir, "MUSICA")
        self.bandeja = os.path.join(self.dir, "TIDAL Download")
        escribir(os.path.join(self.musica, "Edmundo", "Firpo", "Ojos negros.flac"), os.urandom(5000))
        escribir(os.path.join(self.musica, "Eduardo", "1", "La taba.mp3"), os.urandom(6000))
        escribir(os.path.join(self.musica, "musica_variada_edmundo", "Pop.mp3"), os.urandom(7000))
        escribir(os.path.join(self.musica, "_duplicados", "Edmundo", "x.mp3"), os.urandom(7100))
        escribir(os.path.join(self.musica, "Edmundo", "notas.txt"), b"no es audio")
        config = {"raices": [
            {"ruta": self.musica, "subcarpetas_son_colecciones": True, "excluir": ["musica_variada_edmundo"]},
            {"ruta": self.bandeja, "subcarpetas_son_colecciones": False, "excluir": []}]}
        self.bib = Biblioteca(os.path.join(self.dir, "bib.sqlite"), config=config)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def actualizar(self):
        return self.bib.actualizar(leer=leer_falso)

    def test_primera_construccion(self):
        inf = self.actualizar()
        self.assertEqual((inf["nuevas"], inf["leidas"]), (2, 2))       # sin variada, _duplicados ni .txt
        df = self.bib.dataframe()
        self.assertEqual(sorted(df["coleccion"]), ["Edmundo", "Eduardo"])
        self.assertEqual(set(df["title"]), {"Ojos negros", "La taba"})
        self.assertTrue((df["creado"] > 0).all())

    def test_segunda_vez_no_lee_nada(self):
        self.actualizar()
        inf = self.actualizar()
        self.assertEqual((inf["nuevas"], inf["cambiadas"], inf["leidas"]), (0, 0, 0))

    def test_nueva_en_la_bandeja_y_luego_movida_a_musica(self):
        self.actualizar()
        descarga = os.path.join(self.bandeja, "Playlists", "download", "El resplandor.flac")
        escribir(descarga, os.urandom(8000))
        inf = self.actualizar()
        self.assertEqual(inf["nuevas"], 1)
        fila = self.bib.dataframe("ruta=?", (descarga,)).iloc[0]
        self.assertEqual(fila["coleccion"], "TIDAL Download")
        llegada, identificador = fila["visto_primera"], fila["id"]

        destino = os.path.join(self.musica, "Edmundo", "Firpo", "El resplandor.flac")
        time.sleep(0.01)
        shutil.move(descarga, destino)
        inf = self.actualizar()
        self.assertEqual((inf["movidas"], inf["nuevas"], inf["borradas"]), (1, 0, 0))
        fila = self.bib.dataframe("ruta=?", (destino,)).iloc[0]
        self.assertEqual((fila["id"], fila["visto_primera"], fila["coleccion"]), (identificador, llegada, "Edmundo"))

    def test_cambiada_se_vuelve_a_leer(self):
        self.actualizar()
        ruta = os.path.join(self.musica, "Eduardo", "1", "La taba.mp3")
        escribir(ruta, os.urandom(6100))
        inf = self.actualizar()
        self.assertEqual((inf["cambiadas"], inf["leidas"]), (1, 1))

    def test_borrada_y_error(self):
        self.actualizar()
        os.remove(os.path.join(self.musica, "Eduardo", "1", "La taba.mp3"))
        escribir(os.path.join(self.musica, "Eduardo", "roto.mp3"), os.urandom(100))
        inf = self.actualizar()
        self.assertEqual((inf["borradas"], inf["errores"]), (1, 1))
        self.assertIn("dañado", self.bib.dataframe("ruta LIKE ?", ("%roto%",)).iloc[0]["error"])

    def test_cancelar_y_seguir(self):
        for i in range(450):
            escribir(os.path.join(self.musica, "Dan", f"{i}.mp3"), os.urandom(50 + i))
        llamadas = {"n": 0}

        def cancelar():
            llamadas["n"] += 1
            return llamadas["n"] > 250
        self.bib.actualizar(leer=leer_falso, cancelado=cancelar)
        pendientes = len(self.bib.dataframe("tags_leidas=0"))
        self.assertGreater(pendientes, 0)
        self.actualizar()
        self.assertEqual(len(self.bib.dataframe("tags_leidas=0")), 0)

    def test_sesiones(self):
        self.assertIsNone(self.bib.inicio_sesion_anterior())
        self.bib.empezar_sesion()
        primera = float(self.bib.meta("sesion_actual"))
        self.bib.empezar_sesion()
        self.assertEqual(self.bib.inicio_sesion_anterior(), primera)


class EmparejarTest(unittest.TestCase):
    """Nivel 3: estado de cada canción guardado y versión de reglas."""

    def setUp(self):
        from tests.utils.motor_test import bd
        from src.motor.emparejar import Motor, resumen
        self.dir = tempfile.mkdtemp()
        musica = os.path.join(self.dir, "MUSICA")
        for nombre in ("Humillacion", "Ojos negros", "Desconocida"):
            escribir(os.path.join(musica, "Edmundo", nombre + ".mp3"), os.urandom(3000 + len(nombre)))
        config = {"raices": [{"ruta": musica, "subcarpetas_son_colecciones": True, "excluir": []}]}
        self.bib = Biblioteca(os.path.join(self.dir, "bib.sqlite"), config=config)
        tags = {"Humillacion": ("Juan D'Arienzo / Héctor Mauré", "1941"), "Ojos negros": ("Roberto Firpo", "2014"),
                "Desconocida": ("Orquesta Inventada", "1950")}

        def leer(ruta):
            t = os.path.splitext(os.path.basename(ruta))[0]
            return SimpleNamespace(title=t, artist=tags[t][0], album="", year=tags[t][1], genre="tango", composer="")
        self.bib.actualizar(leer=leer)
        db, dic = bd()
        motor = Motor(db=db, dic_art=dic)
        self.lote = lambda filas: [(i, resumen(motor.emparejar(r, t))) for i, r, t in filas]

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_guarda_el_estado_y_no_repite(self):
        inf = self.bib.emparejar("v1", funcion_lote=self.lote)
        self.assertEqual((inf["emparejadas"], inf["total"]), (3, 3))
        df = self.bib.dataframe().set_index("title")
        self.assertEqual(df.loc["Humillacion", "estado"], "preferida")
        self.assertIn("1941-07-14", df.loc["Humillacion", "cambios"])
        self.assertEqual(df.loc["Ojos negros", "estado"], "dudosa")
        self.assertIn("CD", df.loc["Ojos negros", "motivo_fecha"])
        self.assertEqual(df.loc["Desconocida", "estado"], "sin_artista")
        self.assertEqual(self.bib.emparejar("v1", funcion_lote=self.lote)["total"], 0)   # ya hecho

    def test_otras_reglas_vuelven_a_emparejar(self):
        self.bib.emparejar("v1", funcion_lote=self.lote)
        self.assertEqual(self.bib.emparejar("v2", funcion_lote=self.lote)["total"], 3)

    def test_archivo_cambiado_vuelve_a_emparejarse(self):
        self.bib.emparejar("v1", funcion_lote=self.lote)
        ruta = self.bib.dataframe("title=?", ("Desconocida",)).iloc[0]["ruta"]
        escribir(ruta, os.urandom(9999))
        self.bib.actualizar(leer=lambda r: SimpleNamespace(title="Desconocida", artist="Orquesta Inventada",
                                                           album="", year="", genre="", composer=""))
        self.assertEqual(self.bib.emparejar("v1", funcion_lote=self.lote)["total"], 1)


if __name__ == "__main__":
    unittest.main()
