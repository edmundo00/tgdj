import unittest

import pandas as pd

from src.motor.emparejar import Motor, cambios_de, contexto_disco, resumen, ya_revisada


def bd():
    filas = [
        ("Humillación", "Juan D'Arienzo", "Héctor Mauré", "1941-07-14", "tango", "Musica: Rodolfo Biagi - Letra: Carlos Bahr"),
        ("El olivo", "Juan D'Arienzo", "Héctor Mauré", "1941-01-14", "tango", ""),
        ("Ojos negros", "Roberto Firpo", "-", "1917", "tango", "Musica: Vicente Greco - Letra: ?"),
        ("Ojos negros", "Roberto Firpo", "-", "1937", "tango", "Musica: Vicente Greco - Letra: ?"),
        ("Ojos negros", "Roberto Firpo", "-", "1942-08-05", "tango", "Musica: Vicente Greco - Letra: ?"),
    ]
    db = pd.DataFrame(filas, columns=["titulo", "artista", "cantor", "fecha", "estilo", "compositor_autor"])
    for c in ("audio30", "audio10"):
        db[c] = ""
    db["origen"] = "recodo"
    db["fecha_ano"] = db["fecha"].str[:4]
    db["titulo_min"] = db["titulo"].str.lower().str.replace("ó", "o")
    db["artista_min"] = db["artista"]
    db["cantor_min"] = db["cantor"].str.lower()
    return db, {a: g for a, g in db.groupby("artista_min")}


def tags(titulo, artista, fecha="", genero="tango", compositor="", album=""):
    return [titulo, artista, fecha, genero, compositor, f"C:/x/{titulo}.mp3", album]


class MotorTest(unittest.TestCase):
    def setUp(self):
        db, dic = bd()
        self.motor = Motor(db=db, dic_art=dic)

    def test_perfecta_no_se_marca(self):
        c = self.motor.emparejar("x", tags("Humillación", "Juan D'Arienzo / Héctor Mauré", "1941-07-14",
                                           compositor="Musica: Rodolfo Biagi - Letra: Carlos Bahr"))
        self.assertEqual((c.categoria, c.seleccion), ("perfecta", None))
        self.assertEqual(cambios_de(c)[2], {})

    def test_sugerida_y_lo_que_cambia(self):
        c = self.motor.emparejar("x", tags("Humillacion", "Juan D'Arienzo / Héctor Mauré", "1941"))
        self.assertEqual(c.categoria, "preferida")
        _, _, dif = cambios_de(c)
        self.assertEqual(dif["title"], "Humillación")
        self.assertEqual(dif["year"], "1941-07-14")
        self.assertEqual(resumen(c)["sugerida"], 0)

    def test_fecha_de_cd_obliga_a_elegir(self):
        c = self.motor.emparejar("x", tags("Ojos negros", "Roberto Firpo", "2014-09-19"))
        self.assertEqual((c.categoria, c.seleccion), ("dudosa", None))
        self.assertIn("CD", c.motivo_fecha)
        self.assertEqual([str(f)[:4] for f in c.coincidencias["fecha"]], ["1917", "1937", "1942"])

    def test_sin_artista_y_sin_titulo(self):
        self.assertEqual(self.motor.emparejar("x", tags("Algo", "Orquesta Inventada")).categoria, "sin_artista")
        self.assertEqual(self.motor.emparejar("x", tags("Tema inexistente", "Roberto Firpo")).categoria, "sin_titulo")

    def test_contexto_del_disco(self):
        album = "Firpo 1937-1942"
        canciones = [
            self.motor.emparejar("a", tags("Humillacion", "Juan D'Arienzo / Héctor Mauré", "1941", album=album)),
            self.motor.emparejar("b", tags("El olivo", "Juan D'Arienzo / Héctor Mauré", "1941", album=album)),
            self.motor.emparejar("c", tags("Ojos negros", "Roberto Firpo", "2014", album=album)),
        ]
        contexto_disco(canciones)
        self.assertEqual(canciones[2].disco["encajan"], {2})       # solo la de 1942 encaja con 1941

    def test_ya_revisada(self):
        self.assertTrue(ya_revisada("Musica: X - Letra: ?"))
        self.assertFalse(ya_revisada("Musica: X"))


if __name__ == "__main__":
    unittest.main()
