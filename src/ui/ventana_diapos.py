"""Ventana para crear la presentación de las tandas a partir de una playlist."""
import os

import pandas as pd
from PyQt5.QtCore import Qt, QDate, QTime, QSettings
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDateEdit, QTimeEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QSplitter,
    QApplication, QProgressBar, QListWidget, QListWidgetItem, QWidget, QComboBox, QSpinBox, QProgressDialog,
)

from src.config.config import m3u_start_path, presentations_start_path, default_milonga_data
from src.diapos.generador import (
    leer_playlist, agrupar_tandas, crear_presentacion, duracion_texto, nombre_archivo, compositor_para_diapo,
)
from src.diapos import bpm, caracter, catalogo, historial
from src.diapos.revision import (
    revisar, horas_de_inicio, segundos_de_inicio, energia, bpm_tanda, ERROR, AVISO, AUTO, LIBRE, PATRONES,
    MINUTOS_SIN_MILONGA,
)
from src.ui.curva_noche import CurvaNoche
from src.ui.dialogo_propuesta import DialogoPropuesta
from src.ui.dialogo_reserva import DialogoReserva
from src.utils.utils import convertir_segundos


def _texto_bpm(valor):
    try:
        return f"{float(valor):.0f}" if valor and float(valor) == float(valor) else ""
    except (TypeError, ValueError):
        return ""


