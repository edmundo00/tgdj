"""
La ventana de Pinchar: a la izquierda la noche (la tanda que suena, la cortina y la siguiente, con sus horas, y
los botones de siempre, grandes); a la derecha las herramientas en pestañas (base de datos, especiales, reserva,
horario) y la preescucha arriba.

La música la pone el motor en su propio proceso (motor.py): esta ventana solo le manda órdenes y enseña lo que
le cuenta. Si la ventana se queda pillada, la música sigue.
"""
import datetime as dt
import os
import time

from PyQt5.QtCore import Qt, QTimer, QSettings, QTime
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QSlider, QDoubleSpinBox, QApplication, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTimeEdit, QFrame,
)

from src.config.config import musicbee_start_folder
from src.diapos.generador import agrupar_tandas, leer_playlist
from src.pinchar import noche
from src.pinchar.motor import Motor

GENEROS = {"tango": "Tango", "vals": "Vals", "milonga": "Milonga", "cortina": "Cortina"}
FONDO = {"tango": QColor("#f6e7c8"), "vals": QColor("#d6efdc"), "milonga": QColor("#f9dccb"),
         "cortina": QColor("#efe1ff")}                  # la cortina, de color moderno
SONANDO = QColor("#b9ecbb")
SONADA = QColor("#8a8a8a")
INDICE = Qt.UserRole                                    # en cada fila del árbol: el índice de la pista


def mmss(s):
    if s is None:
        return "–:––"
    s = max(0, int(round(s)))
    return f"{s // 60}:{s % 60:02d}"


def hhmm(t):
    return "" if t is None else time.strftime("%H:%M", time.localtime(t))


def cercana(hora, referencia):
    """La fecha con esa hora (QTime) más cercana a `referencia` (time.time()): la milonga de 21:00 a 00:00
    acaba «mañana» a las 00:00 aunque se mire a las 23:00."""
    base = dt.datetime.fromtimestamp(referencia)
    candidatas = [dt.datetime.combine(base.date() + dt.timedelta(days=d), dt.time(hora.hour(), hora.minute()))
                  for d in (-1, 0, 1)]
    return min((c.timestamp() for c in candidatas), key=lambda c: abs(c - referencia))


