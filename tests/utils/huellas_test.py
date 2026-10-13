import unittest

import numpy as np

from src.diapos import huellas

F = huellas.FRECUENCIA


def cancion_inventada(semilla, segundos=40):
    """Notas al azar (con armónicos) de duraciones al azar: cada semilla, una "canción" distinta."""
    rng = np.random.default_rng(semilla)
    partes = []
    while sum(map(len, partes)) < segundos * F:
        dur = int(rng.uniform(0.15, 0.6) * F)
        t = np.arange(dur) / F
        f0 = rng.uniform(150, 1200)
        nota = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in (1, 2, 3))
        partes.append((nota * np.hanning(dur)).astype(np.float32))
    return np.concatenate(partes)[:segundos * F]


class HuellasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canciones = {n: cancion_inventada(n) for n in range(8)}
        cls.indice = huellas.Indice()
        for n, m in cls.canciones.items():
            cls.indice.añadir(n, huellas.huella_de(m))

    def test_reconoce_la_cancion_y_el_segundo_con_ruido(self):
        rng = np.random.default_rng(99)
        for n in (2, 5, 7):
            ini = 12 * F
            trozo = self.canciones[n][ini:ini + 8 * F]
            trozo = trozo + rng.normal(0, np.std(trozo), len(trozo)).astype(np.float32)   # ruido tan fuerte como la música
            cancion, segundo, votos = self.indice.buscar(huellas.huella_de(trozo))
            self.assertEqual(cancion, n)
            self.assertAlmostEqual(segundo, 20, delta=0.5)          # el trozo acaba en el segundo 20
            self.assertGreater(votos, 3)

    def test_algo_que_no_esta_saca_pocos_votos(self):
        ajena = cancion_inventada(1234)[5 * F:13 * F]
        _, _, votos = self.indice.buscar(huellas.huella_de(ajena))
        _, _, votos_buena = self.indice.buscar(huellas.huella_de(self.canciones[3][5 * F:13 * F]))
        self.assertLess(votos * 5, votos_buena)

    def test_silencio(self):
        self.assertEqual(self.indice.buscar(huellas.huella_de(np.zeros(8 * F, dtype=np.float32))), (None, None, 0))


if __name__ == "__main__":
    unittest.main()