def _texto_actividad(valor):
    """Para las cortinas: tranquila / media / animada (según la actividad medida del audio)."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return ""
    if valor != valor:
        return ""
    if valor < bpm.CORTINA_TRANQUILA:
        return "tranquila"
    return "animada" if valor > bpm.CORTINA_ANIMADA else "media"


class VentanaDiapos(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear diapos de las tandas")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1400, 800)
        self.settings = QSettings("TangoTags", "TangoTags")
        self.tandas = []
        self.faltan = []
        self.avisos = []
        self.historial = []
        self.alternativas = {}
        self.cambios = []
        self.guardada = True
        self.playlist = None

        lay = QVBoxLayout(self)

        # --- Datos de la milonga (se recuerdan para la próxima vez)
        datos = QGridLayout()
        self.nombre = QLineEdit(self.settings.value("diapos_nombre", default_milonga_data["nombre"]))
        self.fecha = QDateEdit(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("dd/MM/yyyy")
        self.inicio = QTimeEdit(QTime.fromString(self.settings.value("diapos_inicio", default_milonga_data["hora_inicio"]), "HH:mm"))
        self.fin = QTimeEdit(QTime.fromString(self.settings.value("diapos_fin", default_milonga_data["hora_final"]), "HH:mm"))
        self.fecha.setMaximumWidth(130)
        for t in (self.inicio, self.fin):
            t.setDisplayFormat("HH:mm")
            t.setMaximumWidth(90)
            t.timeChanged.connect(self.actualizar_duracion)
        self.duracion = QLabel()
        # Reglas de la revisión (se recuerdan)
        self.patron = QComboBox()
        self.patron.addItem("Detectarlo", AUTO)
        for clave, (_, dibujo) in PATRONES.items():
            self.patron.addItem(f"{clave}  ({dibujo})", clave)
        self.patron.addItem("Libre (no mirar)", LIBRE)
        guardado = self.patron.findData(self.settings.value("diapos_patron", AUTO))
        self.patron.setCurrentIndex(max(guardado, 0))
        self.patron.currentIndexChanged.connect(self.cambiar_reglas)
        self.sin_milonga = QSpinBox()
        self.sin_milonga.setRange(0, 120)
        self.sin_milonga.setSingleStep(5)
        self.sin_milonga.setSuffix(" min")
        self.sin_milonga.setValue(int(self.settings.value("diapos_sin_milonga", MINUTOS_SIN_MILONGA)))
        self.sin_milonga.setToolTip("Al final de la noche no se ponen milongas (0 = no mirar)")
        self.sin_milonga.valueChanged.connect(self.cambiar_reglas)
        reglas = QHBoxLayout()
        reglas.addWidget(QLabel("<b>Patrón de bloques:</b>"))
        reglas.addWidget(self.patron)
        reglas.addSpacing(20)
        reglas.addWidget(QLabel("<b>Sin milonga los últimos</b>"))
        reglas.addWidget(self.sin_milonga)
        reglas.addStretch(1)
        editar_caracter = QPushButton("Editar tabla de carácter…")
        editar_caracter.setToolTip("Carácter, energía y dificultad de cada orquesta y época (se abre con Excel).\n"
                                   "Guarda y pulsa «Volver a revisar».")
        editar_caracter.clicked.connect(lambda: os.startfile(caracter.ARCHIVO))
        volver = QPushButton("↻ Volver a revisar")
        volver.clicked.connect(self.cambiar_reglas)
        reglas.addWidget(editar_caracter)
        reglas.addWidget(volver)
        datos.addWidget(QLabel("<b>Milonga:</b>"), 0, 0)
        datos.addWidget(self.nombre, 0, 1, 1, 6)
        datos.addWidget(QLabel("<b>Fecha:</b>"), 0, 7)
        datos.addWidget(self.fecha, 0, 8)
        datos.addWidget(QLabel("<b>De</b>"), 1, 0)
        datos.addWidget(self.inicio, 1, 1)
        datos.addWidget(QLabel("<b>a</b>"), 1, 2)
        datos.addWidget(self.fin, 1, 3)
        datos.addWidget(self.duracion, 1, 4, 1, 2)
        datos.setColumnStretch(6, 1)
        lay.addLayout(datos)
        lay.addLayout(reglas)

        fila = QHBoxLayout()
        self.boton_playlist = QPushButton("① Elegir playlist…")
        self.boton_playlist.clicked.connect(self.elegir_playlist)
        self.etiqueta_playlist = QLabel("<i>Ninguna playlist cargada</i>")
        fila.addWidget(self.boton_playlist)
        fila.addWidget(self.etiqueta_playlist, 1)
        # Cambios: propuestas solo de MUSICA\Edmundo; se guardan en un .m3u nuevo
        self.boton_tema = QPushButton("Cambiar tema…")
        self.boton_tema.setToolTip("Otro tema de la misma orquesta, cantor y época para el tema elegido abajo")
        self.boton_tema.clicked.connect(self.cambiar_tema)
        self.boton_tanda = QPushButton("Cambiar tanda…")
        self.boton_tanda.setToolTip("Otra tanda de 3 temas de tus 5 estrellas (sin orquestas que suenen cerca)")
        self.boton_tanda.clicked.connect(self.cambiar_tanda)
        self.boton_cortina = QPushButton("Cambiar cortina…")
        self.boton_cortina.setToolTip("Otra cortina que no suene esta noche ni haya sonado en este sitio")
        self.boton_cortina.clicked.connect(self.cambiar_cortina)
        self.boton_deshacer = QPushButton("↶ Deshacer")
        self.boton_deshacer.clicked.connect(self.deshacer)
        self.boton_guardar = QPushButton("Guardar playlist…")
        self.boton_guardar.setToolTip("Guarda la playlist con los cambios en un .m3u (no toca la original)")
        self.boton_guardar.clicked.connect(self.guardar_playlist)
        self.boton_flac = QPushButton("Usar FLAC")
        self.boton_flac.setToolTip("Cambia los MP3 de la playlist por la misma grabación en FLAC (en Edmundo)")
        self.boton_flac.clicked.connect(self.usar_flac)
        self.boton_reserva = QPushButton("Reserva…")
        self.boton_reserva.setToolTip("Tandas de reserva (vals de cumpleaños, tango extra, tango para el final) "
                                      "que no repiten nada de la noche, en un .m3u aparte")
        self.boton_reserva.clicked.connect(self.abrir_reserva)
        for b in (self.boton_tema, self.boton_tanda, self.boton_cortina, self.boton_flac, self.boton_deshacer,
                  self.boton_guardar, self.boton_reserva):
            b.setEnabled(False)
            fila.addWidget(b)
        lay.addLayout(fila)

        # --- Vista previa: tandas arriba, canciones de la tanda seleccionada abajo
        self.tabla_tandas = QTableWidget(0, 9)
        self.tabla_tandas.setHorizontalHeaderLabels(["#", "Tipo", "Título de la diapo", "Subtítulo", "Temas", "Duración",
                                                     "Empieza", "Carácter", "BPM"])
        self.tabla_tandas.verticalHeader().hide()
        self.tabla_tandas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_tandas.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla_tandas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.tabla_tandas.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabla_tandas.itemSelectionChanged.connect(self.mostrar_canciones)

        self.tabla_canciones = QTableWidget(0, 7)
        self.tabla_canciones.setHorizontalHeaderLabels(["Título", "Artista", "Año", "Compositor (en la diapo)", "Duración",
                                                        "BPM", "Volumen"])
        self.tabla_canciones.horizontalHeaderItem(6).setToolTip(
            "Volumen medio del centro del tema; entre paréntesis, la diferencia con el resto de la tanda")
        self.tabla_canciones.verticalHeader().hide()
        self.tabla_canciones.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.tabla_canciones.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        # --- Revisión: lo que conviene mirar antes de crear la presentación (clic = ir a la tanda)
        self.lista_revision = QListWidget()
        self.lista_revision.itemClicked.connect(self.ir_a_aviso)
        caja_revision = QWidget()
        lay_revision = QVBoxLayout(caja_revision)
        lay_revision.setContentsMargins(0, 0, 0, 0)
        self.titulo_revision = QLabel("<b>Revisión</b>")
        lay_revision.addWidget(self.titulo_revision)
        self.curva = CurvaNoche()
        self.curva.setToolTip("Energía de cada tanda (tabla de carácter afinada con el BPM). Clic = ir a la tanda")
        self.curva.tanda_clicada.connect(self.ir_a_fila)
        abajo_revision = QSplitter(Qt.Horizontal)
        abajo_revision.addWidget(self.lista_revision)
        abajo_revision.addWidget(self.curva)
        abajo_revision.setSizes([800, 550])
        lay_revision.addWidget(abajo_revision)

        division = QSplitter(Qt.Vertical)
        division.addWidget(self.tabla_tandas)
        division.addWidget(self.tabla_canciones)
        division.addWidget(caja_revision)
        division.setSizes([420, 160, 210])
        lay.addWidget(division, 1)

        self.resumen = QLabel()
        lay.addWidget(self.resumen)

        abajo = QHBoxLayout()
        self.progreso = QProgressBar()
        self.progreso.hide()
        abajo.addWidget(self.progreso, 1)
        abajo.addStretch(1)
        self.boton_crear = QPushButton("② Crear presentación")
        self.boton_crear.setEnabled(False)
        self.boton_crear.setStyleSheet("QPushButton{font-weight:bold; padding:6px 18px;}")
        self.boton_crear.clicked.connect(self.crear)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.close)
        abajo.addWidget(self.boton_crear)
        abajo.addWidget(cerrar)
        lay.addLayout(abajo)

        self.actualizar_duracion()

    def datos(self):
        return {"milonga": self.nombre.text().strip(), "fecha": self.fecha.date().toPyDate(),
                "inicio": self.inicio.time().toString("HH:mm"), "fin": self.fin.time().toString("HH:mm")}

    def actualizar_duracion(self):
        d = self.datos()
        self.duracion.setText(f"Duración: {duracion_texto(d['inicio'], d['fin'])}")
        if self.tandas:
            self.revisar()

    def cambiar_reglas(self):
        self.settings.setValue("diapos_patron", self.patron.currentData())
        self.settings.setValue("diapos_sin_milonga", self.sin_milonga.value())
        if self.tandas:
            self.revisar()

    def elegir_playlist(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elegir playlist", self.settings.value("dir_playlist_diapos", m3u_start_path) or m3u_start_path,
            "Playlists (*.m3u *.m3u8 *.mbp);;Todos (*.*)")
        if ruta:
            self.settings.setValue("dir_playlist_diapos", os.path.dirname(ruta))
            self.cargar_playlist(ruta)

    def cargar_playlist(self, ruta):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            canciones, faltan = leer_playlist(ruta)
        finally:
            QApplication.restoreOverrideCursor()
        self.playlist = ruta
        self.faltan = faltan
        self.historial = historial.anteriores(ruta)
        self.tandas = agrupar_tandas(canciones)
        self.cambios = []                  # playlists anteriores (planas) para deshacer
        self.guardada = True
        self.poner_etiqueta()
        self.rellenar_tandas()
        self.boton_crear.setEnabled(bool(self.tandas))
        for b in (self.boton_tema, self.boton_tanda, self.boton_cortina, self.boton_guardar, self.boton_reserva):
            b.setEnabled(bool(self.tandas))
        self.boton_deshacer.setEnabled(False)
        if faltan:
            QMessageBox.warning(self, "Canciones no encontradas",
                                f"{len(faltan)} canción(es) de la playlist no existen y no saldrán en las diapos:\n\n"
                                + "\n".join(faltan[:15]))
        self.calcular_bpm()

    # ------------------------------------------------------------------ cambios en la playlist
    def poner_etiqueta(self):
        n = sum(len(t.canciones) for t in self.tandas)
        texto = f"<b>{os.path.basename(self.playlist)}</b> — {n} canciones"
        if self.cambios:
            texto += (f" — <span style='background:#fff3c4'>&nbsp;{len(self.cambios)} cambio(s)"
                      + (" sin guardar" if not self.guardada else "") + "&nbsp;</span>")
        self.etiqueta_playlist.setText(texto)

    def _plana(self):
        return pd.concat([t.canciones for t in self.tandas], ignore_index=True)

    def _inicio_fila(self, fila):
        return sum(len(t.canciones) for t in self.tandas[:fila])

    def _fila_tanda(self):
        filas = self.tabla_tandas.selectionModel().selectedRows()
        return filas[0].row() if filas else None

    def _catalogo(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            return catalogo.catalogo()
        except Exception as e:
            QMessageBox.critical(self, "Biblioteca de MusicBee", f"No se pudo leer la biblioteca de MusicBee:\n{e}")
            return None
        finally:
            QApplication.restoreOverrideCursor()

    def _reproductor(self):
        r = getattr(self.parent(), "reproductor", None)
        if r is None:
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                from src.ui.reproductor import Reproductor
                r = self._reproductor_propio = getattr(self, "_reproductor_propio", None) or Reproductor(self)
            except Exception:
                return None
        return r

    def _aplicar(self, plana, fila):
        """Pone la playlist nueva (plana), recalcula todo y vuelve a la fila."""
        self.cambios.append(self._plana())
        self.guardada = False
        self.tandas = agrupar_tandas(plana)
        self.rellenar_tandas()
        self.calcular_bpm()
        self.poner_etiqueta()
        self.boton_deshacer.setEnabled(True)
        if fila is not None and fila < len(self.tandas):
            self.ir_a_fila(fila)

    @staticmethod
    def _fila_cancion(c):
        return {k: c[k] for k in ("ruta", "title", "artist", "artist1", "artist2", "year", "ano", "genre",
                                  "composer", "duration")}

    def cambiar_tema(self):
        fila = self._fila_tanda()
        if fila is None or self.tandas[fila].es_cortina:
            QMessageBox.information(self, "Cambiar tema", "Elige una tanda en la tabla de arriba "
                                                          "(para las cortinas está «Cambiar cortina…»).")
            return
        k = self.tabla_canciones.currentRow()
        if k < 0:
            QMessageBox.information(self, "Cambiar tema", "Elige en la lista de abajo el tema que quieres cambiar.")
            return
        cat = self._catalogo()
        if cat is None:
            return
        actual = self.tandas[fila].canciones.iloc[k]
        propuestas = {}

        def obtener(solo_5):
            p = propuestas[solo_5] = catalogo.proponer_temas(cat, self.tandas, fila, k, solo_5)
            filas = [[c["title"], c["artist2"] or "instrumental", c["ano"], "★" * int(c["estrellas"]), c["motivo"],
                      convertir_segundos(c["duration"])] for _, c in p.iterrows()]
            return ["Título", "Cantor", "Año", "Estrellas", "", "Duración"], filas, [[r] for r in p["ruta"]]

        d = DialogoPropuesta(self, "Cambiar tema",
                             f"Para cambiar <b>«{actual['title']}»</b> ({actual['artist']}, {actual['ano']}): temas de "
                             f"la misma orquesta, género y época que no suenan esta noche, solo de MUSICA\\Edmundo.",
                             obtener, self._reproductor())
        if d.exec_() != QDialog.Accepted or d.elegida is None:
            return
        nueva = propuestas[d.solo_5.isChecked()].iloc[d.elegida]
        plana = self._plana()
        plana.loc[self._inicio_fila(fila) + k, list(self._fila_cancion(nueva))] = list(self._fila_cancion(nueva).values())
        self._aplicar(plana, fila)

    def cambiar_tanda(self):
        fila = self._fila_tanda()
        if fila is None or self.tandas[fila].es_cortina or self.tandas[fila].es_cumparsita:
            QMessageBox.information(self, "Cambiar tanda", "Elige una tanda en la tabla de arriba.")
            return
        cat = self._catalogo()
        if cat is None:
            return
        tanda = self.tandas[fila]
        propuestas = {}

        def obtener(solo_5):
            p = propuestas[solo_5] = catalogo.proponer_tandas(cat, self.tandas, fila, solo_5)
            filas = [[t.orquesta, t.cantor, t.anos, t.motivo or "—", " · ".join(t.canciones["title"])] for t in p]
            return ["Orquesta", "Cantor", "Años", "Carácter", "Temas"], filas, [list(t.canciones["ruta"]) for t in p]

        d = DialogoPropuesta(self, "Cambiar tanda",
                             f"Para cambiar la tanda de <b>{tanda.titulo_orquesta}</b> ({tanda.subtitulo}): tandas de "
                             f"{tanda.genero or 'tango'} de 3 temas (misma orquesta, cantor y época), primero las de "
                             f"energía parecida, sin orquestas que suenen cerca, solo de MUSICA\\Edmundo. "
                             f"▶ va pasando por sus temas.", obtener, self._reproductor())
        if d.exec_() != QDialog.Accepted or d.elegida is None:
            return
        nueva = propuestas[d.solo_5.isChecked()][d.elegida].canciones
        plana = self._plana()
        inicio = self._inicio_fila(fila)
        filas_nuevas = pd.DataFrame([self._fila_cancion(c) for _, c in nueva.iterrows()])
        plana = pd.concat([plana.iloc[:inicio], filas_nuevas, plana.iloc[inicio + len(tanda.canciones):]],
                          ignore_index=True)
        self._aplicar(plana, fila)

    def cambiar_cortina(self):
        fila = self._fila_tanda()
        if fila is None or not self.tandas[fila].es_cortina:
            QMessageBox.information(self, "Cambiar cortina", "Elige una cortina en la tabla de arriba.")
            return
        cat = self._catalogo()
        if cat is None:
            return
        k = max(self.tabla_canciones.currentRow(), 0)
        siguiente = self.tandas[fila + 1] if fila + 1 < len(self.tandas) else None
        quiero = "media"
        if siguiente is not None and not siguiente.es_cortina:
            e = energia(siguiente, caracter.de_tanda(siguiente))
            if bpm.tipo(siguiente.genero) == "milonga" or (e is not None and e >= 4.5):
                quiero = "animada"
            elif e is not None and e <= 2.5:
                quiero = "tranquila"
        orden_actividad = {"tranquila": 0, "media": 1, "animada": 2}
        propuestas = {}

        def obtener(solo_5):
            p = catalogo.proponer_cortinas(cat, self.tandas, fila, self.historial, solo_5).copy()
            cache = bpm.CacheBpm()
            p["actividad"] = [cache.guardado(r, bpm.ACTIVIDAD)[1] for r in p["ruta"]]
            p["como"] = p["actividad"].map(_texto_actividad)
            # primero las que encajan con lo que viene; luego las demás (las no medidas al final)
            p["_orden"] = p["como"].map(lambda c: abs(orden_actividad[c] - orden_actividad[quiero])
                                        if c in orden_actividad else 9)
            p = propuestas[solo_5] = p.sort_values(["_orden", "artist"]).reset_index(drop=True)
            filas = [[c["title"], c["artist"], c["como"] or "sin medir", convertir_segundos(c["duration"])]
                     for _, c in p.iterrows()]
            return ["Título", "Artista", "Cómo es", "Duración"], filas, [[r] for r in p["ruta"]]

        texto_siguiente = (f"antes de <b>{siguiente.titulo_orquesta}</b> ({siguiente.genero})"
                           if siguiente is not None and not siguiente.es_cortina else "")
        d = DialogoPropuesta(self, "Cambiar cortina",
                             f"Cortinas que no suenan esta noche ni sonaron en este sitio el último año, solo de "
                             f"MUSICA\\Edmundo. {texto_siguiente}: van primero las <b>{quiero}s</b>. "
                             f"«Medir» calcula cómo es cada cortina (~0,2 s cada una, se guarda).",
                             obtener, self._reproductor())
        medir = QPushButton("Medir las no medidas")
        medir.clicked.connect(lambda: self._medir_cortinas(d, propuestas))
        d.layout().itemAt(d.layout().count() - 1).layout().insertWidget(1, medir)
        if d.exec_() != QDialog.Accepted or d.elegida is None:
            return
        nueva = propuestas[d.solo_5.isChecked()].iloc[d.elegida]
        plana = self._plana()
        posicion = self._inicio_fila(fila) + min(k, len(self.tandas[fila].canciones) - 1)
        plana.loc[posicion, list(self._fila_cancion(nueva))] = list(self._fila_cancion(nueva).values())
        self._aplicar(plana, fila)

    def _medir_cortinas(self, dialogo, propuestas):
        p = propuestas.get(dialogo.solo_5.isChecked())
        if p is None:
            return
        cache = bpm.CacheBpm()
        rutas = [r for r, c in zip(p["ruta"], p["como"]) if not c]
        progreso = QProgressDialog("Midiendo cortinas…", "Parar", 0, len(rutas), dialogo)
        progreso.setWindowModality(Qt.WindowModal)
        for n, r in enumerate(rutas, 1):
            if progreso.wasCanceled():
                break
            cache.actividad(r)
            progreso.setValue(n)
            QApplication.processEvents()
        progreso.close()
        dialogo.rellenar()

    def buscar_alternativas(self):
        """MP3 de la playlist que tienen la misma grabación en FLAC en Edmundo (solo si hay algún MP3)."""
        self.alternativas = {}
        if any(catalogo.con_perdida(r) for t in self.tandas for r in t.canciones["ruta"]):
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                self.alternativas = catalogo.versiones_sin_perdida(catalogo.catalogo(), self.tandas)
            except Exception:
                self.alternativas = {}
            finally:
                QApplication.restoreOverrideCursor()
        n = len(self.alternativas)
        self.boton_flac.setText(f"Usar FLAC ({n})" if n else "Usar FLAC")
        self.boton_flac.setEnabled(bool(n))

    def usar_flac(self):
        if not self.alternativas:
            return
        cat = self._catalogo()
        if cat is None:
            return
        por_ruta = cat.set_index("ruta")
        plana = self._plana()
        cambiadas = 0
        for n, ruta in enumerate(plana["ruta"]):
            nueva = self.alternativas.get(ruta)
            if nueva and nueva in por_ruta.index:
                fila_cat = por_ruta.loc[nueva]
                fila_cat = fila_cat.iloc[0] if hasattr(fila_cat, "columns") else fila_cat
                datos = self._fila_cancion(dict(fila_cat, ruta=nueva))
                plana.loc[n, list(datos)] = list(datos.values())
                cambiadas += 1
        if cambiadas:
            self._aplicar(plana, self._fila_tanda())

    def abrir_reserva(self):
        cat = self._catalogo()
        if cat is None:
            return
        DialogoReserva(self, cat, self.tandas, self.historial, self.playlist, self._reproductor()).exec_()

    def deshacer(self):
        if not self.cambios:
            return
        fila = self._fila_tanda()
        plana = self.cambios.pop()
        self.guardada = False
        self.tandas = agrupar_tandas(plana)
        self.rellenar_tandas()
        self.calcular_bpm()
        self.poner_etiqueta()
        self.boton_deshacer.setEnabled(bool(self.cambios))
        if fila is not None and fila < len(self.tandas):
            self.ir_a_fila(fila)

    def guardar_playlist(self):
        base, _ = os.path.splitext(os.path.basename(self.playlist))
        destino, _ = QFileDialog.getSaveFileName(
            self, "Guardar playlist con los cambios", os.path.join(os.path.dirname(self.playlist),
                                                                   f"{base}_revisada.m3u"),
            "Playlist (*.m3u)")
        if not destino:
            return
        if os.path.normcase(os.path.abspath(destino)) == os.path.normcase(os.path.abspath(self.playlist)):
            QMessageBox.warning(self, "Guardar", "Elige otro nombre: la playlist original no se sobrescribe.")
            return
        try:
            with open(destino, "w", encoding="utf-8-sig", newline="\r\n") as f:
                f.write("\n".join(self._plana()["ruta"]) + "\n")
        except OSError as e:
            QMessageBox.critical(self, "Guardar", f"No se pudo guardar:\n{e}")
            return
        self.guardada = True
        self.poner_etiqueta()
        QMessageBox.information(self, "Guardada", f"Playlist guardada en:\n{destino}\n\n"
                                                  f"Para verla en MusicBee, arrástrala a la lista de playlists.")

    def calcular_bpm(self):
        """Medidas del audio de cada canción (BPM, volumen, silencios; en las cortinas actividad y volumen):
        las guardadas al momento, las nuevas (~0,3 s cada canción, una sola vez) con barra."""
        self.buscar_alternativas()
        try:
            cache = bpm.CacheBpm()
        except Exception:
            return
        pendientes = []          # (fila, índice) de las canciones a las que les falta alguna medida
        for fila, tanda in enumerate(self.tandas):
            for idx, c in tanda.canciones.iterrows():
                medidas = cache.medidas(c["ruta"], c["genre"], tanda.es_cortina, calcular_si_falta=False)
                for nombre, valor in medidas.items():
                    tanda.canciones.loc[idx, nombre] = valor
                if any(cache.guardado(c["ruta"], t)[0] is False for t in
                       ((bpm.ACTIVIDAD, bpm.VOLUMEN) if tanda.es_cortina
                        else (c["genre"], bpm.VOLUMEN, bpm.SILENCIO_INICIO))):
                    pendientes.append((fila, idx))
        if pendientes:
            self.progreso.setMaximum(len(pendientes))
            self.progreso.setFormat("Midiendo el audio (BPM, volumen, silencios)… %v de %m")
            self.progreso.show()
            for n, (fila, idx) in enumerate(pendientes, 1):
                tanda = self.tandas[fila]
                c = tanda.canciones.loc[idx]
                for nombre, valor in cache.medidas(c["ruta"], c["genre"], tanda.es_cortina).items():
                    tanda.canciones.loc[idx, nombre] = valor
                self.progreso.setValue(n)
                QApplication.processEvents()
            self.progreso.hide()
            self.progreso.setFormat("%p%")
        for fila, tanda in enumerate(self.tandas):
            if not tanda.es_cortina:
                valores = [v for v in tanda.canciones["bpm"] if v]
                texto = "" if not valores else (f"{min(valores):.0f}" if min(valores) == max(valores)
                                                else f"{min(valores):.0f}–{max(valores):.0f}")
                self.tabla_tandas.item(fila, 8).setText(texto)
        self.revisar()
        self.mostrar_canciones()

    def rellenar_tandas(self):
        t = self.tabla_tandas
        t.setRowCount(len(self.tandas))
        n_tanda = 0
        for fila, tanda in enumerate(self.tandas):
            es_tanda = not tanda.es_cortina and not tanda.es_cumparsita
            if es_tanda:
                n_tanda += 1
            valores = [str(n_tanda) if es_tanda else "",
                       "Cortina" if tanda.es_cortina else "Final" if tanda.es_cumparsita else tanda.genero.capitalize(),
                       tanda.titulo_orquesta, tanda.subtitulo, str(len(tanda.canciones)),
                       convertir_segundos(tanda.duracion), "", "", ""]
            for col, v in enumerate(valores):
                it = QTableWidgetItem(v)
                if col == 2 and not tanda.es_cortina:
                    it.setFont(QFont("", -1, QFont.Bold))
                t.setItem(fila, col, it)
        self.revisar()
        if self.tandas:
            t.selectRow(0)

    def revisar(self):
        """Revisa la playlist, colorea las filas con problemas y llena la lista de la revisión."""
        d = self.datos()
        self.avisos = revisar(self.tandas, self.faltan, d["inicio"], d["fin"], patron=self.patron.currentData(),
                              minutos_sin_milonga=self.sin_milonga.value(), historial=self.historial,
                              alternativas=self.alternativas)
        por_fila = {}
        for a in self.avisos:
            if a.fila is not None:
                por_fila.setdefault(a.fila, []).append(a)
        colores = {ERROR: QColor("#ffcdd2"), AVISO: QColor("#fff3c4")}
        horas = horas_de_inicio(self.tandas, d["inicio"])
        for fila, tanda in enumerate(self.tandas):
            suyos = por_fila.get(fila, [])
            niveles = {a.nivel for a in suyos}
            nivel = ERROR if ERROR in niveles else AVISO if AVISO in niveles else None
            color = colores.get(nivel, QColor("#eeeeee") if tanda.es_cortina else QColor("#ffffff"))
            self.tabla_tandas.item(fila, 6).setText(horas[fila])
            car = None if tanda.es_cumparsita else caracter.de_tanda(tanda)
            self.tabla_tandas.item(fila, 7).setText(car.texto if car else "")
            for col in range(self.tabla_tandas.columnCount()):
                it = self.tabla_tandas.item(fila, col)
                it.setBackground(color)
                it.setToolTip("\n".join(a.texto for a in suyos) if suyos else it.text())
            if car and not suyos:
                self.tabla_tandas.item(fila, 7).setToolTip(
                    f"{car.texto}, dificultad {car.dificultad}" + (f"\n{car.notas}" if car.notas else ""))

        self.lista_revision.clear()
        iconos = {ERROR: "❌", AVISO: "⚠", "info": "ℹ"}
        for a in self.avisos:
            item = QListWidgetItem(f"{iconos[a.nivel]}  {a.texto}")
            item.setData(Qt.UserRole, a.fila)
            if a.nivel in colores:
                item.setBackground(colores[a.nivel])
            self.lista_revision.addItem(item)
        errores = sum(a.nivel == ERROR for a in self.avisos)
        avisos = sum(a.nivel == AVISO for a in self.avisos)
        if not self.avisos:
            self.lista_revision.addItem("✔  Todo bien")
        self.titulo_revision.setText(f"<b>Revisión</b> — {errores} error(es), {avisos} aviso(s)"
                                     + ("" if errores or avisos else " ✔"))

        self.pintar_curva(d)

        reales = [x for x in self.tandas if not x.es_cortina]
        musica = sum(x.duracion for x in reales)
        texto = (f"{len(reales)} tandas, {len(self.tandas) - len(reales)} cortinas — música: "
                 f"{convertir_segundos(musica, 'x minutos y x segundos')}, estimado con cortinas: "
                 f"{convertir_segundos(musica + max(len(reales) - 1, 0) * 60, 'x minutos y x segundos')}")
        if errores:
            texto += f" — <span style='background:#ffcdd2'>&nbsp;{errores} error(es): mira la revisión&nbsp;</span>"
        self.resumen.setText(texto)

    def pintar_curva(self, d):
        horas = horas_de_inicio(self.tandas, d["inicio"])
        empieza = segundos_de_inicio(self.tandas)
        fin_musica = empieza[-1] + (self.tandas[-1].duracion if self.tandas else 0)
        zona_final = fin_musica - self.sin_milonga.value() * 60 if self.sin_milonga.value() else None
        barras, inicio_final = [], None
        for fila, tanda in enumerate(self.tandas):
            if tanda.es_cortina or tanda.es_cumparsita:
                continue
            if zona_final is not None and inicio_final is None and empieza[fila] >= zona_final:
                inicio_final = len(barras)
            barras.append({"fila": fila, "numero": len(barras) + 1, "genero": bpm.tipo(tanda.genero),
                           "energia": energia(tanda, caracter.de_tanda(tanda)), "bpm": bpm_tanda(tanda),
                           "hora": horas[fila], "titulo": f"{tanda.titulo_orquesta} · {tanda.subtitulo}"})
        self.curva.poner(barras, inicio_final)

    def ir_a_fila(self, fila):
        self.tabla_tandas.selectRow(fila)
        self.tabla_tandas.scrollToItem(self.tabla_tandas.item(fila, 0))

    def ir_a_aviso(self, item):
        fila = item.data(Qt.UserRole)
        if fila is not None:
            self.tabla_tandas.selectRow(fila)
            self.tabla_tandas.scrollToItem(self.tabla_tandas.item(fila, 0))

    def mostrar_canciones(self):
        filas = self.tabla_tandas.selectionModel().selectedRows()
        if not filas:
            return
        tanda = self.tandas[filas[0].row()]
        df = tanda.canciones
        volumenes = [v for v in df.get("volumen", []) if v is not None and v == v]
        medio = sorted(volumenes)[len(volumenes) // 2] if volumenes else None
        self.tabla_canciones.setRowCount(len(df))
        for i, (_, c) in enumerate(df.iterrows()):
            volumen = c.get("volumen")
            if volumen is None or volumen != volumen:
                texto_volumen = ""
            elif tanda.es_cortina or medio is None:
                texto_volumen = f"{volumen:.0f} dB"
            else:
                texto_volumen = f"{volumen:.0f} dB ({volumen - medio:+.0f})"
            for col, v in enumerate([c["title"], c["artist"], c["ano"], compositor_para_diapo(c["composer"]),
                                     convertir_segundos(c["duration"]),
                                     _texto_actividad(c.get("actividad")) if tanda.es_cortina
                                     else _texto_bpm(c.get("bpm")), texto_volumen]):
                it = QTableWidgetItem(str(v))
                it.setToolTip(f"{v}\n\n{c['ruta']}")
                self.tabla_canciones.setItem(i, col, it)

    def crear(self):
        d = self.datos()
        if not d["milonga"]:
            QMessageBox.warning(self, "Falta el nombre", "Escribe el nombre de la milonga.")
            return
        if self.cambios and not self.guardada:
            r = QMessageBox.question(self, "Cambios sin guardar",
                                     "La playlist tiene cambios sin guardar. ¿Guardarla antes de crear la presentación?",
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Yes:
                self.guardar_playlist()
        errores =[a.texto for a in self.avisos if a.nivel == ERROR]
        if errores and QMessageBox.question(
                self, "La playlist tiene errores",
                f"La revisión encontró {len(errores)} error(es):\n\n" + "\n".join(errores[:10])
                + ("\n…" if len(errores) > 10 else "") + "\n\n¿Crear la presentación igualmente?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        for clave, valor in (("diapos_nombre", d["milonga"]), ("diapos_inicio", d["inicio"]), ("diapos_fin", d["fin"])):
            self.settings.setValue(clave, valor)
        destino, _ = QFileDialog.getSaveFileName(
            self, "Guardar presentación", os.path.join(presentations_start_path, nombre_archivo(d)),
            "PowerPoint (*.pptx)")
        if not destino:
            return
        self.progreso.setMaximum(len(self.tandas))
        self.progreso.show()
        self.boton_crear.setEnabled(False)

        def progreso(hechas, total):
            self.progreso.setValue(hechas)
            QApplication.processEvents()

        try:
            crear_presentacion(self.tandas, d, destino, progreso)
        except PermissionError:
            QMessageBox.critical(self, "No se pudo guardar",
                                 "El archivo está abierto en PowerPoint. Ciérralo y vuelve a intentarlo.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear la presentación:\n{e}")
            return
        finally:
            self.progreso.hide()
            self.boton_crear.setEnabled(True)
        if QMessageBox.question(self, "Presentación creada", f"Guardada en:\n{destino}\n\n¿Abrirla ahora?") \
                == QMessageBox.Yes:
            os.startfile(destino)
