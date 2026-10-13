import os
import tempfile
import unittest
from datetime import date

import pandas as pd

from src.diapos import bpm, historial
from src.diapos.generador import agrupar_tandas
from src.diapos.revision import revisar, AVISO, ERROR, INFO
from tests.utils.caracter_test import tabla_temporal
from tests.utils.revision_test import Base


class CortinasTest(Base):
    def setUp(self):
        super().setUp()
        self.tabla = tabla_temporal()

    def cortina_con(self, titulo, artista="Pop", actividad=None, dur=120):
        c = self.cancion(artista, titulo, 2020, "cortina entera", dur=dur)
        c["actividad"] = actividad
        return c

    def revisar_cortinas(self, filas, hist=()):
        tandas = agrupar_tandas(pd.DataFrame(filas))
        return revisar(tandas, carpeta=self.edmundo, minutos_sin_milonga=0, archivo_caracter=self.tabla,
                       historial=hist)

    def textos(self, avisos, nivel=None):
        return [a.texto for a in avisos if nivel is None or a.nivel == nivel]

    def test_cortina_repetida_en_la_noche(self):
        c = self.cortina_con("Careless Whisper")
        filas = self.tanda("Juan D'Arienzo") + [c] + self.tanda("Carlos di Sarli") + [dict(c)] + self.tanda("Biagi")
        avisos = self.revisar_cortinas(filas)
        self.assertTrue(any("la cortina «Careless Whisper» ya sonó" in t for t in self.textos(avisos, ERROR)))

    def test_cortina_muy_corta_y_que_suena_a_tango(self):
        filas = (self.tanda("Juan D'Arienzo") + [self.cortina_con("Corta", dur=15)] + self.tanda("Carlos di Sarli")
                 + [self.cortina_con("Ventarrón", artista="Osvaldo Pugliese")] + self.tanda("Biagi"))
        txt = self.textos(self.revisar_cortinas(filas), AVISO)
        self.assertTrue(any("dura solo 15 s" in t for t in txt))
        self.assertTrue(any("«Ventarrón» (Osvaldo Pugliese) parece de tango" in t for t in txt))

    def test_mismo_artista_de_cortina(self):
        filas = self.tanda("A")
        for n in range(3):
            filas += [self.cortina_con(f"c{n}", artista="Scott Bradlee")] + self.tanda(f"B{n}")
        info = self.textos(self.revisar_cortinas(filas), INFO)
        self.assertTrue(any("3 cortinas de Scott Bradlee" in t for t in info))
        self.assertTrue(any("dos cortinas seguidas de Scott Bradlee" in t for t in info))

    def test_cortina_que_no_anuncia_lo_que_viene(self):
        filas = (self.tanda("Carlos di Sarli") + [self.cortina_con("Mad World", actividad=4.0)]
                 + self.tanda("Juan D'Arienzo", anos=(1937, 1937, 1938))                       # energía 5
                 + [self.cortina_con("Conga", actividad=22.0)]
                 + self.tanda("Osvaldo Fresedo", anos=(1935, 1935, 1936)))                     # energía 2
        info = self.textos(self.revisar_cortinas(filas), INFO)
        self.assertTrue(any("«Mad World» es muy tranquila" in t for t in info))
        self.assertTrue(any("«Conga» es muy animada" in t for t in info))

    def test_historial_cortinas_y_tandas(self):
        dar = self.tanda("Juan D'Arienzo")
        c = self.cortina_con("Despechá")
        filas = dar + [c] + self.tanda("Carlos di Sarli") + [self.cortina_con("Otra")] + self.tanda("Biagi")
        antes = historial.Milonga(date(2026, 1, 1), "260101_Milonga_Mia",
                                  {historial.clave(dar[0]["ruta"]), historial.clave(dar[1]["ruta"]),
                                   historial.clave(c["ruta"])})
        info = self.textos(self.revisar_cortinas(filas, [antes]), INFO)
        self.assertTrue(any("Tanda 1 (Juan D'Arienzo): 2 de sus 3 temas ya sonaron en 260101_Milonga_Mia" in t
                            for t in info))
        self.assertTrue(any("la cortina «Despechá» ya sonó en 260101_Milonga_Mia (01/01/2026)" in t for t in info))

    def test_noche_casi_igual_un_solo_aviso(self):
        filas, claves = [], set()
        for n in range(4):
            if filas:
                filas.append(self.cortina_con(f"c{n}"))
            filas += self.tanda(f"Orquesta {n}")
        claves = {historial.clave(f["ruta"]) for f in filas}
        antes = historial.Milonga(date(2026, 1, 1), "260101_Milonga_Mia", claves)
        avisos = self.revisar_cortinas(filas, [antes])
        txt = self.textos(avisos)
        self.assertTrue(any("Es casi la misma playlist que 260101_Milonga_Mia" in t for t in txt))
        self.assertFalse(any("ya sonaron" in t or "ya sonó en" in t for t in txt))


class HistorialTest(unittest.TestCase):
    def test_fecha_y_lugar(self):
        self.assertEqual(historial.fecha_y_lugar("261013_Milonga_Mia.mbp"), (date(2026, 10, 13), "milonga mia"))
        self.assertEqual(historial.fecha_y_lugar("240217  Glorieta.mbp"), (date(2024, 2, 17), "glorieta"))
        self.assertEqual(historial.fecha_y_lugar("2502xx_xxxxxx.mbp"), (None, None))
        self.assertEqual(historial.fecha_y_lugar("MIS TANDAS.mbp"), (None, None))

    def test_anteriores_mismo_lugar_y_fecha(self):
        carpeta = tempfile.mkdtemp()

        def m3u(nombre, rutas):
            with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as f:
                f.write("\n".join(rutas) + "\n")

        m3u("261013_Milonga_Mia.m3u", [r"D:\Dropbox\TDJ\MUSICA\Edmundo\a.flac"])
        m3u("260601_Milonga_Mia.m3u", [r"D:\Dropbox\TDJ\MUSICA\Edmundo\a.flac"])
        m3u("260801_Milonga Mia.m3u", [r"C:\Dropbox\TDJ\MUSICA\Edmundo\b.flac"])
        m3u("260901_Desbande.m3u", [r"D:\Dropbox\TDJ\MUSICA\Edmundo\c.flac"])
        m3u("240101_Milonga_Mia.m3u", [r"D:\Dropbox\TDJ\MUSICA\Edmundo\d.flac"])     # hace más de un año
        m3u("261101_Milonga_Mia.m3u", [r"D:\Dropbox\TDJ\MUSICA\Edmundo\e.flac"])     # después
        lista = historial.anteriores(os.path.join(carpeta, "261013_Milonga_Mia.m3u"))
        self.assertEqual([m.nombre for m in lista], ["260801_Milonga Mia", "260601_Milonga_Mia"])
        self.assertEqual(lista[0].claves, {r"tdj\musica\edmundo\b.flac"})


class ActividadTest(unittest.TestCase):
    def test_animada_tiene_mas_actividad_que_tranquila(self):
        from tests.utils.bpm_test import metronomo
        import numpy as np
        tranquila = (np.sin(2 * np.pi * 220 * np.arange(bpm.FRECUENCIA * 30) / bpm.FRECUENCIA) * 0.3).astype(np.float32)
        animada = metronomo(128)
        self.assertLess(bpm.actividad(tranquila), bpm.actividad(animada))


if __name__ == "__main__":
    unittest.main()
