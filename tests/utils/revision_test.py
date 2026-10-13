import os
import tempfile
import unittest

import pandas as pd

from src.diapos.generador import agrupar_tandas
from src.diapos.revision import revisar, horas_de_inicio, ERROR, AVISO, INFO
from src.utils.musicbee_playlist import leer_mbp


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.edmundo = os.path.join(self.dir, "MUSICA", "Edmundo")
        os.makedirs(self.edmundo)
        self.n = 0

    def cancion(self, artista, titulo, ano, genero="tango", carpeta=None, dur=180):
        self.n += 1
        ruta = os.path.join(carpeta or self.edmundo, f"{self.n:03}.flac")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        open(ruta, "wb").close()
        orq, _, cantor = artista.partition(" / ")
        return {"ruta": ruta, "title": titulo, "artist": artista, "artist1": orq, "artist2": cantor,
                "year": str(ano), "ano": str(ano), "genre": genero, "composer": "", "duration": float(dur)}

    def cortina(self, titulo="Cortina"):
        return self.cancion("Pop", titulo, 2020, "cortina entera", dur=120)

    def tanda(self, artista, anos=(1941, 1941, 1942), genero="tango", titulos=None):
        titulos = titulos or [f"{artista} {genero} {i}" for i in range(len(anos))]
        return [self.cancion(artista, t, a, genero) for t, a in zip(titulos, anos)]

    def revisar(self, filas, **kw):
        tandas = agrupar_tandas(pd.DataFrame(filas))
        return tandas, revisar(tandas, carpeta=self.edmundo, **kw)

    def textos(self, avisos, nivel=None):
        return [a.texto for a in avisos if nivel is None or a.nivel == nivel]



class RevisionTest(Base):
    def test_playlist_bien_hecha_sin_errores_ni_avisos(self):
        filas = (self.tanda("Juan D'Arienzo") + [self.cortina()] + self.tanda("Carlos di Sarli / Alberto Podestá")
                 + [self.cortina()] + self.tanda("Francisco Canaro", genero="tango vals") + [self.cortina()]
                 + self.tanda("Osvaldo Fresedo / Roberto Ray"))
        _, avisos = self.revisar(filas)
        self.assertEqual(self.textos(avisos, ERROR) + self.textos(avisos, AVISO), [])

    def test_fuera_de_la_carpeta_del_portatil(self):
        otra = os.path.join(self.dir, "MUSICA", "Dan")
        filas = self.tanda("Juan D'Arienzo")
        filas[1] = self.cancion("Juan D'Arienzo", "Pensalo bien", 1938, carpeta=otra)
        _, avisos = self.revisar(filas)
        errores = self.textos(avisos, ERROR)
        self.assertEqual(len(errores), 1)
        self.assertIn("Pensalo bien", errores[0])
        self.assertIn("portátil", errores[0])

    def test_falta_cortina_entre_dos_tandas_del_mismo_genero(self):
        filas = self.tanda("Juan D'Arienzo") + self.tanda("Carlos di Sarli")
        _, avisos = self.revisar(filas)
        self.assertTrue(any("sin cortina" in t for t in self.textos(avisos, ERROR)))

    def test_falta_cortina_entre_generos_distintos(self):
        filas = self.tanda("Juan D'Arienzo") + self.tanda("Francisco Canaro", genero="tango milonga")
        _, avisos = self.revisar(filas)
        self.assertTrue(any("Falta una cortina" in t for t in self.textos(avisos, ERROR)))

    def test_cortinas_seguidas(self):
        filas = self.tanda("Juan D'Arienzo") + [self.cortina("a"), self.cortina("b")] + self.tanda("Carlos di Sarli")
        _, avisos = self.revisar(filas)
        self.assertIn("2 cortinas seguidas", self.textos(avisos, AVISO))

    def test_numero_de_temas(self):
        filas = self.tanda("Juan D'Arienzo", anos=(1940, 1941)) + [self.cortina()] + self.tanda("Carlos di Sarli")
        _, avisos = self.revisar(filas)
        self.assertIn("Tanda 1: tiene 2 temas", self.textos(avisos, AVISO))

    def test_cantores_e_instrumentales_mezclados(self):
        filas = [self.cancion("Juan D'Arienzo / Alberto Echagüe", "a", 1939),
                 self.cancion("Juan D'Arienzo / Héctor Mauré", "b", 1941),
                 self.cancion("Juan D'Arienzo", "c", 1940)]
        _, avisos = self.revisar(filas)
        avisos_txt = self.textos(avisos, AVISO)
        self.assertTrue(any("instrumentales y cantadas" in t for t in avisos_txt))
        self.assertTrue(any("cantores distintos" in t for t in avisos_txt))

    def test_cantor_que_comparte_es_solo_info(self):
        filas = [self.cancion("Edgardo Donato / Horacio Lagos", "a", 1938, "tango vals"),
                 self.cancion("Edgardo Donato / Lita Morales y Horacio Lagos", "b", 1940, "tango vals"),
                 self.cancion("Edgardo Donato / Lita Morales y Horacio Lagos", "c", 1940, "tango vals")]
        _, avisos = self.revisar(filas)
        self.assertFalse(any("cantores" in t for t in self.textos(avisos, AVISO)))
        self.assertTrue(any("cantores" in t for t in self.textos(avisos, INFO)))

    def test_anos_muy_separados(self):
        _, avisos = self.revisar(self.tanda("Carlos di Sarli", anos=(1940, 1941, 1955)))
        self.assertIn("Tanda 1: años muy separados (1940 – 1955)", self.textos(avisos, AVISO))

    def test_vals_y_milonga_seguidos(self):
        filas = (self.tanda("Juan D'Arienzo") + [self.cortina()] + self.tanda("Biagi", genero="tango vals")
                 + [self.cortina()] + self.tanda("Canaro", genero="tango milonga"))
        _, avisos = self.revisar(filas)
        self.assertTrue(any("sin tango en medio" in t for t in self.textos(avisos, AVISO)))

    def test_orquesta_y_cantor_repetidos_cerca(self):
        filas = (self.tanda("Juan D'Arienzo") + [self.cortina()] + self.tanda("Carlos di Sarli / Roberto Rufino")
                 + [self.cortina()] + self.tanda("Juan D'Arienzo / Alberto Echagüe", anos=(1938, 1938, 1939))
                 + [self.cortina()] + self.tanda("Miguel Caló / Roberto Rufino"))
        _, avisos = self.revisar(filas)
        txt = self.textos(avisos, AVISO)
        self.assertTrue(any("Juan D'Arienzo en la Tanda 1 y otra vez en la Tanda 3" in t for t in txt))
        self.assertTrue(any("Cantor repetido" in t and "Rufino" in t for t in txt))

    def test_mismo_tema_dos_veces_en_la_noche(self):
        filas = (self.tanda("Enrique Rodríguez", titulos=["Mi piba (Mi piba linda)", "x", "y"]) + [self.cortina()]
                 + self.tanda("Ricardo Tanturi", titulos=["Mi piba", "z", "w"]))
        _, avisos = self.revisar(filas)
        self.assertTrue(any("suena dos veces" in t for t in self.textos(avisos, AVISO)))

    def test_duracion_y_horas(self):
        filas = self.tanda("Juan D'Arienzo") + [self.cortina()] + self.tanda("Carlos di Sarli")
        tandas, avisos = self.revisar(filas, inicio="21:00", fin="21:10")
        self.assertTrue(any("sobran" in t for t in self.textos(avisos, AVISO)))
        self.assertEqual(horas_de_inicio(tandas, "21:00"), ["21:00", "21:09", "21:10"])


