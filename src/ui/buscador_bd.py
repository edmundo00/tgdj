"""
Ventana "Buscar en la base de datos".

Una sola caja de búsqueda (busca mientras escribes), filtros de un clic, resultados agrupados
por grabación con su fuente, coincidencias resaltadas y un panel con la ficha completa.
No es modal: se puede dejar abierta mientras se trabaja en la ventana principal; sigue a la
canción seleccionada allí y "Usar para esta canción" le asigna la grabación elegida.
"""
import html
import re

import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, QSettings, QSize, QRectF
from PyQt5.QtGui import QColor, QFont, QTextDocument, QPalette, QKeySequence
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QTableView, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QStyle, QSpinBox, QFrame, QSplitter, QApplication, QShortcut,
    QStyleOptionViewItem, QDialog, QFormLayout, QDialogButtonBox, QCheckBox,
)
from unidecode import unidecode

from src.utils.buscador import interpretar_consulta, normalizar, NOMBRES_FUENTE
from src.utils.formato_tags import tags_desde_coincidencia

COLUMNAS = [("tengo", "Tuya"), ("titulo", "Título"), ("orquesta", "Orquesta"), ("cantor", "Cantor"),
            ("fecha", "Fecha"), ("estilo", "Estilo"), ("musica", "Música"), ("letra", "Letra"),
            ("fuentes", "Fuente"), ("audio", "Audio")]
RESALTABLES = {"titulo", "orquesta", "cantor", "musica", "letra"}
GRIS = "#8a8a8a"


def resaltar(texto, palabras):
    """Devuelve HTML con en negrita las palabras buscadas (por comienzo de palabra, sin acentos)."""
    texto = str(texto or "")
    if not palabras or not texto:
        return html.escape(texto)
    # Texto normalizado carácter a carácter, recordando la posición original de cada uno
    normal, origen = [], []
    for i, ch in enumerate(texto):
        for c in unidecode(ch).lower():
            normal.append(c)
            origen.append(i)
    normal = "".join(normal)
    marcas = [False] * len(texto)
    for p in palabras:
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(p)}", normal):
            for j in range(m.start(), m.end()):
                marcas[origen[j]] = True
    salida, dentro = [], False
    for ch, marca in zip(texto, marcas):
        if marca and not dentro:
            salida.append("<b style='background:#fff59d'>")
        elif not marca and dentro:
            salida.append("</b>")
        dentro = marca
        salida.append(html.escape(ch))
    if dentro:
        salida.append("</b>")
    return "".join(salida)


class ModeloResultados(QAbstractTableModel):
    def __init__(self, reproductor):
        super().__init__()
        self.reproductor = reproductor
        self.df = pd.DataFrame()
        self.palabras = []

    def poner(self, df, palabras):
        self.beginResetModel()
        self.df = df.reset_index(drop=True)
        self.palabras = palabras
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.df)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNAS)

    def headerData(self, seccion, orientacion, rol=Qt.DisplayRole):
        if orientacion == Qt.Horizontal and rol == Qt.DisplayRole:
            return COLUMNAS[seccion][1]
        return None

    def fila(self, n):
        return self.df.iloc[n]

    def texto(self, fila, campo):
        if campo == "tengo":
            return {"si": "✔", "otra": "≈"}.get(fila.get("_tengo", ""), "")
        if campo == "fuentes":
            return " · ".join(NOMBRES_FUENTE.get(f, f) for f in fila["fuentes"])
        if campo == "audio":
            if not (fila["audio30"] or fila["audio10"]):
                return ""
            suena = any(self.reproductor.sonando(("bd", fila[c])) for c in ("audio30", "audio10") if fila[c])
            return "■" if suena else "▶"
        return str(fila[campo] or "")

    def data(self, indice, rol=Qt.DisplayRole):
        if not indice.isValid():
            return None
        fila = self.df.iloc[indice.row()]
        campo = COLUMNAS[indice.column()][0]
        valor = self.texto(fila, campo)
        if rol == Qt.DisplayRole:
            if campo == "cantor" and not valor:
                return "instrumental"
            if campo == "fecha" and not valor:
                return "sin fecha"
            if campo in ("musica", "letra") and not valor:
                return "?"
            return valor
        if rol == Qt.UserRole:          # HTML que pinta el delegado
            if not valor:
                vacio = {"cantor": "instrumental", "fecha": "sin fecha", "musica": "?", "letra": "?"}.get(campo, "")
                return f"<i style='color:{GRIS}'>{vacio}</i>"
            if campo == "tengo" and valor:
                color = "#2e7d32" if valor == "✔" else "#ef6c00"
                return f"<b style='color:{color}'>{valor}</b>"
            if campo == "audio" and valor == "■":
                return "<b style='color:white; background:#43a047'>&nbsp;■&nbsp;</b>"
            if campo == "fuentes":
                return f"<span style='color:{GRIS}'>{html.escape(valor)}</span>"
            if campo in RESALTABLES:
                return resaltar(valor, self.palabras)
            return html.escape(valor)
        if rol == Qt.ToolTipRole:
            if campo == "audio":
                return {"▶": "Clic para escuchar el fragmento", "■": "Sonando: clic para parar"}.get(valor)
            if campo == "tengo":
                return {"✔": "La tienes en tu colección (mismo título, orquesta y año)",
                        "≈": "Tienes este tema por esta orquesta, pero con otra fecha "
                             "(otra grabación, o tu archivo tiene la fecha del CD)"}.get(valor, "No la tienes")
            return valor or None
        if rol == Qt.TextAlignmentRole and campo in ("audio", "tengo"):
            return Qt.AlignCenter
        return None


