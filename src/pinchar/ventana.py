"""
La ventana de Pinchar (fase 0): la noche por tandas y los botones de siempre, grandes.

La música la pone el motor en su propio proceso (motor.py): esta ventana solo le manda órdenes y enseña lo que
le cuenta. Si la ventana se queda pillada, la música sigue.
"""
import os

from PyQt5.QtCore import Qt, QTimer, QSettings
from PyQt5.QtGui import QColor, QFont, QBrush
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QSlider, QDoubleSpinBox, QApplication,
)

from src.config.config import musicbee_start_folder
from src.diapos.generador import agrupar_tandas, leer_playlist
from src.pinchar.motor import Motor

COLUMNAS = ["Tanda", "Título", "Orquesta / cantor", "Año", "Dura"]
FONDOS = [QColor("#fbf6ec"), QColor("#eef3f7")]          # tandas alternas
CORTINA = QColor("#ececec")
SONANDO = QColor("#c8efc9")


def mmss(s):
    if s is None:
        return "–:––"
    s = max(0, int(round(s)))
    return f"{s // 60}:{s % 60:02d}"


class VentanaPinchar(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pinchar")
        self.settings = QSettings("TangoTags", "Pinchar")
        self.pistas = []                 # [{ruta, titulo, artista, ano, duracion, tanda, cortina}]
        self.situacion = None
        self.motor = Motor(silencio=float(self.settings.value("silencio", 2.0)),
                           fundido=float(self.settings.value("fundido", 3.0))).arrancar()

        central = QWidget()
        lay = QVBoxLayout(central)
        arriba = QHBoxLayout()
        cargar = QPushButton("Cargar la noche…")
        cargar.clicked.connect(self.elegir)
        self.nombre = QLabel("Ninguna playlist cargada")
        self.nombre.setStyleSheet("font-weight:bold")
        arriba.addWidget(cargar)
        arriba.addWidget(self.nombre, 1)
        arriba.addWidget(QLabel("Fundido (s):"))
        self.fundido = QDoubleSpinBox()
        self.fundido.setRange(0.5, 15)
        self.fundido.setSingleStep(0.5)
        self.fundido.setValue(float(self.settings.value("fundido", 3.0)))
        self.fundido.valueChanged.connect(self.cambiar_ajustes)
        arriba.addWidget(self.fundido)
        arriba.addWidget(QLabel("Silencio entre temas (s):"))
        self.silencio = QDoubleSpinBox()
        self.silencio.setRange(0, 10)
        self.silencio.setSingleStep(0.5)
        self.silencio.setValue(float(self.settings.value("silencio", 2.0)))
        self.silencio.valueChanged.connect(self.cambiar_ajustes)
        arriba.addWidget(self.silencio)
        lay.addLayout(arriba)

        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.verticalHeader().setVisible(False)
        cab = self.tabla.horizontalHeader()
        cab.setSectionResizeMode(QHeaderView.ResizeToContents)
        cab.setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.cellDoubleClicked.connect(self.tocar_fila)
        lay.addWidget(self.tabla, 1)

        # lo que suena
        self.que = QLabel("—")
        self.que.setStyleSheet("font-size:20px; font-weight:bold")
        self.estado = QLabel("")
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
        self.b_play = self.boton("▶ Empezar", "Empieza por el tema elegido (o el primero)", self.empezar)
        self.b_siguiente = self.boton("⏭ Fundido y siguiente", "Baja el volumen, silencio y el siguiente tema "
                                      "(el volumen vuelve solo)", lambda: self.motor.orden("fundido_siguiente"))
        self.b_pausa = self.boton("⏸ Fundido y pausa", "Baja el volumen y se queda en pausa (habla el "
                                  "organizador)", lambda: self.motor.orden("fundido_pausa"))
        self.b_seguir = self.boton("▶ Seguir", "Sigue donde se quedó subiendo el volumen",
                                   lambda: self.motor.orden("seguir"))
        for b in (self.b_play, self.b_siguiente, self.b_pausa, self.b_seguir):
            botones.addWidget(b)
        botones.addWidget(QLabel("Volumen"))
        self.volumen = QSlider(Qt.Horizontal)
        self.volumen.setRange(0, 100)
        self.volumen.setValue(int(self.settings.value("volumen", 100)))
        self.volumen.setFixedWidth(160)
        self.volumen.valueChanged.connect(self.cambiar_volumen)
        botones.addWidget(self.volumen)
        lay.addLayout(botones)
        self.setCentralWidget(central)

        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.actualizar)
        self.reloj.start(100)
        self.cambiar_volumen()
        ultima = self.settings.value("ultima_noche")
        if ultima and os.path.exists(ultima):
            QTimer.singleShot(0, lambda: self.cargar(ultima))

    def boton(self, texto, ayuda, accion):
        b = QPushButton(texto)
        b.setToolTip(ayuda)
        b.setMinimumHeight(64)
        b.setStyleSheet("QPushButton{font-size:18px; font-weight:bold; padding:0 18px;}")
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
        self.pistas = []
        numero = 0
        for t in agrupar_tandas(canciones):
            if not t.es_cortina:
                numero += 1
            for _, c in t.canciones.iterrows():
                self.pistas.append({"ruta": c["ruta"], "titulo": c["title"], "artista": c["artist"],
                                    "ano": c["ano"], "duracion": float(c["duration"] or 0),
                                    "tanda": None if t.es_cortina else numero, "cortina": t.es_cortina,
                                    "nombre_tanda": t.titulo_orquesta})
        self.motor.orden("cargar", [p["ruta"] for p in self.pistas], 0)
        self.settings.setValue("ultima_noche", ruta)
        self.nombre.setText(f"{os.path.basename(ruta)} — {numero} tandas, {len(self.pistas)} temas")
        self.pintar_tabla()
        if faltan:
            QMessageBox.warning(self, "Faltan canciones", f"{len(faltan)} canción(es) de la playlist no se "
                                f"encuentran y no sonarán:\n\n" + "\n".join(faltan[:15]))

    def pintar_tabla(self):
        self.tabla.setRowCount(len(self.pistas))
        for fila, p in enumerate(self.pistas):
            valores = ["Cortina" if p["cortina"] else str(p["tanda"]), p["titulo"], p["artista"], str(p["ano"] or ""),
                       mmss(p["duracion"])]
            for col, v in enumerate(valores):
                item = QTableWidgetItem(v)
                if p["cortina"]:
                    f = item.font()
                    f.setItalic(True)
                    item.setFont(f)
                self.tabla.setItem(fila, col, item)
        self.colorear(None)

    def colorear(self, actual):
        for fila, p in enumerate(self.pistas):
            fondo = SONANDO if fila == actual else CORTINA if p["cortina"] else FONDOS[(p["tanda"] or 0) % 2]
            for col in range(self.tabla.columnCount()):
                item = self.tabla.item(fila, col)
                if item:
                    item.setBackground(QBrush(fondo))
                    f = item.font()
                    f.setBold(fila == actual)
                    item.setFont(f)

    # ------------------------------------------------------------------ órdenes
    def empezar(self):
        fila = self.tabla.currentRow()
        self.motor.orden("ir" if self.sonando() else "play", fila if fila >= 0 else 0)
        self.tabla.clearSelection()                    # que se vea la fila verde de lo que suena

    def tocar_fila(self, fila, _col):
        if self.sonando() and QMessageBox.question(
                self, "Saltar", f"¿Dejar lo que suena y pasar ya a «{self.pistas[fila]['titulo']}»?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.motor.orden("ir" if self.sonando() else "play", fila)
        self.tabla.clearSelection()

    def mover(self):
        s = self.situacion
        if s and s.get("duracion"):
            self.motor.orden("buscar", s["duracion"] * self.posicion.value() / 1000)

    def cambiar_ajustes(self):
        self.settings.setValue("fundido", self.fundido.value())
        self.settings.setValue("silencio", self.silencio.value())
        self.motor.orden("ajustes", {"fundido": self.fundido.value(), "silencio": self.silencio.value()})

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
        anterior = (self.situacion or {}).get("indice")
        self.situacion = s
        i = s["indice"]
        p = self.pistas[i] if 0 <= i < len(self.pistas) else None
        if i != anterior:
            self.colorear(i)
            self.tabla.scrollToItem(self.tabla.item(i, 0), QAbstractItemView.PositionAtCenter)
        if p:
            donde = "Cortina" if p["cortina"] else f"Tanda {p['tanda']} · {p['nombre_tanda']}"
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