class PatronTest(Base):
    GENEROS = {"T": "tango", "V": "tango vals", "M": "tango milonga"}

    def noche(self, letras, primera="Juan D'Arienzo"):
        """'TTVTTM' -> playlist con cortinas; cada tanda de una orquesta distinta."""
        filas = []
        for n, letra in enumerate(letras.replace(" ", "")):
            if filas:
                filas.append(self.cortina(f"c{n}"))
            orquesta = primera if n == 0 else f"Orquesta {n}"
            filas += self.tanda(orquesta, genero=self.GENEROS[letra])
        return filas

    def test_detecta_el_patron(self):
        from src.diapos.revision import detectar_patron, _genero_corto
        for letras, esperado in (("TTVTTMTTVTTM", "2-1-2-1"), ("TTTVTTTMTTTV", "3-1-3-1"),
                                 ("TTTTVTTTTMTTTTV", "4-1-4-1"), ("TTVTMTTVTM", "2-1-1-1")):
            tandas = agrupar_tandas(pd.DataFrame(self.noche(letras)))
            generos = [(i, _genero_corto(t.genero)) for i, t in enumerate(tandas) if not t.es_cortina]
            self.assertEqual(detectar_patron(generos)[0], esperado, letras)

    def test_patron_bien_seguido_sin_avisos_de_patron(self):
        _, avisos = self.revisar(self.noche("TTVTTMTTVTTM"), minutos_sin_milonga=0)
        self.assertFalse([t for t in self.textos(avisos, AVISO) if "patrón" in t or "otra vez" in t])
        self.assertTrue(any("Patrón detectado: 2-1-2-1" in t for t in self.textos(avisos, INFO)))

    def test_aqui_tocaria_milonga(self):
        _, avisos = self.revisar(self.noche("TTVTTMTTVTTTM"), minutos_sin_milonga=0)
        self.assertIn("Tanda 12: en tu patrón 2-1-2-1 aquí tocaría milonga (van 3 tandas de tango seguidas)",
                      self.textos(avisos, AVISO))

    def test_dos_valses_seguidos_en_el_ciclo(self):
        _, avisos = self.revisar(self.noche("TTVTTVTTMTTV"), minutos_sin_milonga=0)
        self.assertTrue(any("otra vez vals" in t and "tocaría milonga" in t for t in self.textos(avisos, AVISO)))

    def test_calentamiento_largo_es_solo_info(self):
        _, avisos = self.revisar(self.noche("TTTTVTTMTTVTTM"), minutos_sin_milonga=0)
        self.assertFalse([t for t in self.textos(avisos, AVISO) if "patrón" in t])
        self.assertTrue(any("calentar" in t for t in self.textos(avisos, INFO)))

    def test_patron_elegido_y_libre(self):
        _, avisos = self.revisar(self.noche("TTVTTMTTVTTM"), patron="3-1-3-1", minutos_sin_milonga=0)
        self.assertTrue(any("patrón 3-1-3-1" in t for t in self.textos(avisos, AVISO)))
        _, avisos = self.revisar(self.noche("TTVTTVTTTTM"), patron="libre", minutos_sin_milonga=0)
        self.assertFalse([t for t in self.textos(avisos) if "atrón" in t or "otra vez" in t])

    def test_sin_milonga_al_final(self):
        # cada tanda 9 min + 1 de cortina: la milonga 6 empieza en el minuto 50 de 59
        _, avisos = self.revisar(self.noche("TTVTTM"), inicio="21:00", minutos_sin_milonga=40)
        self.assertTrue(any("milonga (21:50) en los últimos 40 min" in t for t in self.textos(avisos, AVISO)))
        _, avisos = self.revisar(self.noche("TTVTTM"), minutos_sin_milonga=0)
        self.assertFalse(any("últimos" in t for t in self.textos(avisos)))

    def test_abrir_con_pugliese(self):
        _, avisos = self.revisar(self.noche("TTVTTM", primera="Osvaldo Pugliese"), minutos_sin_milonga=0)
        self.assertTrue(any("Abrir con Osvaldo Pugliese" in t for t in self.textos(avisos, INFO)))