class VentanaPinchar(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pinchar")
        self.settings = QSettings("TangoTags", "Pinchar")
        self.pistas, self.bloques = [], []
        self.situacion = None
        self.empezadas = {}              # índice -> hora a la que empezó a sonar de verdad
        self.inicios, self.fin = [], None
        self.ultimo_repintado = 0.0
        self.motor = Motor(silencio=float(self.settings.value("silencio", 2.0)),
                           fundido=float(self.settings.value("fundido", 3.0))).arrancar()

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addLayout(self._barra_de_arriba())
        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._izquierda())
        division.addWidget(self._derecha())
        division.setStretchFactor(0, 11)
        division.setStretchFactor(1, 9)
        division.setChildrenCollapsible(False)
        lay.addWidget(division, 1)
        self.setCentralWidget(central)

        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.actualizar)
        self.reloj.start(100)
        self.cambiar_volumen()
        ultima = self.settings.value("ultima_noche")
        if ultima and os.path.exists(ultima):
            QTimer.singleShot(0, lambda: self.cargar(ultima))

    # ------------------------------------------------------------------ montar la ventana
    def _barra_de_arriba(self):
        arriba = QHBoxLayout()
        cargar = QPushButton("Cargar la noche…")
        cargar.clicked.connect(self.elegir)
        self.nombre = QLabel("Ninguna playlist cargada")
        self.nombre.setStyleSheet("font-weight:bold")
        arriba.addWidget(cargar)
        arriba.addWidget(self.nombre, 1)
        arriba.addWidget(QLabel("Milonga de"))
        self.hora_inicio = QTimeEdit(QTime.fromString(self.settings.value("hora_inicio", "21:00"), "HH:mm"))
        arriba.addWidget(self.hora_inicio)
        arriba.addWidget(QLabel("a"))
        self.hora_fin = QTimeEdit(QTime.fromString(self.settings.value("hora_fin", "00:00"), "HH:mm"))
        arriba.addWidget(self.hora_fin)
        for t in (self.hora_inicio, self.hora_fin):
            t.setDisplayFormat("HH:mm")
            t.timeChanged.connect(self.cambiar_horario)
        arriba.addSpacing(16)
        arriba.addWidget(QLabel("Fundido (s):"))
        self.fundido = self._numero(0.5, 15, "fundido", 3.0)
        arriba.addWidget(self.fundido)
        arriba.addWidget(QLabel("Silencio entre temas (s):"))
        self.silencio = self._numero(0, 10, "silencio", 2.0)
        arriba.addWidget(self.silencio)
        return arriba

    def _numero(self, minimo, maximo, clave, defecto):
        n = QDoubleSpinBox()
        n.setRange(minimo, maximo)
        n.setSingleStep(0.5)
        n.setValue(float(self.settings.value(clave, defecto)))
        n.valueChanged.connect(self.cambiar_ajustes)
        return n

    def _izquierda(self):
        caja = QWidget()
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 4, 0)
        self.b_anteriores = QPushButton("▲ Tandas anteriores")
        self.b_anteriores.setCheckable(True)
        self.b_anteriores.toggled.connect(lambda: self.pintar_noche(forzar=True))
        lay.addWidget(self.b_anteriores)
        self.arbol = QTreeWidget()
        self.arbol.setColumnCount(3)
        self.arbol.setHeaderLabels(["La noche", "Hora", "Dura"])
        self.arbol.setRootIsDecorated(False)
        self.arbol.setIndentation(18)
        self.arbol.setUniformRowHeights(True)
        self.arbol.setStyleSheet("QTreeWidget{font-size:15px;} QTreeWidget::item{padding:3px 0;}")
        cab = self.arbol.header()
        cab.setStretchLastSection(False)
        cab.setSectionResizeMode(0, QHeaderView.Stretch)
        cab.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        cab.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.arbol.itemDoubleClicked.connect(self.tocar_item)
        lay.addWidget(self.arbol, 1)
        self.b_siguientes = QPushButton("▼ Tandas siguientes")
        self.b_siguientes.setCheckable(True)
        self.b_siguientes.toggled.connect(lambda: self.pintar_noche(forzar=True))
        lay.addWidget(self.b_siguientes)
        self.final = QLabel("")
        self.final.setStyleSheet("font-size:14px; padding:4px 2px")
        lay.addWidget(self.final)

        linea = QFrame()
        linea.setFrameShape(QFrame.HLine)
        lay.addWidget(linea)
        self.que = QLabel("—")
        self.que.setWordWrap(True)
        self.que.setStyleSheet("font-size:20px; font-weight:bold")
        self.estado = QLabel("")
        self.estado.setWordWrap(True)
        self.estado.setStyleSheet("font-size:14px; color:#555")
        lay.addWidget(self.que)
        lay.addWidget(self.estado)
        barra = QHBoxLayout()
        self.lleva = QLabel("0:00")
        self.posicion = QSlider(Qt.Horizontal)
        self.posicion.setRange(0, 1000)
        self.posicion.sliderReleased.connect(self.mover)
        self.queda = QLabel("−0:00")
        for w in (self.lleva, self.queda):
            w.setStyleSheet("font-size:16px; font-family:Consolas, monospace")
        barra.addWidget(self.lleva)
        barra.addWidget(self.posicion, 1)
        barra.addWidget(self.queda)
        lay.addLayout(barra)

        botones = QHBoxLayout()
        self.b_siguiente = self.boton("⏭ Fundido y\nsiguiente", "Baja el volumen, silencio y el siguiente tema "
                                      "(el volumen vuelve solo)", lambda: self.motor.orden("fundido_siguiente"))
        self.b_pausa = self.boton("⏸ Fundido y\npausa", "Baja el volumen y se queda en pausa (habla el "
                                  "organizador)", lambda: self.motor.orden("fundido_pausa"))
        self.b_seguir = self.boton("▶ Seguir", "Sigue donde se quedó subiendo el volumen",
                                   lambda: self.motor.orden("seguir"))
        for b in (self.b_siguiente, self.b_pausa, self.b_seguir):
            botones.addWidget(b)
        lay.addLayout(botones)
        abajo = QHBoxLayout()
        self.b_play = QPushButton("▶ Empezar")
        self.b_play.setToolTip("Empieza por el tema elegido en la lista (o el primero)")
        self.b_play.setMinimumHeight(36)
        self.b_play.clicked.connect(self.empezar)
        abajo.addWidget(self.b_play)
        abajo.addStretch(1)
        abajo.addWidget(QLabel("Volumen"))
        self.volumen = QSlider(Qt.Horizontal)
        self.volumen.setRange(0, 100)
        self.volumen.setValue(int(self.settings.value("volumen", 100)))
        self.volumen.setFixedWidth(180)
        self.volumen.valueChanged.connect(self.cambiar_volumen)
        abajo.addWidget(self.volumen)
        lay.addLayout(abajo)
        return caja

    def _derecha(self):
        caja = QWidget()
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(4, 0, 0, 0)
        self.preescucha = QLabel("🎧 Preescucha · llega en la fase 2. Sonará solo por la tarjeta de los "
                                 "auriculares, nunca por la sala.")
        self.preescucha.setWordWrap(True)
        self.preescucha.setStyleSheet("background:#eef3f7; border:1px solid #c9d6e2; border-radius:8px; "
                                      "padding:10px; font-size:14px; color:#456")
        lay.addWidget(self.preescucha)
        self.pestanas = QTabWidget()
        self.pestanas.setStyleSheet("QTabBar::tab{font-size:15px; padding:8px 14px; min-width:130px;}")
        self.pestanas.tabBar().setElideMode(Qt.ElideNone)      # que no corte los nombres
        self.pestanas.tabBar().setExpanding(False)
        proximamente = {
            "🔎 Base de datos": "Buscar en toda tu música (orquesta, título, cantor, año, género, solo 5★), "
                               "preescuchar con 🎧 y meter en la noche con ➕.\n\nLlega en la fase 2.",
            "🎂 Especiales": "Valses de cumpleaños, La Cumparsita, efectos de sonido y tandas de emergencia, "
                            "a mano para meterlos con un toque.\n\nLlega en la fase 2.",
            "📋 Reserva": "Las tandas de reserva que calcula TangoTags para esta noche.\n\nLlega en la fase 2.",
        }
        for nombre, texto in proximamente.items():
            l = QLabel(texto)
            l.setWordWrap(True)
            l.setAlignment(Qt.AlignCenter)
            l.setStyleSheet("font-size:15px; color:#777; padding:30px")
            self.pestanas.addTab(l, nombre)
        self.pestanas.addTab(self._horario(), "⏱ Horario")
        self.pestanas.setCurrentIndex(3)
        lay.addWidget(self.pestanas, 1)
        return caja

    def _horario(self):
        caja = QWidget()
        lay = QVBoxLayout(caja)
        self.resumen = QLabel("")
        self.resumen.setWordWrap(True)
        self.resumen.setStyleSheet("font-size:15px; padding:4px")
        lay.addWidget(self.resumen)
        self.tabla_horario = QTableWidget(0, 4)
        self.tabla_horario.setHorizontalHeaderLabels(["Tanda", "", "Empieza", "Acaba"])
        self.tabla_horario.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_horario.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla_horario.verticalHeader().setVisible(False)
        cab = self.tabla_horario.horizontalHeader()
        cab.setSectionResizeMode(QHeaderView.ResizeToContents)
        cab.setSectionResizeMode(0, QHeaderView.Stretch)
        lay.addWidget(self.tabla_horario, 1)
        return caja

    def boton(self, texto, ayuda, accion):
        b = QPushButton(texto)
        b.setToolTip(ayuda)
        b.setMinimumHeight(72)
        b.setStyleSheet("QPushButton{font-size:18px; font-weight:bold; padding:0 14px;}")
        b.clicked.connect(accion)
        return b

    # ------------------------------------------------------------------ cargar
    def elegir(self):
        carpeta = self.settings.value("dir_noches") or os.path.join(musicbee_start_folder, "tango", "Playlists")
        ruta, _ = QFileDialog.getOpenFileName(self, "Cargar la noche", carpeta,
                                              "Playlists (*.mbp *.m3u *.m3u8);;Todos (*.*)")
        if ruta:
            if self.sonando() and QMessageBox.question(
                    self, "Cargar otra noche", "Está sonando música: si cargas otra noche, se para. ¿Seguir?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            self.settings.setValue("dir_noches", os.path.dirname(ruta))
            self.cargar(ruta)

    def cargar(self, ruta):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            canciones, faltan = leer_playlist(ruta)
        finally:
            QApplication.restoreOverrideCursor()
        self.pistas = noche.pistas_de(agrupar_tandas(canciones))
        self.bloques = noche.bloques(self.pistas)
        self.empezadas = {}
        self.situacion = None
        self.motor.orden("cargar", [p["ruta"] for p in self.pistas], 0)
        self.settings.setValue("ultima_noche", ruta)
        tandas = sum(b["tipo"] == "tanda" for b in self.bloques)
        self.nombre.setText(f"{os.path.basename(ruta)} — {tandas} tandas, {len(self.pistas)} temas")
        self.montar_arbol()
        self.montar_horario()
        self.pintar_noche(forzar=True)
        if faltan:
            QMessageBox.warning(self, "Faltan canciones", f"{len(faltan)} canción(es) de la playlist no se "
                                f"encuentran y no sonarán:\n\n" + "\n".join(faltan[:15]))

    def montar_arbol(self):
        self.arbol.clear()
        self.items = [None] * len(self.pistas)           # índice de pista -> fila del árbol
        self.cabeceras = []                              # por bloque
        for b in self.bloques:
            if b["tipo"] == "cortina":
                i = b["indices"][0]
                it = QTreeWidgetItem(self.arbol)
                it.setData(0, INDICE, i)
                self.items[i] = it
            else:
                it = QTreeWidgetItem(self.arbol)
                it.setData(0, INDICE, b["indices"][0])
                f = it.font(0)
                f.setBold(True)
                it.setFont(0, f)
                for i in b["indices"]:
                    hijo = QTreeWidgetItem(it)
                    hijo.setData(0, INDICE, i)
                    self.items[i] = hijo
            for col in range(3):
                it.setBackground(col, QBrush(FONDO.get(b["genero"], FONDO["tango"])))
            self.cabeceras.append(it)

    def montar_horario(self):
        tandas = [b for b in self.bloques if b["tipo"] == "tanda"]
        self.tabla_horario.setRowCount(len(tandas))
        for fila, b in enumerate(tandas):
            for col, v in enumerate([f"{b['numero']}. {b['orquesta']}", GENEROS[b["genero"]], "", ""]):
                item = QTableWidgetItem(v)
                if col == 1:
                    item.setBackground(QBrush(FONDO[b["genero"]]))
                self.tabla_horario.setItem(fila, col, item)

    # ------------------------------------------------------------------ pintar la noche
    def bloque_de(self, i):
        for k, b in enumerate(self.bloques):
            if i in b["indices"]:
                return k
        return 0

    def pintar_noche(self, forzar=False):
        """Horas, qué se ve (la tanda que suena, la cortina y la siguiente) y colores."""
        if not self.pistas:
            return
        s = self.situacion or {"indice": 0, "estado": "parado", "segundo": 0.0, "hueco": 0.0}
        ahora = time.time()
        if not forzar and ahora - self.ultimo_repintado < 1:
            return
        self.ultimo_repintado = ahora
        indice, estado = s["indice"], s["estado"]
        inicio_previsto = cercana(self.hora_inicio.time(), ahora)
        self.inicios, self.fin = noche.horas(self.pistas, indice, s["segundo"], estado, ahora,
                                             self.silencio.value(), empezadas=self.empezadas,
                                             hueco=s.get("hueco", 0.0), inicio_previsto=inicio_previsto)
        actual = self.bloque_de(indice)
        # se ve: la tanda que suena (o la que acaba de sonar, si suena la cortina), la cortina y la siguiente
        desde = actual - 1 if self.bloques[actual]["tipo"] == "cortina" and actual > 0 else actual
        hasta = next((k for k in range(actual + 1, len(self.bloques)) if self.bloques[k]["tipo"] == "tanda"),
                     len(self.bloques) - 1)
        if self.b_anteriores.isChecked():
            desde = 0
        if self.b_siguientes.isChecked():
            hasta = len(self.bloques) - 1
        antes = sum(b["tipo"] == "tanda" for b in self.bloques[:desde])
        despues = sum(b["tipo"] == "tanda" for b in self.bloques[hasta + 1:])
        self.b_anteriores.setText(("▼ Ocultar las anteriores" if self.b_anteriores.isChecked()
                                   else f"▲ Tandas anteriores ({antes})"))
        self.b_anteriores.setEnabled(antes > 0 or self.b_anteriores.isChecked())
        self.b_siguientes.setText(("▲ Ocultar las siguientes" if self.b_siguientes.isChecked()
                                   else f"▼ Tandas siguientes ({despues})"))
        self.b_siguientes.setEnabled(despues > 0 or self.b_siguientes.isChecked())

        en_marcha = estado in ("sonando", "pausado", "fin")
        for k, b in enumerate(self.bloques):
            cab = self.cabeceras[k]
            cab.setHidden(not desde <= k <= hasta)
            idx = b["indices"]
            ini = next((self.inicios[i] for i in idx if self.inicios[i] is not None), None)
            fin_b = (self.inicios[idx[-1]] or 0) + noche.duracion_prevista(self.pistas[idx[-1]]) \
                if self.inicios[idx[-1]] is not None else None
            if b["tipo"] == "cortina":
                p = self.pistas[idx[0]]
                cab.setText(0, f"     Cortina · {p['titulo']}" + (f" — {p['artista']}" if p["artista"] else ""))
                cab.setText(1, hhmm(ini))
                cab.setText(2, mmss(p["duracion"]))
                self._marcar(cab, idx[0], indice, en_marcha)
                continue
            cab.setText(0, f"{b['numero']} · {b['orquesta']} — {b['subtitulo']}")
            cab.setText(1, f"{hhmm(ini)}–{hhmm(fin_b)}" if ini and fin_b else hhmm(ini))
            cab.setText(2, mmss(sum(self.pistas[i]["duracion"] for i in idx)))
            # abierta la tanda que suena (o la que acaba de sonar) y la siguiente
            cab.setExpanded(k in (actual, desde, hasta) or self.b_anteriores.isChecked() and k < actual
                            or self.b_siguientes.isChecked() and k > actual)
            for i in idx:
                p, hijo = self.pistas[i], self.items[i]
                marca = "✓ " if (i < indice or i == indice and estado == "fin") else "♪ " \
                    if i == indice and en_marcha else "    "
                hijo.setText(0, f"{marca}{p['titulo']}" + (f"   ({p['ano']})" if p["ano"] else ""))
                hijo.setText(1, hhmm(self.inicios[i]))
                hijo.setText(2, mmss(p["duracion"]))
                self._marcar(hijo, i, indice, en_marcha)
        self.pintar_final()
        self.pintar_horario(indice, estado)

    def _marcar(self, item, i, indice, en_marcha):
        """Verde lo que suena; gris lo que ya sonó."""
        suena = i == indice and en_marcha
        for col in range(3):
            if suena:
                item.setBackground(col, QBrush(SONANDO))
            elif item.parent() is not None:
                item.setBackground(col, QBrush(Qt.transparent))
            elif item.data(0, INDICE) is not None and self.pistas[i]["cortina"]:
                item.setBackground(col, QBrush(FONDO["cortina"]))
            item.setForeground(col, QBrush(SONADA if i < indice else QColor("#000")))
        f = item.font(0)
        f.setBold(suena or item.parent() is None and not self.pistas[i]["cortina"])
        item.setFont(0, f)

    def pintar_final(self):
        if self.fin is None:
            return
        fin_milonga = cercana(self.hora_fin.time(), self.fin)
        diferencia = (self.fin - fin_milonga) / 60
        if abs(diferencia) < 2:
            como = "justo a tiempo 👌"
            color = "#2e7d32"
        elif diferencia > 0:
            como = f"⚠ {diferencia:.0f} min más tarde que el final de la milonga ({hhmm(fin_milonga)}): " \
                   f"quizá sobre una tanda"
            color = "#c62828"
        else:
            como = f"faltan {-diferencia:.0f} min de música hasta las {hhmm(fin_milonga)}"
            color = "#ef6c00"
        self.final.setText(f"<b>La música acabará a las {hhmm(self.fin)}</b> · "
                           f"<span style='color:{color}'>{como}</span>")
        self.resumen.setText(self.final.text())

    def pintar_horario(self, indice, estado):
        fila = 0
        for b in self.bloques:
            if b["tipo"] != "tanda":
                continue
            idx = b["indices"]
            ini = next((self.inicios[i] for i in idx if self.inicios[i] is not None), None)
            ult = self.inicios[idx[-1]]
            fin_b = ult + self.pistas[idx[-1]]["duracion"] if ult is not None else None
            sonada = idx[-1] < indice or estado == "fin"
            suena = idx[0] <= indice <= idx[-1] and estado in ("sonando", "pausado", "hueco")
            for col, v in ((2, hhmm(ini)), (3, hhmm(fin_b))):
                self.tabla_horario.item(fila, col).setText(v)
            for col in range(4):
                it = self.tabla_horario.item(fila, col)
                it.setForeground(QBrush(SONADA if sonada else QColor("#000")))
                if col != 1:
                    it.setBackground(QBrush(SONANDO if suena else Qt.transparent))
            fila += 1

    # ------------------------------------------------------------------ órdenes
    def elegido(self):
        it = self.arbol.currentItem()
        return it.data(0, INDICE) if it is not None and it.data(0, INDICE) is not None else None

    def empezar(self):
        i = self.elegido()
        self.motor.orden("ir" if self.sonando() else "play", 0 if i is None else i)
        self.arbol.clearSelection()

    def tocar_item(self, item, _col):
        i = item.data(0, INDICE)
        if i is None:
            return
        if self.sonando() and QMessageBox.question(
                self, "Saltar", f"¿Dejar lo que suena y pasar ya a «{self.pistas[i]['titulo']}»?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.motor.orden("ir" if self.sonando() else "play", i)
        self.arbol.clearSelection()

    def mover(self):
        s = self.situacion
        if s and s.get("duracion"):
            self.motor.orden("buscar", s["duracion"] * self.posicion.value() / 1000)

    def cambiar_ajustes(self):
        self.settings.setValue("fundido", self.fundido.value())
        self.settings.setValue("silencio", self.silencio.value())
        self.motor.orden("ajustes", {"fundido": self.fundido.value(), "silencio": self.silencio.value()})
        self.pintar_noche(forzar=True)

    def cambiar_horario(self):
        self.settings.setValue("hora_inicio", self.hora_inicio.time().toString("HH:mm"))
        self.settings.setValue("hora_fin", self.hora_fin.time().toString("HH:mm"))
        self.pintar_noche(forzar=True)

    def cambiar_volumen(self):
        self.settings.setValue("volumen", self.volumen.value())
        self.motor.orden("ajustes", {"volumen": self.volumen.value() / 100})

    def sonando(self):
        s = self.situacion
        return bool(s) and s.get("estado") in ("sonando", "hueco", "pausado")

    # ------------------------------------------------------------------ lo que cuenta el motor
    def actualizar(self):
        s = self.motor.situacion()
        if s and s.get("error"):
            self.reloj.stop()
            QMessageBox.critical(self, "Sonido", "No se pudo abrir la tarjeta de sonido:\n\n" + s["error"][-800:])
            return
        if not self.motor.vivo() and self.situacion is not None:
            self.estado.setText("⚠ El motor de sonido se ha parado")
        if not s or not self.pistas:
            return
        antes = self.situacion or {}
        self.situacion = s
        i = s["indice"]
        if s["estado"] == "sonando" and i not in self.empezadas:
            self.empezadas[i] = time.time() - s["segundo"]
        cambio = (i, s["estado"]) != (antes.get("indice"), antes.get("estado"))
        self.pintar_noche(forzar=cambio)
        if cambio and 0 <= i < len(self.items) and self.items[i] is not None:
            self.arbol.scrollToItem(self.items[i])
        p = self.pistas[i] if 0 <= i < len(self.pistas) else None
        if p:
            donde = "Cortina" if p["cortina"] else f"Tanda {p['tanda']} · {p['orquesta']}"
            self.que.setText(f"{p['titulo']} — {p['artista']}   ·   {donde}")
        textos = {"parado": "Parado", "sonando": "Sonando", "pausado": "⏸ En pausa: ▶ Seguir para continuar",
                  "hueco": f"Silencio antes del siguiente tema ({s['hueco']:.0f} s)", "fin": "Fin de la noche"}
        texto = textos.get(s["estado"], s["estado"])
        if s["fundiendo"] == "bajando":
            texto = "Bajando el volumen…"
        elif s["fundiendo"] == "subiendo":
            texto = "Subiendo el volumen…"
        if s.get("esperando"):
            texto += " · preparando el tema…"
        if s.get("fallidos"):
            malos = [self.pistas[int(k)]["titulo"] for k in s["fallidos"] if int(k) < len(self.pistas)]
            texto += f" · ⚠ no se pudo leer (se salta): {', '.join(malos)}"
        if s.get("cortes"):
            texto += f" · {s['cortes']} microcorte(s) de sonido"
        self.estado.setText(f"{texto}   ·   salida: {s.get('dispositivo', '')}")
        dur = s.get("duracion")
        self.lleva.setText(mmss(s["segundo"]))
        self.queda.setText("−" + mmss(dur - s["segundo"]) if dur else "−–:––")
        if dur and not self.posicion.isSliderDown():
            self.posicion.setValue(int(1000 * s["segundo"] / dur))
        estado = s["estado"]
        self.b_seguir.setEnabled(estado == "pausado" or s["fundiendo"] == "bajando")
        self.b_pausa.setEnabled(estado in ("sonando", "hueco") and s["fundiendo"] != "bajando")
        self.b_siguiente.setEnabled(estado in ("sonando", "pausado") and s["fundiendo"] != "bajando")
        self.b_play.setText("▶ Ir al elegido" if self.sonando() else "▶ Empezar")

    def closeEvent(self, evento):
        if self.sonando() and QMessageBox.question(
                self, "Salir", "Está sonando música. ¿Parar la música y cerrar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            evento.ignore()
            return
        self.motor.parar()
        evento.accept()
