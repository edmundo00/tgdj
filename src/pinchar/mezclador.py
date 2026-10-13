"""
El mezclador: qué suena en cada momento. Sin tarjeta de sonido (la pone motor.py), para poder probarlo entero.

Cada vez que la tarjeta pide sonido se llama a rellenar(n) y devuelve n muestras estéreo. Las órdenes (play,
fundidos, ir a otro tema…) solo cambian el estado; nunca leen disco ni esperan, para que el sonido no se corte.

- Entre tema y tema, `silencio` segundos sin sonido (en tango no se mezclan canciones).
- ⏭ fundido y siguiente: baja el volumen en `fundido` segundos, silencio y la siguiente a volumen normal.
- ⏸ fundido y pausa: baja y se queda en pausa en ese punto. ▶ seguir: vuelve a sonar subiendo el volumen.
  El volumen vuelve solo a su sitio: no hay ningún mando que se pueda quedar abajo.
- Si un tema no se puede leer, se salta (nunca silencio). Si aún no está preparado, silencio hasta que lo esté.
"""
import numpy as np

PARADO, SONANDO, PAUSADO, HUECO, FIN = "parado", "sonando", "pausado", "hueco", "fin"
ESCALA = 1 / 32768                  # int16 -> -1..1
FUNDIDO_SALTO = 0.25                # s: al saltar a otro tema mientras suena, un fundido cortito (sin chasquido)