class DelegadoResaltado(QStyledItemDelegate):
    """Pinta el texto como HTML para poder resaltar en negrita lo buscado."""

    def paint(self, painter, opcion, indice):
        contenido = indice.data(Qt.UserRole)
        if contenido is None:
            return super().paint(painter, opcion, indice)
        op = QStyleOptionViewItem(opcion)
        self.initStyleOption(op, indice)
        op.text = ""
        estilo = op.widget.style() if op.widget else QApplication.style()
        estilo.drawControl(QStyle.CE_ItemViewItem, op, painter, op.widget)
        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setDefaultFont(op.font)
        seleccionada = bool(op.state & QStyle.State_Selected)
        color = op.palette.color(QPalette.HighlightedText if seleccionada else QPalette.Text)
        if seleccionada:   # sobre el azul de la selección: solo negrita, sin fondo ni gris
            contenido = contenido.replace("background:#fff59d", "").replace(f"color:{GRIS}", "")
        alineado = indice.data(Qt.TextAlignmentRole) == Qt.AlignCenter
        if alineado:
            doc.setTextWidth(op.rect.width())
            contenido = f"<div align='center'>{contenido}</div>"
        doc.setHtml(f"<span style='color:{color.name()}; white-space:pre'>{contenido}</span>")
        rect = op.rect.adjusted(0, 0, 0, 0) if alineado else estilo.subElementRect(QStyle.SE_ItemViewItemText, op, op.widget)
        painter.save()
        painter.translate(rect.left(), rect.top() + (rect.height() - doc.size().height()) / 2)
        doc.drawContents(painter, QRectF(0, 0, rect.width(), rect.height()))
        painter.restore()


class Chip(QPushButton):
    """Botón de filtro que se queda pulsado."""

    def __init__(self, texto, tooltip=""):
        super().__init__(texto)
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton{border:1px solid #bbb; border-radius:11px; padding:3px 12px; background:#fafafa;}"
            "QPushButton:checked{background:#1e88e5; color:white; border-color:#1e88e5;}"
            "QPushButton:hover:!checked{background:#eef5fd;}")


