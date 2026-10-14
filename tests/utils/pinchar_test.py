import os
import tempfile
import time
import unittest
import wave

import numpy as np

from src.pinchar.mezclador import Mezclador, SONANDO, PAUSADO, HUECO, FIN, PARADO
from src.pinchar.motor import Almacen, decodificar

F = 1000                     # frecuencia pequeña para que las cuentas sean fáciles


def tema(segundos, valor=10000):
    return np.full((int(segundos * F), 2), valor, dtype=np.int16)


class MezcladorTest(unittest.TestCase):
    def nuevo(self, temas, **kw):
        self.temas = temas
        m = Mezclador(F, lambda i: self.temas[i] if 0 <= i < len(self.temas) else None, **kw)
        m.cargar(len(temas))
        return m

    def segundos(self, m, s):
        return m.rellenar(int(s * F))

    def test_suena_entero_silencio_y_el_siguiente(self):
        m = self.nuevo([tema(1, 10000), tema(1, 20000)], silencio=0.5)
        m.play()
        a = self.segundos(m, 1)
        self.assertTrue(np.allclose(a, 10000 / 32768))
        b = self.segundos(m, 0.5)
        self.assertEqual(m.estado, HUECO if m.hueco else SONANDO)
        self.assertTrue(np.all(b == 0))                          # silencio entre temas
        c = self.segundos(m, 1)
        self.assertEqual(m.indice, 1)
        self.assertTrue(np.allclose(c, 20000 / 32768))
        self.segundos(m, 1)
        self.assertEqual(m.estado, FIN)
        self.assertTrue(np.all(self.segundos(m, 1) == 0))        # al acabar la noche, silencio (sin errores)

    def test_fundido_y_siguiente_vuelve_a_volumen_normal(self):
        m = self.nuevo([tema(10), tema(10, 20000)], silencio=1, fundido=2)
        m.play()
        self.segundos(m, 1)
        m.fundido_siguiente()
        bajada = self.segundos(m, 2)[:, 0]
        self.assertTrue(np.all(np.diff(bajada) <= 1e-9))         # baja sin subir nunca
        self.assertLess(bajada[-1], 0.001)
        self.assertEqual(m.estado, HUECO)
        self.assertTrue(np.all(self.segundos(m, 1) == 0))
        siguiente = self.segundos(m, 1)
        self.assertEqual(m.indice, 1)
        self.assertTrue(np.allclose(siguiente, 20000 / 32768))   # el volumen ha vuelto solo
        self.assertEqual(m.ganancia, 1.0)

    def test_fundido_pausa_y_seguir_donde_estaba(self):
        m = self.nuevo([tema(30)], fundido=2)
        m.play()
        self.segundos(m, 5)
        m.fundido_pausa()
        self.segundos(m, 2)
        self.assertEqual(m.estado, PAUSADO)
        donde = m.pos
        self.assertAlmostEqual(donde / F, 7, delta=0.01)
        self.assertTrue(np.all(self.segundos(m, 60) == 0))       # el organizador habla un minuto
        self.assertEqual(m.pos, donde)
        m.seguir()
        subida = self.segundos(m, 2)[:, 0]
        self.assertLess(subida[0], 0.001)
        self.assertTrue(np.all(np.diff(subida) >= -1e-9))
        self.assertAlmostEqual(float(subida[-1]), 10000 / 32768, places=3)
        self.assertEqual((m.ganancia, m.paso), (1.0, 0.0))

    def test_arrepentirse_a_mitad_de_fundido(self):
        m = self.nuevo([tema(30), tema(30)], fundido=2)
        m.play()
        m.fundido_siguiente()
        self.segundos(m, 1)
        m.seguir()
        self.segundos(m, 3)
        self.assertEqual((m.indice, m.estado, m.ganancia), (0, SONANDO, 1.0))

    def test_tema_que_no_se_lee_se_salta_sin_silencio(self):
        m = self.nuevo([tema(1), False, tema(1, 20000)], silencio=0)
        m.play()
        self.segundos(m, 1)
        b = self.segundos(m, 0.5)
        self.assertEqual(m.indice, 2)
        self.assertTrue(np.allclose(b, 20000 / 32768))
        self.assertEqual(m.saltadas, [1])

    def test_aun_no_preparado_espera_en_silencio(self):
        m = self.nuevo([None])
        m.play()
        self.assertTrue(np.all(self.segundos(m, 1) == 0))
        self.assertTrue(m.esperando)
        self.temas[0] = tema(1)
        self.assertTrue(np.allclose(self.segundos(m, 0.5), 10000 / 32768))

    def test_ir_a_otro_tema(self):
        m = self.nuevo([tema(10), tema(10), tema(10, 30000)])
        m.play()
        self.segundos(m, 1)
        m.ir(2)
        self.segundos(m, 0.3)                                    # fundido cortito
        self.assertEqual((m.indice, m.estado), (2, SONANDO))
        self.assertTrue(np.allclose(self.segundos(m, 0.5), 30000 / 32768))
        m.buscar(9.5)
        self.assertEqual(m.pos, 9500)

    def test_pausa_en_el_silencio_entre_temas(self):
        m = self.nuevo([tema(1), tema(5)], silencio=2)
        m.play()
        self.segundos(m, 1.5)
        m.fundido_pausa()
        self.assertEqual((m.estado, m.indice, m.pos), (PAUSADO, 1, 0))
        m.seguir()
        self.segundos(m, 4)
        self.assertEqual((m.estado, m.ganancia), (SONANDO, 1.0))

    def test_parado_no_suena(self):
        m = self.nuevo([tema(1)])
        self.assertEqual(m.estado, PARADO)
        self.assertTrue(np.all(self.segundos(m, 1) == 0))

    def test_trozos_pequenos_y_grandes_dan_lo_mismo(self):
        """El sonido no depende de cómo lo pida la tarjeta (trozos de 1 en 1 o de golpe)."""
        def todo(trozo):
            m = self.nuevo([tema(1.5, 8000), tema(1, 16000)], silencio=0.3, fundido=0.4)
            m.play()
            partes = []
            for k in range(0, 4000, trozo):
                if k == 700:
                    m.fundido_siguiente()
                partes.append(m.rellenar(trozo))
            return np.concatenate(partes)
        self.assertTrue(np.allclose(todo(100), todo(700 // 7)))
        self.assertTrue(np.allclose(todo(1), todo(100), atol=1e-6))


class LeerTest(unittest.TestCase):
    def wav(self, frecuencia=22050, segundos=1.0):
        ruta = os.path.join(tempfile.mkdtemp(), "t.wav")
        t = np.arange(int(frecuencia * segundos)) / frecuencia
        onda = (np.sin(2 * np.pi * 440 * t) * 12000).astype(np.int16)
        with wave.open(ruta, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(frecuencia)
            w.writeframes(onda.tobytes())
        return ruta

    def test_decodificar_a_otra_frecuencia_y_estereo(self):
        a = decodificar(self.wav(22050, 1.0), 48000)
        self.assertEqual(a.dtype, np.int16)
        self.assertEqual(a.shape[1], 2)
        self.assertAlmostEqual(len(a) / 48000, 1.0, delta=0.02)
        self.assertGreater(np.abs(a).max(), 8000)          # mono -> estéreo: -3 dB por canal

    def test_almacen_prepara_por_adelantado_y_marca_los_rotos(self):
        bueno = self.wav()
        roto = os.path.join(tempfile.mkdtemp(), "roto.flac")
        with open(roto, "wb") as f:
            f.write(b"esto no es audio")
        al = Almacen(8000)
        try:
            al.poner_rutas([bueno, roto, bueno, bueno, bueno])
            al.preparar(0)
            fin = time.time() + 10
            while time.time() < fin and not (0 in al.listos and 2 in al.listos and 1 in al.fallidos):
                time.sleep(0.05)
            self.assertIsNotNone(al.audio(0))
            self.assertIs(al.audio(1), False)
            self.assertIsNotNone(al.audio(2))
            self.assertIsNone(al.audio(4))                       # demasiado lejos: aún no
            al.preparar(2)
            fin = time.time() + 10
            while time.time() < fin and 4 not in al.listos:
                time.sleep(0.05)
            self.assertEqual(sorted(al.listos), [2, 3, 4])       # el 0 ya se ha soltado
        finally:
            al.cerrar()


if __name__ == "__main__":
    unittest.main()


class NocheTest(unittest.TestCase):
    def pistas(self):
        from src.pinchar import noche
        p = lambda d, tanda=None, cortina=False: {"duracion": d, "cortina": cortina, "tanda": tanda,
                                                  "orquesta": "O", "subtitulo": "", "genero": "tango"}
        return noche, [p(180, 1), p(180, 1), p(180, 1), p(240, cortina=True), p(150, 2), p(150, 2)]

    def test_bloques(self):
        noche, ps = self.pistas()
        self.assertEqual([(b["tipo"], b["indices"]) for b in noche.bloques(ps)],
                         [("tanda", [0, 1, 2]), ("cortina", [3]), ("tanda", [4, 5])])

    def test_horas_sonando_con_silencio_y_cortina_al_minuto(self):
        noche, ps = self.pistas()
        inicios, fin = noche.horas(ps, 1, 30, "sonando", 1000.0, silencio=2, empezadas={0: 700.0})
        self.assertEqual(inicios[0], 700.0)
        self.assertEqual(inicios[1], 1000.0 - 30)            # sin anotar: ahora - lo que lleva
        self.assertEqual(inicios[2], 1000 + 150 + 2)
        self.assertEqual(inicios[3], 1152 + 180 + 2)
        self.assertEqual(inicios[4], 1334 + 60 + 2)          # la cortina cuenta un minuto, no 4
        self.assertEqual(fin, 1396 + 150 + 2 + 150)

    def test_horas_parado_empieza_a_la_hora_de_la_milonga(self):
        noche, ps = self.pistas()
        inicios, _ = noche.horas(ps, 0, 0, "parado", 1000.0, silencio=0, inicio_previsto=5000.0)
        self.assertEqual(inicios[0], 5000.0)
        inicios, _ = noche.horas(ps, 0, 0, "parado", 1000.0, silencio=0, inicio_previsto=500.0)
        self.assertEqual(inicios[0], 1000.0)                 # ya pasó la hora: desde ahora

    def test_horas_en_el_silencio_y_al_final(self):
        noche, ps = self.pistas()
        inicios, _ = noche.horas(ps, 4, 0, "hueco", 1000.0, silencio=2, hueco=1.5)
        self.assertEqual(inicios[4], 1001.5)
        _, fin = noche.horas(ps, 5, 150, "fin", 3000.0, silencio=2)
        self.assertEqual(fin, 3000.0)