class Mezclador:
    def __init__(self, frecuencia, audio, silencio=2.0, fundido=3.0):
        """audio(indice) -> array int16 (muestras, 2) si está preparado, None si aún no, False si no se puede leer."""
        self.f = frecuencia
        self.audio = audio
        self.silencio, self.fundido = silencio, fundido
        self.volumen = 1.0
        self.n = 0
        self._inicio(0)
        self.saltadas = []          # temas que no se pudieron leer (para avisar)
        self.esperando = False      # el tema que toca aún no estaba preparado

    def _inicio(self, indice):
        self.indice, self.pos, self.estado = indice, 0, PARADO
        self.ganancia, self.paso, self.despues = 1.0, 0.0, None
        self.objetivo = 1.0
        self.restante = 0           # muestras que le quedan al fundido en marcha (se cuentan: sin decimales)
        self.hueco = 0

    # ------------------------------------------------------------------ órdenes
    def cargar(self, n, indice=0):
        self.n = n
        self._inicio(max(0, min(indice, n - 1)))

    def play(self, indice=None):
        """Empezar (desde el tema `indice`, o el actual) a volumen normal."""
        if not self.n:
            return
        if indice is not None:
            self.indice, self.pos = max(0, min(indice, self.n - 1)), 0
        if self.estado == FIN:
            self.indice, self.pos = self.n - 1, 0
        self.estado, self.ganancia, self.paso, self.despues, self.restante = SONANDO, 1.0, 0.0, None, 0

    def fundido_siguiente(self, segundos=None):
        if self.estado == SONANDO:
            self._bajar(segundos, ("siguiente",))
        elif self.estado == PAUSADO:
            self._siguiente(hueco=False)
        elif self.estado == PARADO:
            self.play()

    def fundido_pausa(self, segundos=None):
        if self.estado == SONANDO:
            self._bajar(segundos, ("pausa",))
        elif self.estado == HUECO:              # en el silencio entre temas: el siguiente espera en pausa
            self.estado, self.ganancia, self.paso, self.hueco, self.restante = PAUSADO, 0.0, 0.0, 0, 0

    def seguir(self, segundos=None):
        """Vuelve a sonar subiendo el volumen (desde la pausa, o si se arrepiente a mitad de un fundido)."""
        if self.estado == PAUSADO or (self.estado == SONANDO and self.paso < 0):
            self.estado, self.despues = SONANDO, None
            self._rampa(segundos if segundos is not None else self.fundido, 1.0)
        elif self.estado == PARADO:
            self.play()

    def ir(self, indice):
        """Saltar a otro tema y que suene ya (con un fundido cortito si estaba sonando algo)."""
        indice = max(0, min(indice, self.n - 1))
        if self.estado == SONANDO and self.ganancia > 0:
            self._bajar(FUNDIDO_SALTO, ("ir", indice))
        else:
            self.indice, self.pos, self.hueco = indice, 0, 0
            self.estado, self.ganancia, self.paso, self.despues, self.restante = SONANDO, 1.0, 0.0, None, 0

    def buscar(self, segundos):
        a = self.audio(self.indice)
        if a is not None and a is not False:
            self.pos = int(max(0, min(len(a) - 1, segundos * self.f)))

    def parar(self):
        self._inicio(self.indice)

    # ------------------------------------------------------------------ internas
    def _rampa(self, segundos, objetivo):
        self.restante = max(1, round(max(0.05, segundos) * self.f))
        self.objetivo = objetivo
        self.paso = (objetivo - self.ganancia) / self.restante
        if self.paso == 0:
            self.paso = -1e-12 if objetivo == 0 else 1e-12

    def _bajar(self, segundos, despues):
        self.despues = despues
        self._rampa(self.fundido if segundos is None else segundos, 0.0)

    def _siguiente(self, hueco=True):
        self.indice += 1
        self.pos, self.ganancia, self.paso, self.despues, self.restante = 0, 1.0, 0.0, None, 0
        if self.indice >= self.n:
            self.indice, self.estado = self.n - 1, FIN
        elif hueco and self.silencio > 0:
            self.estado, self.hueco = HUECO, int(self.silencio * self.f)
        else:
            self.estado = SONANDO

    def _al_llegar_a_cero(self):
        despues, self.despues, self.paso, self.ganancia, self.restante = self.despues, None, 0.0, 0.0, 0
        if despues is None or despues[0] == "pausa":
            self.estado = PAUSADO
        elif despues[0] == "siguiente":
            self._siguiente(hueco=True)
        elif despues[0] == "ir":
            self.indice, self.pos, self.estado, self.ganancia = despues[1], 0, SONANDO, 1.0

    # ------------------------------------------------------------------ sonido
    def rellenar(self, frames):
        """frames muestras estéreo float32 de lo que suena ahora."""
        salida = np.zeros((frames, 2), dtype=np.float32)
        hecho = 0
        self.esperando = False
        for _ in range(100):                     # vueltas de seguridad: nunca un bucle infinito aquí
            if hecho >= frames or self.estado in (PARADO, PAUSADO, FIN):
                break
            if self.estado == HUECO:
                k = min(self.hueco, frames - hecho)
                hecho += k
                self.hueco -= k
                if self.hueco <= 0:
                    self.estado, self.pos = SONANDO, 0
                continue
            a = self.audio(self.indice)
            if a is None:                        # aún no está preparado: silencio hasta que lo esté
                self.esperando = True
                break
            if a is False:                       # no se puede leer: saltarlo, sin silencio
                self.saltadas.append(self.indice)
                self._siguiente(hueco=False)
                continue
            k = min(frames - hecho, len(a) - self.pos)
            if k <= 0:                           # se acabó el tema
                self._siguiente(hueco=True)
                continue
            if self.restante:
                # rampa de volumen: si acaba dentro de este trozo, el trozo se corta ahí
                k = min(k, self.restante)
                g = self.ganancia + self.paso * np.arange(1, k + 1, dtype=np.float64)
                self.restante -= k
                if not self.restante:
                    g[-1] = self.objetivo
                g = np.clip(g, 0, 1)
                curva = (g * g).astype(np.float32)[:, None]          # fundido más natural al oído
            else:
                g = None
                curva = np.float32(self.ganancia * self.ganancia)
            trozo = a[self.pos:self.pos + k].astype(np.float32)
            trozo *= np.float32(ESCALA * self.volumen)
            trozo *= curva
            salida[hecho:hecho + k] = trozo
            hecho += k
            self.pos += k
            if g is not None:
                self.ganancia = float(g[-1])
                if not self.restante:
                    if self.objetivo > 0:
                        self.paso = 0.0
                    else:
                        self._al_llegar_a_cero()
        return salida

    # ------------------------------------------------------------------ para la ventana
    def situacion(self):
        a = self.audio(self.indice) if self.n else None
        listo = a is not None and a is not False
        return {
            "estado": self.estado, "indice": self.indice, "segundo": self.pos / self.f,
            "duracion": len(a) / self.f if listo else None,
            "fundiendo": "bajando" if self.paso < 0 else "subiendo" if self.paso > 0 else None,
            "ganancia": self.ganancia, "hueco": self.hueco / self.f, "esperando": self.esperando,
            "saltadas": list(self.saltadas), "volumen": self.volumen,
        }