class VentanaBuscador(QWidget):
    """
    obtener_indice(): devuelve el IndiceBusqueda (puede tardar la primera vez).
    obtener_bd(): DataFrame completo de la base de datos (para construir las tags).
    usar(archivo, indice_bd): asigna la grabación a la canción.
    reproducir(enlace) / parar(): audio de los fragmentos de la base de datos.
    """

    def __init__(self, parent, obtener_indice, obtener_bd, usar, reproductor, recargar_bd, obtener_tengo=None):
        super().__init__(parent, Qt.Window)
        self.recargar_bd = recargar_bd
        self.obtener_tengo = obtener_tengo
        self.tengo = None
        self.reproductor = reproductor
        self.setWindowTitle("Buscar en la base de datos")
        self.obtener_indice, self.obtener_bd = obtener_indice, obtener_bd
        self.usar_callback = usar
        self.indice = None
        self.destino = None
        self.settings = QSettings("TangoTags", "TangoTags")
        self.temporizador = QTimer(self, singleShot=True, interval=250, timeout=self.buscar)

        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        # --- Canción de destino
        self.etiqueta_destino = QLabel()
        self.etiqueta_destino.setWordWrap(True)
        self.etiqueta_destino.setStyleSheet("background:#e3f2fd; border-radius:6px; padding:6px 10px;")
        lay.addWidget(self.etiqueta_destino)

        # --- Caja de búsqueda
        self.caja = QLineEdit()
        self.caja.setClearButtonEnabled(True)
        self.caja.setPlaceholderText("Buscar título, orquesta, cantor, compositor o año…   "
                                     "p. ej.  rosa firpo   ·   pugliese chanel 1944   ·   di sarli 1940-1945")
        self.caja.setStyleSheet("QLineEdit{font-size:16px; padding:8px 10px; border:2px solid #90caf9;"
                                " border-radius:8px;} QLineEdit:focus{border-color:#1e88e5;}")
        self.caja.textChanged.connect(lambda: self.temporizador.start())
        self.caja.returnPressed.connect(self.enter)
        lay.addWidget(self.caja)

        # --- Filtros
        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Estilo:"))
        self.chips_estilo = {}
        for clave, texto in (("tango", "Tango"), ("vals", "Vals"), ("milonga", "Milonga"), ("otros", "Otros")):
            c = Chip(texto, "Pulsa varios para combinarlos; ninguno = todos")
            c.toggled.connect(self.buscar)
            self.chips_estilo[clave] = c
            filtros.addWidget(c)
        filtros.addSpacing(16)
        filtros.addWidget(QLabel("Fuente:"))
        self.chips_fuente = {}
        for clave in ("recodo", "tangoinfo"):
            c = Chip(NOMBRES_FUENTE[clave], "Solo grabaciones que están en esta fuente")
            c.toggled.connect(self.buscar)
            self.chips_fuente[clave] = c
            filtros.addWidget(c)
        filtros.addSpacing(16)
        self.chip_audio = Chip("Con audio", "Solo grabaciones con fragmento para escuchar")
        self.chip_audio.toggled.connect(self.buscar)
        filtros.addWidget(self.chip_audio)
        filtros.addSpacing(16)
        filtros.addWidget(QLabel("Tu colección:"))
        self.chip_tengo = Chip("La tengo", "Solo las grabaciones que ya tienes (✔ misma fecha, ≈ otra fecha)")
        self.chip_no_tengo = Chip("Me falta", "Solo las grabaciones que NO tienes en tu colección")
        for c in (self.chip_tengo, self.chip_no_tengo):
            c.toggled.connect(self.buscar)
            filtros.addWidget(c)
        filtros.addSpacing(16)
        filtros.addWidget(QLabel("Años:"))
        self.desde, self.hasta = QSpinBox(), QSpinBox()
        for sb, texto in ((self.desde, "desde"), (self.hasta, "hasta")):
            sb.setRange(1899, 2030)
            sb.setSpecialValueText(texto)   # el mínimo significa "sin límite"
            sb.setValue(1899)
            sb.setFixedWidth(80)
            sb.valueChanged.connect(lambda: self.temporizador.start())
            filtros.addWidget(sb)
        limpiar = QPushButton("Quitar filtros")
        limpiar.setFlat(True)
        limpiar.setStyleSheet(f"color:{GRIS};")
        limpiar.clicked.connect(self.quitar_filtros)
        filtros.addWidget(limpiar)
        filtros.addStretch(1)
        lay.addLayout(filtros)

        self.info = QLabel()
        self.info.setStyleSheet(f"color:{GRIS};")
        lay.addWidget(self.info)

        # --- Resultados
        self.modelo = ModeloResultados(reproductor)
        self.tabla = QTableView()
        self.tabla.setModel(self.modelo)
        self.tabla.setItemDelegate(DelegadoResaltado(self.tabla))
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.setWordWrap(False)
        self.tabla.verticalHeader().hide()
        self.tabla.verticalHeader().setDefaultSectionSize(26)
        fuente = self.tabla.font()
        fuente.setPointSize(10)
        self.tabla.setFont(fuente)
        h = self.tabla.horizontalHeader()
        h.setHighlightSections(False)
        from src.ui.columnas import preparar_columnas
        anchos = {"tengo": 44, "titulo": 260, "orquesta": 190, "cantor": 170, "fecha": 95, "estilo": 100,
                  "musica": 190, "letra": 190, "fuentes": 140, "audio": 50}
        preparar_columnas(self.tabla, "buscador", {i: anchos[c] for i, (c, _) in enumerate(COLUMNAS)},
                          siempre_visibles={1})
        self.tabla.selectionModel().selectionChanged.connect(self.mostrar_detalle)
        self.tabla.doubleClicked.connect(
            lambda i: None if COLUMNAS[i.column()][0] == "audio" else self.enter_tabla())
        self.tabla.clicked.connect(self.clic_tabla)

        # --- Ficha de la grabación seleccionada
        self.ficha = QFrame()
        self.ficha.setStyleSheet("QFrame#ficha{background:#fafafa; border:1px solid #e0e0e0; border-radius:8px;}")
        self.ficha.setObjectName("ficha")
        ficha_lay = QHBoxLayout(self.ficha)
        self.texto_ficha = QLabel()
        self.texto_ficha.setTextFormat(Qt.RichText)
        self.texto_ficha.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.texto_ficha.setWordWrap(True)
        ficha_lay.addWidget(self.texto_ficha, 1)
        botones = QVBoxLayout()
        self.boton_usar = QPushButton("✔  Usar para esta canción")
        self.boton_usar.setStyleSheet("QPushButton{font-weight:bold; padding:8px 14px; background:#2e7d32;"
                                      " color:white; border-radius:6px;} QPushButton:disabled{background:#c8c8c8;}")
        self.boton_usar.clicked.connect(self.usar)
        self.boton_30 = QPushButton("▶  Escuchar 30 s")
        self.boton_10 = QPushButton("▶  Escuchar 10 s")
        self.boton_parar = QPushButton("■  Parar")
        self.boton_mia = QPushButton("▶  Escuchar la mía")
        self.boton_mia.setToolTip("Escuchar tu archivo de esta grabación")
        self.boton_mia.clicked.connect(self.escuchar_mia)
        self.boton_copiar = QPushButton("Copiar ficha")
        self.boton_corregir = QPushButton("✎  Corregir datos…")
        self.boton_corregir.setToolTip("Corregir un error de la base de datos (se guarda en data/correcciones.csv)")
        self.boton_corregir.clicked.connect(self.corregir)
        self.boton_30.clicked.connect(lambda: self.escuchar("audio30"))
        self.boton_10.clicked.connect(lambda: self.escuchar("audio10"))
        self.boton_parar.clicked.connect(self.reproductor.parar)
        self.reproductor.cambiado.connect(self.sonando_cambiado)
        self.boton_copiar.clicked.connect(self.copiar)
        for b in (self.boton_usar, self.boton_30, self.boton_10, self.boton_mia, self.boton_parar,
                  self.boton_copiar, self.boton_corregir):
            botones.addWidget(b)
        botones.addStretch(1)
        ficha_lay.addLayout(botones)

        division = QSplitter(Qt.Vertical)
        division.addWidget(self.tabla)
        division.addWidget(self.ficha)
        division.setSizes([500, 190])
        division.setCollapsible(1, False)
        lay.addWidget(division, 1)

        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: (self.caja.setFocus(), self.caja.selectAll()))
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.usar)

        self.restaurar()
        self.set_destino(None)
        self.mostrar_detalle()

    # ------------------------------------------------------------------ estado
    def restaurar(self):
        geometria = self.settings.value("buscador_geometria")
        if geometria is not None:
            self.restoreGeometry(geometria)
        else:
            self.resize(1300, 780)
        for clave, c in {**self.chips_estilo, **self.chips_fuente}.items():
            c.blockSignals(True)
            c.setChecked(self.settings.value(f"buscador_{clave}", False, type=bool))
            c.blockSignals(False)

    def closeEvent(self, evento):
        self.settings.setValue("buscador_geometria", self.saveGeometry())
        for clave, c in {**self.chips_estilo, **self.chips_fuente}.items():
            self.settings.setValue(f"buscador_{clave}", c.isChecked())
        super().closeEvent(evento)

    def quitar_filtros(self):
        for c in [*self.chips_estilo.values(), *self.chips_fuente.values(), self.chip_audio,
                  self.chip_tengo, self.chip_no_tengo]:
            c.blockSignals(True)
            c.setChecked(False)
            c.blockSignals(False)
        self.desde.setValue(self.desde.minimum())
        self.hasta.setValue(self.hasta.minimum())
        self.buscar()

    def set_destino(self, archivo, buscar_por_defecto=False):
        """Canción a la que se asignará la grabación elegida (la seleccionada en la ventana principal)."""
        self.destino = archivo
        if archivo is None:
            self.etiqueta_destino.setText(
                "Sin canción seleccionada: puedes buscar libremente. Para asignar una grabación a una "
                "canción, selecciónala en la ventana principal (esta ventana puede quedarse abierta).")
            self.boton_usar.setEnabled(False)
        else:
            t = archivo.tags
            titulo = getattr(t, "title", "") or archivo.ruta_archivo
            self.etiqueta_destino.setText(
                f"Canción seleccionada: <b>{html.escape(str(titulo))}</b> — {html.escape(str(getattr(t, 'artist', '') or ''))}"
                f" ({html.escape(str(getattr(t, 'year', '') or 'sin año'))})")
            self.boton_usar.setEnabled(self.grabacion_actual() is not None)
            if buscar_por_defecto:
                from src.utils.buscar_artista import separar_orquesta_cantor
                orquesta = separar_orquesta_cantor(getattr(t, "artist", "") or "")[0]
                orquesta = orquesta.split(",")[0]          # "D'Arienzo, Juan" -> "D'Arienzo"
                palabras = [w for w in orquesta.split() if w.lower() not in ("orquesta", "típica", "tipica", "de")]
                apellido = palabras[-1] if palabras else ""
                self.caja.setText(f"{titulo} {apellido}".strip())

    # ------------------------------------------------------------------ búsqueda
    def asegurar_indice(self):
        if self.indice is None:
            self.info.setText("Preparando el índice de búsqueda (solo la primera vez)…")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            try:
                self.indice = self.obtener_indice()
            finally:
                QApplication.restoreOverrideCursor()
        return self.indice

    def buscar(self):
        indice = self.asegurar_indice()
        texto = self.caja.text()
        estilos = {k for k, c in self.chips_estilo.items() if c.isChecked()} or None
        fuentes = {k for k, c in self.chips_fuente.items() if c.isChecked()} or None
        desde = self.desde.value() if self.desde.value() > self.desde.minimum() else None
        hasta = self.hasta.value() if self.hasta.value() > self.hasta.minimum() else None
        palabras, d_texto, h_texto = interpretar_consulta(texto)
        if not palabras and d_texto is None and not estilos and not fuentes and desde is None and hasta is None:
            self.modelo.poner(pd.DataFrame(), [])
            self.info.setText("Escribe para buscar. Las palabras pueden ir en cualquier orden; "
                              "un año (1944), un rango (1940-1945) o una década (1940s) filtran por fecha.")
            self.mostrar_detalle()
            return
        r = indice.buscar(texto, estilos=estilos, fuentes=fuentes, desde=desde, hasta=hasta)
        if self.chip_audio.isChecked() and not r.empty:
            r = r[(r["audio30"] != "") | (r["audio10"] != "")]
        r = self.marcar_tengo(r)
        if not r.empty and (self.chip_tengo.isChecked() or self.chip_no_tengo.isChecked()):
            quiero = set()
            if self.chip_tengo.isChecked():
                quiero |= {"si", "otra"}
            if self.chip_no_tengo.isChecked():
                quiero |= {""}
            r = r[r["_tengo"].isin(quiero)]
        palabras_n = [normalizar(p) for p in palabras if normalizar(p)]
        self.modelo.poner(r, palabras_n)

        partes = []
        if palabras_n:
            partes.append("palabras: " + " ".join(f"«{p}»" for p in palabras_n))
        d, h = (d_texto, h_texto) if d_texto is not None else (desde, hasta)
        if d is not None or h is not None:
            partes.append(f"años {d if d is not None else '…'}–{h if h is not None else '…'}"
                          if d != h else f"año {d}")
        filas_bd = int(r["repeticiones"].sum()) if not r.empty else 0
        resumen = "1 grabación" if len(r) == 1 else f"{len(r)} grabaciones"
        if filas_bd > len(r):
            resumen += f" ({filas_bd} filas en la base de datos; las repetidas se muestran juntas)"
        self.info.setText(("Buscando " + " · ".join(partes) + "  →  " if partes else "") + resumen)
        if len(r):
            self.tabla.selectRow(0)
            self.tabla.scrollToTop()
        else:
            self.mostrar_detalle()

    # ------------------------------------------------------------------ ficha
    def grabacion_actual(self):
        filas = self.tabla.selectionModel().selectedRows()
        if not filas or self.modelo.rowCount() == 0:
            return None
        return self.modelo.fila(filas[0].row())

    def mostrar_detalle(self, *_):
        g = self.grabacion_actual()
        hay = g is not None
        self.boton_usar.setEnabled(hay and self.destino is not None)
        self.boton_30.setEnabled(hay and bool(g["audio30"]))
        self.boton_10.setEnabled(hay and bool(g["audio10"]))
        self.boton_copiar.setEnabled(hay)
        self.boton_corregir.setEnabled(hay)
        self.boton_mia.setEnabled(hay and bool(g.get("_mias")))
        self.sonando_cambiado(self.reproductor.clave)
        if not hay:
            self.texto_ficha.setText(f"<span style='color:{GRIS}'>Selecciona una grabación para ver su ficha.</span>")
            return
        esc = lambda x: html.escape(str(x or ""))
        tags = tags_desde_coincidencia(self.obtener_bd().loc[g["indice_bd"]])
        fuentes = " y ".join(NOMBRES_FUENTE.get(f, f) for f in g["fuentes"]) or "—"
        rep = f" ({g['repeticiones']} filas)" if g["repeticiones"] > 1 else ""
        etiqueta = lambda t: f"<td style='color:{GRIS}; padding-right:8px'>{t}</td>"
        corregida = " <span style='color:#e65100'>(corregida a mano)</span>" if g.get("corregida") else ""
        self.texto_ficha.setText(f"""
            <div style='font-size:18px'><b>{esc(g['titulo'])}</b>{corregida}</div>
            <div style='font-size:14px; margin-top:2px'>{esc(g['orquesta'])}
                {' — ' + esc(g['cantor']) if g['cantor'] else " — <i style='color:" + GRIS + "'>instrumental</i>"}</div>
            <table width='75%' style='margin-top:8px' cellspacing=0 cellpadding=2>
              <tr>{etiqueta('Fecha')}<td width='35%'>{esc(g['fecha']) or '<i>sin fecha</i>'}</td>
                  {etiqueta('Estilo')}<td>{esc(g['estilo']) or '—'}</td></tr>
              <tr>{etiqueta('Música')}<td>{esc(g['musica']) or '?'}</td>
                  {etiqueta('Letra')}<td>{esc(g['letra']) or '?'}</td></tr>
              <tr>{etiqueta('Fuente')}<td colspan=3>{esc(fuentes)}{rep}</td></tr>
              <tr>{etiqueta('Tu colección')}<td colspan=3>{self.texto_mias(g)}</td></tr>
            </table>
            <div style='margin-top:8px; color:{GRIS}'>Tags que se escribirían:</div>
            <div style='font-family:Consolas,monospace; font-size:12px'>
              {esc(tags['title'])} &nbsp;|&nbsp; {esc(tags['artist'])} &nbsp;|&nbsp; {esc(tags['year']) or '—'}
              &nbsp;|&nbsp; {esc(tags['genre']) or '—'} &nbsp;|&nbsp; {esc(tags['composer'])}</div>""")

    # ------------------------------------------------------------------ acciones
    def enter(self):
        """Enter en la caja: busca ya y pasa a la lista."""
        self.temporizador.stop()
        self.buscar()
        self.tabla.setFocus()

    def clic_tabla(self, indice):
        if COLUMNAS[indice.column()][0] == "audio":
            self.escuchar("audio30") if self.boton_30.isEnabled() else self.escuchar("audio10")

    def enter_tabla(self):
        if self.destino is not None:
            self.usar()
        else:
            self.escuchar("audio30") if self.boton_30.isEnabled() else self.escuchar("audio10")

    def keyPressEvent(self, evento):
        if self.tabla.hasFocus() and evento.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.enter_tabla()
            return
        if self.caja.hasFocus() and evento.key() == Qt.Key_Down:
            self.tabla.setFocus()
            return
        super().keyPressEvent(evento)

    def usar(self):
        g = self.grabacion_actual()
        if g is None or self.destino is None:
            return
        self.usar_callback(self.destino, g["indice_bd"])
        self.info.setText(f"✔ Asignada «{g['titulo']}» ({g['orquesta']}) a la canción seleccionada. "
                          "Revisa y pulsa Aplicar tags en la ventana principal.")

    def escuchar(self, campo):
        g = self.grabacion_actual()
        if g is not None and g[campo]:
            from src.utils.utils import link_to_music
            duracion = "30 s" if campo == "audio30" else "10 s"
            self.reproductor.alternar(("bd", g[campo]), link_to_music(g[campo]),
                                      f"BD {duracion}: {g['titulo']} — {g['orquesta']} ({g['fecha'] or 'sin fecha'})")

    def sonando_cambiado(self, clave):
        """Refresca ■/▶ en la columna Audio y en los botones de la ficha."""
        col = [c for c, _ in COLUMNAS].index("audio")
        if self.modelo.rowCount():
            self.modelo.dataChanged.emit(self.modelo.index(0, col), self.modelo.index(self.modelo.rowCount() - 1, col))
        g = self.grabacion_actual()
        for boton, campo, duracion in ((self.boton_30, "audio30", "30 s"), (self.boton_10, "audio10", "10 s")):
            suena = g is not None and bool(g[campo]) and self.reproductor.sonando(("bd", g[campo]))
            boton.setText(f"■  Parar ({duracion})" if suena else f"▶  Escuchar {duracion}")
            boton.setStyleSheet("background:#43a047; color:white; font-weight:bold;" if suena else "")

    def corregir(self):
        g = self.grabacion_actual()
        if g is None:
            return
        dialogo = DialogoCorregir(self, g)
        if dialogo.exec_() != QDialog.Accepted:
            return
        from src.utils import correcciones
        bd = self.obtener_bd()
        valores = dialogo.valores()
        correcciones.guardar(bd.loc[g["indice_bd"], "_clave_original"], valores)
        if dialogo.todas.isChecked():
            # El mismo tema grabado por otras orquestas: se corrige solo música y letra, y solo donde
            # tenían el mismo dato (equivocado) que esta grabación
            gr = self.indice.grabaciones
            mismas = gr[(gr["_titulo_n"] == normalizar(g["titulo"])) & (gr["indice_bd"] != g["indice_bd"])
                        & (gr["musica"] == g["musica"]) & (gr["letra"] == g["letra"])]
            for indice_bd in mismas["indice_bd"]:
                correcciones.guardar(bd.loc[indice_bd, "_clave_original"],
                                     {"musica": valores["musica"], "letra": valores["letra"]})
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.info.setText("Guardando la corrección y recargando la base de datos…")
            QApplication.processEvents()
            self.recargar_bd()
            self.indice = None
            self.buscar()
        finally:
            QApplication.restoreOverrideCursor()
        self.info.setText(self.info.text() + "   ✔ Corrección guardada.")

    # ------------------------------------------------------------------ ¿la tengo?
    def marcar_tengo(self, r):
        """Añade a los resultados _tengo ('si'/'otra'/'') y _mias (tus archivos de esa grabación)."""
        if self.tengo is None and self.obtener_tengo is not None:
            self.tengo = self.obtener_tengo() or False
        if r.empty or not self.tengo:
            r = r.copy()
            r["_tengo"], r["_mias"] = "", [[] for _ in range(len(r))]
            return r
        estados = [self.tengo.buscar(t, o, f) for t, o, f in zip(r["titulo"], r["orquesta"], r["fecha"])]
        r = r.copy()
        r["_tengo"] = [e for e, _ in estados]
        r["_mias"] = [m for _, m in estados]
        return r

    def texto_mias(self, g):
        if not self.tengo:
            return (f"<span style='color:{GRIS}'>Para saberlo, abre una vez <i>Archivo → Estado de la "
                    "colección</i></span>")
        mias = g.get("_mias") or []
        if not mias:
            return "<span style='color:#c62828'>No la tienes</span>"
        cabecera = ("<b style='color:#2e7d32'>✔ La tienes</b>" if g.get("_tengo") == "si"
                    else "<b style='color:#ef6c00'>≈ Tienes este tema por esta orquesta con otra fecha</b>")
        lista = "<br>".join(html.escape(m.split("MUSICA", 1)[-1].lstrip("\\/")) for m in mias[:3])
        return f"{cabecera}<br><span style='font-size:11px; color:#555'>{lista}</span>"

    def escuchar_mia(self):
        g = self.grabacion_actual()
        if g is not None and g.get("_mias"):
            ruta = g["_mias"][0]
            self.reproductor.alternar(("archivo", ruta), ruta, f"Tu archivo: {g['titulo']} — {g['orquesta']}")

    def copiar(self):
        g = self.grabacion_actual()
        if g is None:
            return
        QApplication.clipboard().setText(
            f"{g['titulo']} — {g['orquesta']}" + (f" / {g['cantor']}" if g["cantor"] else "")
            + f" — {g['fecha'] or 'sin fecha'} — {g['estilo']} — Música: {g['musica'] or '?'} - Letra: {g['letra'] or '?'}")
        self.info.setText("Ficha copiada al portapapeles.")


