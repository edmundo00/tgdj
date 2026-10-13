import os
import tempfile
import unittest
import wave

import numpy as np
import pandas as pd

from src.diapos import bpm
from src.diapos.generador import agrupar_tandas
from src.diapos.revision import revisar, AVISO, INFO
from tests.utils.bpm_test import metronomo
from tests.utils.revision_test import Base


def wav(ruta, muestras):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(bpm.FRECUENCIA)
        w.writeframes((np.clip(muestras, -1, 1) * 32000).astype(np.int16).tobytes())


class MedidasTest(unittest.TestCase):
    def test_nivel(self):
        seno = np.sin(np.arange(bpm.FRECUENCIA) / 5).astype(np.float32)        # RMS 0,707 -> -3 dB
        self.assertAlmostEqual(bpm.nivel(seno), -3.0, delta=0.2)
        self.assertAlmostEqual(bpm.nivel(seno * 0.1), -23.0, delta=0.2)

    def test_silencios_y_medidas_de_un_archivo(self):
        f = bpm.FRECUENCIA
        musica = metronomo(120, segundos=40) * 3
        muestras = np.concatenate([np.zeros(5 * f, np.float32), musica, np.zeros(2 * f, np.float32)])
        dir_ = tempfile.mkdtemp()
        ruta = os.path.join(dir_, "Dropbox", "TDJ", "MUSICA", "Edmundo", "tema.wav")
        wav(ruta, muestras)
        ini, fin = bpm.silencios(ruta)
        self.assertAlmostEqual(ini, 5.0, delta=0.15)
        self.assertAlmostEqual(fin, 2.0, delta=0.3)
        cache = bpm.CacheBpm(os.path.join(dir_, "bpm.sqlite"))
        m = cache.medidas(ruta, "tango")
        self.assertAlmostEqual(m["bpm"], 120, delta=2)
        self.assertAlmostEqual(m["silencio_inicio"], 5.0, delta=0.15)
        self.assertIsNotNone(m["volumen"])
        # la segunda vez sale de la caché (sin leer el audio)
        self.assertEqual(cache.medidas(ruta, "tango", calcular_si_falta=False), m)
        c = cache.medidas(ruta, "cortina entera", es_cortina=True)
        self.assertEqual(set(c), {"actividad", "volumen"})


class RevisionVolumenTest(Base):
    def tanda_con(self, artista, volumenes, silencios=((0.5, 3),) * 3, genero="tango"):
        filas = self.tanda(artista, genero=genero)
        for f, v, (ini, fin) in zip(filas, volumenes, silencios):
            f.update(volumen=v, silencio_inicio=ini, silencio_fin=fin)
        return filas

    def revisar_vol(self, *tandas, cortina_volumen=None):
        filas = []
        for n, t in enumerate(tandas):
            if filas:
                c = self.cortina(f"c{n}")
                c["volumen"] = cortina_volumen
                filas.append(c)
            filas += t
        avisos = revisar(agrupar_tandas(pd.DataFrame(filas)), carpeta=self.edmundo, minutos_sin_milonga=0)
        return [(a.nivel, a.texto) for a in avisos]

    def test_tema_mas_fuerte_en_la_tanda(self):
        avisos = self.revisar_vol(self.tanda_con("Ricardo Tanturi", [-21.8, -21.1, -14.0]))
        self.assertIn((AVISO, "Tanda 1: «Ricardo Tanturi tango 2» suena 7 dB más fuerte que el resto de la tanda: "
                              "ajusta la ganancia"), avisos)
        avisos = self.revisar_vol(self.tanda_con("Ricardo Tanturi", [-15, -16, -17]))
        self.assertFalse([t for _, t in avisos if "dB" in t])

    def test_silencios(self):
        avisos = self.revisar_vol(self.tanda_con("A", [-15] * 3, [(4.5, 3), (0.5, 9.5), (0.5, 9)]))
        textos = dict((t, n) for n, t in avisos)
        self.assertEqual(textos.get("Tanda 1: «A tango 0» empieza con 4 s de silencio: quedará un hueco en la pista")
                         or textos.get("Tanda 1: «A tango 0» empieza con 5 s de silencio: quedará un hueco en la pista"),
                         AVISO)
        self.assertTrue(any(n == AVISO and "«A tango 1» acaba con" in t and "hueco" in t for n, t in avisos))
        self.assertTrue(any(n == INFO and "«A tango 2» acaba con 9 s de silencio" in t for n, t in avisos))

    def test_salto_entre_tandas_y_cortinas_fuertes(self):
        avisos = self.revisar_vol(self.tanda_con("A", [-12] * 3), self.tanda_con("B", [-20] * 3), cortina_volumen=-4)
        self.assertTrue(any(n == INFO and "Tanda 2: suena 8 dB más baja que la anterior" in t for n, t in avisos))
        self.assertTrue(any(n == INFO and "Las cortinas suenan de media" in t for n, t in avisos))

    def test_archivos_que_no_suenan_bien(self):
        filas = self.tanda("A", titulos=["Dañado", "Mudo", "Cortado"])
        filas += [self.cancion("A", "Disco entero", 1941, dur=40 * 60), self.cancion("A", "Sin medir", 1941)]
        for f, vol, medido in zip(filas, [None, -60, -15, -15, None], [True, True, True, True, float("nan")]):
            f.update(volumen=vol, medido=medido)
        filas[2]["duration"] = 12
        textos = [t for n, t in self.revisar_vol(filas) if n == "error"]
        self.assertTrue(any("no se pudo leer el audio de «Dañado»" in t for t in textos))
        self.assertTrue(any("«Mudo» casi no suena" in t for t in textos))
        self.assertTrue(any("«Cortado» dura solo 12 s" in t for t in textos))
        self.assertTrue(any("«Disco entero» dura 40 min" in t for t in textos))
        self.assertFalse(any("Sin medir" in t for t in textos))

    def test_mp3_de_poca_calidad(self):
        filas = self.tanda("A")
        filas[0]["ruta"] = filas[0]["ruta"].replace(".flac", ".mp3")
        open(filas[0]["ruta"], "wb").close()
        filas[0]["bitrate"] = 128
        avisos = revisar(agrupar_tandas(pd.DataFrame(filas)), carpeta=self.edmundo, minutos_sin_milonga=0)
        self.assertTrue(any("es un MP3 de 128 kbps" in a.texto for a in avisos))


if __name__ == "__main__":
    unittest.main()
