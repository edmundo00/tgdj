"""Gráfico de la noche: una barra por tanda (altura = energía, color = género). Clic = ir a la tanda."""
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QColor, QPainter, QPen, QFont
from PyQt5.QtWidgets import QWidget, QToolTip

COLORES = {"tango": QColor("#5b7db1"), "vals": QColor("#5aa469"), "milonga": QColor("#e08a3c")}
SIN_DATO = QColor("#c8c8c8")
ENERGIA_MAXIMA = 6.0


class CurvaNoche(QWidget):
    tanda_clicada = pyqtSignal(int)          # fila de la tabla de tandas

    def __init__(self, parent=None):
        super().__init__(parent)
        self.barras = []                     # dicts: fila, numero, genero, energia, bpm, hora, titulo
        self.inicio_final = None             # índice de la primera tanda de la zona final (sin milonga)
        self.setMinimumHeight(120)
        self.setMouseTracking(True)

    def poner(self, barras, inicio_final=None):
        self.barras = barras
        self.inicio_final = inicio_final
        self.update()

    def _rectangulos(self):
        if not self.barras:
            return []
        margen_izq, margen_inf, margen_sup = 8, 30, 18
        ancho = (self.width() - 2 * margen_izq) / len(self.barras)
        alto_util = self.height() - margen_inf - margen_sup
        rects = []
        for n, b in enumerate(self.barras):
            energia = b["energia"] if b["energia"] is not None else 1.5
            alto = alto_util * min(energia, ENERGIA_MAXIMA) / ENERGIA_MAXIMA
            x = margen_izq + n * ancho
            rects.append(QRectF(x + ancho * 0.12, margen_sup + alto_util - alto, ancho * 0.76, alto))
        return rects

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        rects = self._rectangulos()
        if not rects:
            p.setPen(self.palette().mid().color())
            p.drawText(self.rect(), Qt.AlignCenter, "Carga una playlist para ver la curva de la noche")
            return
        base = self.height() - 30
        p.setPen(QPen(self.palette().mid().color(), 1))
        p.drawLine(4, int(base), self.width() - 4, int(base))
        if self.inicio_final is not None and self.inicio_final < len(rects):
            x = int(rects[self.inicio_final].left() - 3)
            p.setPen(QPen(QColor("#999999"), 1, Qt.DashLine))
            p.drawLine(x, 4, x, int(base))
            p.setFont(QFont("", 7))
            p.drawText(x + 3, 12, "final")
        p.setFont(QFont("", 7))
        x = self.width() - 150
        for nombre, color in COLORES.items():
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRect(x, 4, 8, 8)
            p.setPen(self.palette().text().color())
            p.drawText(x + 11, 12, nombre)
            x += 50
        for r, b in zip(rects, self.barras):
            color = COLORES.get(b["genero"], SIN_DATO) if b["energia"] is not None else SIN_DATO
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(r, 2, 2)
            p.setPen(self.palette().text().color())
            p.drawText(QRectF(r.left() - 4, base + 2, r.width() + 8, 12), Qt.AlignCenter, str(b["numero"]))
            if b["hora"] and (b["numero"] == 1 or b["numero"] % 3 == 1):
                p.setPen(self.palette().mid().color())
                p.drawText(QRectF(r.left() - 12, base + 14, r.width() + 24, 12), Qt.AlignCenter, b["hora"])

    def _barra_en(self, pos):
        for r, b in zip(self._rectangulos(), self.barras):
            if r.left() - 2 <= pos.x() <= r.right() + 2:
                return b
        return None

    def mouseMoveEvent(self, ev):
        b = self._barra_en(ev.pos())
        if b is None:
            QToolTip.hideText()
            return
        partes = [f"Tanda {b['numero']} ({b['hora']})" if b["hora"] else f"Tanda {b['numero']}", b["titulo"]]
        if b["energia"] is not None:
            partes.append(f"energía {b['energia']:.1f}")
        if b["bpm"]:
            partes.append(f"{b['bpm']:.0f} BPM")
        QToolTip.showText(ev.globalPos(), "\n".join(partes), self)

    def mousePressEvent(self, ev):
        b = self._barra_en(ev.pos())
        if b is not None:
            self.tanda_clicada.emit(b["fila"])
