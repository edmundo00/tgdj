import os
import tempfile
import unittest
import wave

import numpy as np

from src.diapos import bpm


def metronomo(pulsos_por_minuto, segundos=30, frecuencia=bpm.FRECUENCIA, acento_cada=0):
    """Clics cortos (con ruido) a un BPM exacto; acento_cada=2 hace un clic fuerte cada dos."""
    rng = np.random.default_rng(0)
    muestras = rng.normal(0, 0.01, int(segundos * frecuencia)).astype(np.float32)
    clic = (np.sin(2 * np.pi * 1500 * np.arange(200) / frecuencia) * np.exp(-np.arange(200) / 40)).astype(np.float32)
    periodo = frecuencia * 60 / pulsos_por_minuto
    for n, inicio in enumerate(np.arange(0, len(muestras) - 200, periodo)):
        fuerza = 1.0 if not acento_cada or n % acento_cada == 0 else 0.4
        muestras[int(inicio):int(inicio) + 200] += fuerza * clic
    return muestras


class PulsoTest(unittest.TestCase):
    def test_encuentra_el_bpm_de_un_metronomo(self):
        for valor, genero in ((96, "tango"), (120, "tango"), (128, "tango"), (205, "vals"), (100, "milonga")):
            bajo, alto = bpm.RANGOS[genero]
            calculado = bpm.pulso(metronomo(valor), minimo=bajo, maximo=alto - 0.25)
            self.assertAlmostEqual(calculado, valor, delta=2, msg=valor)

    def test_dentro_del_rango_del_genero_no_sale_a_la_mitad(self):
        # mismo metrónomo: como tango (85-170) sale 120, como vals (150-300) sale 240
        muestras = metronomo(120, acento_cada=2)
        self.assertAlmostEqual(bpm.pulso(muestras, minimo=85, maximo=169.75), 120, delta=2)
        self.assertAlmostEqual(bpm.pulso(muestras, minimo=150, maximo=299.75), 240, delta=4)

    def test_silencio_no_da_pulso(self):
        self.assertIsNone(bpm.pulso(np.zeros(bpm.FRECUENCIA * 30, dtype=np.float32)))


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.wav = os.path.join(self.dir, "Dropbox", "TDJ", "MUSICA", "Edmundo", "metronomo.wav")
        os.makedirs(os.path.dirname(self.wav))
        datos = (metronomo(126, segundos=40) * 20000).astype(np.int16)
        with wave.open(self.wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(bpm.FRECUENCIA)
            w.writeframes(datos.tobytes())

    def test_calcula_una_vez_y_luego_lo_lee(self):
        cache = bpm.CacheBpm(os.path.join(self.dir, "bpm.sqlite"))
        self.assertEqual(cache.guardado(self.wav, "tango"), (False, None))
        self.assertAlmostEqual(cache.bpm(self.wav, "tango"), 126, delta=2)
        encontrado, valor = cache.guardado(self.wav, "tango")
        self.assertTrue(encontrado)
        self.assertAlmostEqual(valor, 126, delta=2)
        self.assertEqual(cache.guardado(self.wav, "tango vals")[0], False)   # cada género por separado

    def test_la_clave_vale_en_otro_ordenador(self):
        clave, _ = bpm._clave(r"D:\Dropbox\TDJ\MUSICA\Edmundo\x.flac")
        self.assertEqual(clave, bpm._clave(r"C:\Dropbox\TDJ\MUSICA\Edmundo\x.flac")[0])


if __name__ == "__main__":
    unittest.main()