class CumparsitaTest(Base):
    def test_al_final_va_sola_aunque_no_haya_cortina(self):
        filas = (self.tanda("Juan D'Arienzo") + [self.cortina()] + self.tanda("Carlos di Sarli / Alberto Podestá")
                 + [self.cancion("Juan D'Arienzo", "La cumparsita", 1971)])
        tandas, avisos = self.revisar(filas)
        self.assertTrue(tandas[-1].es_cumparsita)
        self.assertEqual(len(tandas[-2].canciones), 3)
        self.assertEqual(self.textos(avisos, ERROR) + self.textos(avisos, AVISO), [])
        self.assertTrue(any("Cierre con La Cumparsita" in t for t in self.textos(avisos, INFO)))

    def test_dentro_de_una_tanda_es_aviso(self):
        filas = (self.tanda("Juan D'Arienzo", titulos=["a", "La Cumparsita", "b"]) + [self.cortina()]
                 + self.tanda("Carlos di Sarli"))
        tandas, avisos = self.revisar(filas)
        self.assertFalse(any(t.es_cumparsita for t in tandas))
        self.assertTrue(any("va sola al final" in t for t in self.textos(avisos, AVISO)))


class LeerMbpTest(unittest.TestCase):
    def test_lee_todas_las_rutas_incluida_la_primera(self):
        rutas = ["D:\\Dropbox\\TDJ\\MUSICA\\Edmundo\\Firpo\\01. La maleva.flac",
                 "D:\\Dropbox\\TDJ\\MUSICA\\Edmundo\\" + "x" * 150 + "\\Canción larga.flac"]

        def cadena(texto):
            datos = texto.encode("utf-8")
            n, prefijo = len(datos), bytearray()
            while True:
                b = n & 0x7f
                n >>= 7
                prefijo.append(b | (0x80 if n else 0))
                if not n:
                    return bytes(prefijo) + datos

        contenido = (b"\x04\x00\x00\x00" + cadena("D:\\Dropbox\\TDJ\\MUSICBEE DATABASES\\tango\\") + b"\x00-2\x00"
                     + b"\xff" * 4 + b"\x2a\x00\x00\x00" + cadena(rutas[0]) + b"\xff" * 4 + cadena(rutas[1]))
        ruta = os.path.join(tempfile.mkdtemp(), "milonga.mbp")
        with open(ruta, "wb") as f:
            f.write(contenido)
        self.assertEqual(leer_mbp(ruta), rutas)


if __name__ == "__main__":
    unittest.main()