class DialogoCorregir(QDialog):
    """Formulario para corregir los datos de una grabación."""

    CAMPOS = [("titulo", "Título"), ("orquesta", "Orquesta"), ("cantor", "Cantor"), ("fecha", "Fecha"),
              ("estilo", "Estilo"), ("musica", "Música"), ("letra", "Letra")]

    def __init__(self, parent, grabacion):
        super().__init__(parent)
        self.setWindowTitle("Corregir datos de la grabación")
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        aviso = QLabel("La corrección se guarda en <b>data/correcciones.csv</b> y se aplica siempre al cargar "
                       "(también si regeneras la base de datos). Fecha: AAAA-MM-DD, AAAA-MM o AAAA. "
                       "Cantor vacío = instrumental; varios: «A y B».")
        aviso.setWordWrap(True)
        aviso.setStyleSheet(f"color:{GRIS};")
        lay.addWidget(aviso)
        form = QFormLayout()
        self.cajas = {}
        for campo, nombre in self.CAMPOS:
            caja = QLineEdit(str(grabacion[campo] or ""))
            self.cajas[campo] = caja
            form.addRow(nombre + ":", caja)
        lay.addLayout(form)
        self.todas = QCheckBox(f"Aplicar música y letra a todas las grabaciones de «{grabacion['titulo']}» "
                               "que tienen el mismo dato")
        self.todas.setChecked(True)
        self.todas.setToolTip("El compositor es del tema, no de la grabación: normalmente hay que corregirlo en todas")
        lay.addWidget(self.todas)
        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Save).setText("Guardar corrección")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        lay.addWidget(botones)

    def valores(self):
        v = {c: self.cajas[c].text().strip() for c, _ in self.CAMPOS}
        v["artista"] = v.pop("orquesta")
        if not v["cantor"]:
            v["cantor"] = "-"      # instrumental explícito
        return v
