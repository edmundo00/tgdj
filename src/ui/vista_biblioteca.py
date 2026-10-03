"""
Pestaña "Mi biblioteca": toda tu música, con listas inteligentes (nuevas, por revisar…), el árbol de
colecciones y carpetas, búsqueda y "Revisar estas" (las manda a la pestaña de etiquetado).
Todo sale de la biblioteca (src/biblioteca), así que es instantáneo.
"""
import os
import subprocess
import time
from datetime import datetime

import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, QEvent
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem, QLineEdit, QLabel, QPushButton,
    QTableView, QAbstractItemView, QMenu, QMessageBox,
)

from src.utils import no_tocar
from src.utils.buscador import normalizar, interpretar_consulta

ESTADOS = {
    # estado: (texto, color de fondo, explicación)
    "perfecta": ("✔ Perfecta", "#e8f5e9", "Ya tiene la misma información que la base de datos"),
    "preferida": ("★ Sugerida", "#fff8e1", "Hay una grabación clara en la base de datos"),
    "dudosa": ("? Elegir", "#fff3e0", "Varias grabaciones posibles: hay que elegir"),
    "sin_titulo": ("✖ Sin título", "#ffebee", "El artista está en la base de datos, el título no"),
    "sin_artista": ("✖ Sin artista", "#ffebee", "El artista no está en la base de datos"),
    "error": ("⚠ Error", "#ffebee", "No se pudo comparar"),
    "": ("… Por comparar", "#f5f5f5", "Todavía no comparada (la biblioteca lo hace en segundo plano)"),
}
COLUMNAS = [("estado", "Estado"), ("title", "Título"), ("artist", "Artista"), ("year", "Año"), ("genre", "Género"),
            ("composer", "Compositor"), ("album", "Álbum"), ("coleccion", "Colección"), ("carpeta_rel", "Carpeta"),
            ("llegada", "Llegada"), ("ext", "Formato")]
LIMITE_REVISAR = 1500


def normalizar_serie(serie):
    """Como buscador.normalizar pero para 46.000 textos de golpe (unidecode uno a uno tarda 5 s)."""
    return (serie.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii").str.lower()
            .str.replace("'", "", regex=False).str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip())


class ModeloCanciones(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.df = pd.DataFrame()

    def poner(self, df):
        self.beginResetModel()
        self.df = df.reset_index(drop=True)
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

    def data(self, indice, rol=Qt.DisplayRole):
        if not indice.isValid():
            return None
        f = self.df.iloc[indice.row()]
        campo = COLUMNAS[indice.column()][0]
        if rol == Qt.DisplayRole:
            if campo == "estado":
                texto = ESTADOS.get(f["estado"], ESTADOS[""])[0]
                if f["estado"] == "dudosa" and f["motivo_fecha"]:
                    texto += " · fecha CD"
                return texto
            if campo == "llegada":
                return datetime.fromtimestamp(f["visto_primera"]).strftime("%Y-%m-%d") if f["visto_primera"] else ""
            if campo == "ext":
                return str(f["ext"]).lstrip(".").upper()
            return str(f[campo] or "")
        if rol == Qt.BackgroundRole and campo == "estado":
            return QColor(ESTADOS.get(f["estado"], ESTADOS[""])[1])
        if rol == Qt.FontRole and campo == "estado":
            fuente = QFont()
            fuente.setBold(True)
            return fuente
        if rol == Qt.ToolTipRole:
            if campo == "estado":
                partes = [ESTADOS.get(f["estado"], ESTADOS[""])[2]]
                if f["motivo_fecha"]:
                    partes.append(f["motivo_fecha"])
                if f["cambios"] and f["cambios"] not in ("{}", ""):
                    partes.append("Al aplicar la sugerida cambia: " + f["cambios"])
                if f["notocar"]:
                    partes.append("Marcada «No tocar»")
                return "\n".join(partes)
            if campo in ("title", "carpeta_rel"):
                return f["ruta"]
            return str(f[campo] or "") or None
        return None

    def sort(self, columna, orden=Qt.AscendingOrder):
        if self.df.empty or columna < 0:
            return
        campo = COLUMNAS[columna][0]
        clave = {"llegada": "visto_primera"}.get(campo, campo)
        self.beginResetModel()
        if clave == "visto_primera":
            self.df = self.df.sort_values(clave, ascending=orden == Qt.AscendingOrder, kind="stable")
        else:
            self.df = self.df.sort_values(clave, ascending=orden == Qt.AscendingOrder, kind="stable",
                                          key=lambda s: s.astype(str).str.lower())
        self.df = self.df.reset_index(drop=True)
        self.endResetModel()


class VistaBiblioteca(QWidget):
    def __init__(self, parent, biblioteca, reproductor, revisar, actualizar):
        """revisar(df, nombre): manda canciones a la pestaña de etiquetado. actualizar(): buscar cambios."""
        super().__init__(parent)
        self.biblioteca, self.reproductor = biblioteca, reproductor
        self.revisar_cb, self.actualizar_cb = revisar, actualizar
        self.df = pd.DataFrame()
        self.lista_actual = ("lista", "sugeridas")
        self.temporizador = QTimer(self, singleShot=True, interval=250, timeout=self.filtrar)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        division = QSplitter(Qt.Horizontal)

        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.setMinimumWidth(250)
        self.arbol.itemSelectionChanged.connect(self.lista_elegida)
        division.addWidget(self.arbol)

        derecha = QWidget()
        ld = QVBoxLayout(derecha)
        ld.setContentsMargins(4, 0, 0, 0)
        arriba = QHBoxLayout()
        self.titulo = QLabel()
        self.titulo.setStyleSheet("font-size:15px; font-weight:bold;")
        self.caja = QLineEdit()
        self.caja.setClearButtonEnabled(True)
        self.caja.setPlaceholderText("Buscar en esta lista: título, artista, álbum, carpeta, año (1944, 1940-1945)…")
        self.caja.textChanged.connect(lambda: self.temporizador.start())
        arriba.addWidget(self.titulo)
        arriba.addWidget(self.caja, 1)
        ld.addLayout(arriba)

        self.modelo = ModeloCanciones()
        self.tabla = QTableView()
        self.tabla.setModel(self.modelo)
        self.tabla.setSortingEnabled(True)
        self.tabla.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setWordWrap(False)
        self.tabla.verticalHeader().hide()
        self.tabla.verticalHeader().setDefaultSectionSize(24)
        self.tabla.doubleClicked.connect(lambda i: self.revisar(solo=[i.row()]))
        self.tabla.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self.menu)
        self.tabla.installEventFilter(self)
        self.tabla.selectionModel().selectionChanged.connect(lambda *_: self.actualizar_botones())
        from src.ui.columnas import preparar_columnas
        preparar_columnas(self.tabla, "biblioteca", {0: 135, 1: 240, 2: 260, 3: 90, 4: 95, 5: 260, 6: 220,
                                                     7: 120, 8: 260, 9: 90, 10: 60}, siempre_visibles={0, 1})
        ld.addWidget(self.tabla, 1)

        abajo = QHBoxLayout()
        self.info = QLabel()
        self.info.setStyleSheet("color:#555;")
        self.boton_revisar = QPushButton()
        self.boton_revisar.setStyleSheet("QPushButton{font-weight:bold; padding:6px 16px; background:#1565c0; "
                                         "color:white; border-radius:5px;} QPushButton:disabled{background:#bbb;}")
        self.boton_revisar.setToolTip("Cargar estas canciones en la pestaña Revisar para etiquetarlas "
                                      "(las seleccionadas, o toda la lista si no hay selección)")
        self.boton_revisar.clicked.connect(lambda: self.revisar())
        actualizar = QPushButton("⟳  Buscar cambios")
        actualizar.setToolTip("Mirar si hay música nueva o cambiada (también se hace solo al abrir la app)")
        actualizar.clicked.connect(self.actualizar_cb)
        abajo.addWidget(self.info, 1)
        abajo.addWidget(actualizar)
        abajo.addWidget(self.boton_revisar)
        ld.addLayout(abajo)
        division.addWidget(derecha)
        division.setSizes([280, 1400])
        lay.addWidget(division)

    # ------------------------------------------------------------------ datos
    def cargar(self):
        """Lee la biblioteca (rápido) y repinta listas y tabla, manteniendo la lista elegida."""
        df = self.biblioteca.dataframe()
        self.df = self._preparar(df) if not df.empty else df
        self.pintar_arbol()
        self.filtrar()

    def _preparar(self, df, marcadas=None):
        """Columnas que usa la vista (no tocar, carpeta relativa, subcarpeta, año…)."""
        marcadas = no_tocar.claves() if marcadas is None else marcadas
        df["notocar"] = [no_tocar.esta(r, marcadas) for r in df["ruta"]] if marcadas else False
        df["carpeta_rel"] = [c[len(r):].lstrip(os.sep) if c.startswith(r) else c
                             for c, r in zip(df["carpeta"], df["raiz"])]
        for c in ("estado", "motivo_fecha", "cambios", "title", "artist", "album", "year", "genre", "composer"):
            df[c] = df[c].fillna("").astype(str)
        # Subcarpeta dentro de la colección (en MUSICA la primera carpeta ya es la colección)
        df["sub"] = [r.split(os.sep, 1)[1] if r.split(os.sep, 1)[0] == c and os.sep in r else ("" if r == c else r)
                     for r, c in zip(df["carpeta_rel"], df["coleccion"])]
        df["visto_primera"] = df["visto_primera"].fillna(0)
        df["_ano"] = pd.to_numeric(df["year"].str[:4], errors="coerce")
        if "_buscar" in self.df:
            df["_buscar"] = self._texto_busqueda(df)
        return df

    @staticmethod
    def _texto_busqueda(df):
        return normalizar_serie(df["title"] + " | " + df["artist"] + " | " + df["album"] + " | " + df["composer"]
                                + " | " + df["carpeta_rel"])

    def refrescar_rutas(self, rutas):
        """Tras una acción tuya: cambia solo esas filas (rápido) y repinta, sin perder la posición."""
        if self.df.empty:
            self.cargar()
            return
        rutas = list(dict.fromkeys(rutas))
        nuevas = pd.concat([self.biblioteca.dataframe(f"ruta IN ({','.join('?' * len(lote))})", tuple(lote))
                            for lote in (rutas[i:i + 500] for i in range(0, len(rutas), 500))] or [pd.DataFrame()],
                           ignore_index=True)
        resto = self.df[~self.df["ruta"].isin(rutas)]
        if not nuevas.empty:
            nuevas = self._preparar(nuevas)
            resto = pd.concat([resto, nuevas[[c for c in resto.columns if c in nuevas]]], ignore_index=True)
        self.df = resto.sort_values("id").reset_index(drop=True)
        self.repintar()

    def refrescar_no_tocar(self):
        if self.df.empty:
            return
        marcadas = no_tocar.claves()
        self.df["notocar"] = [no_tocar.esta(r, marcadas) for r in self.df["ruta"]] if marcadas else False
        self.repintar()

    def repintar(self):
        """Repinta listas y tabla conservando la selección de lista y la posición de la tabla."""
        barra = self.tabla.verticalScrollBar().value()
        self.pintar_arbol()
        self.filtrar()
        self.tabla.verticalScrollBar().setValue(barra)

    def listas(self):
        """(clave, texto, máscara) de las listas inteligentes."""
        d = self.df
        ahora = time.time()
        anterior = self.biblioteca.inicio_sesion_anterior()
        revisable = ~d["notocar"]
        return {
            "nuevas_sesion": ("Desde la última vez", (d["visto_primera"] >= anterior) if anterior else d["id"] < 0),
            "nuevas_7": ("Últimos 7 días", d["visto_primera"] >= ahora - 7 * 86400),
            "nuevas_30": ("Últimos 30 días", d["visto_primera"] >= ahora - 30 * 86400),
            "sugeridas": ("Sugeridas", (d["estado"] == "preferida") & revisable),
            "elegir": ("Hay que elegir", (d["estado"] == "dudosa") & revisable),
            "fecha_cd": ("· con fecha de CD", (d["estado"] == "dudosa") & (d["motivo_fecha"] != "") & revisable),
            "sin_titulo": ("Título no encontrado", (d["estado"] == "sin_titulo") & revisable),
            "sin_artista": ("Artista no encontrado", (d["estado"] == "sin_artista") & revisable),
            "pendientes": ("Por comparar", d["estado"].isin(["", "error"])),
            "todas": ("Todas", d["id"] >= 0),
            "perfectas": ("Perfectas", d["estado"] == "perfecta"),
            "notocar": ("No tocar", d["notocar"]),
        }

    def pintar_arbol(self):
        self.arbol.blockSignals(True)
        self.arbol.clear()
        if self.df.empty:
            self.arbol.blockSignals(False)
            return
        listas = self.listas()
        self.mascaras = {k: m for k, (_, m) in listas.items()}
        negrita = QFont()
        negrita.setBold(True)
        elegido = None

        def grupo(nombre):
            g = QTreeWidgetItem(self.arbol, [nombre])
            g.setFlags(Qt.ItemIsEnabled)
            g.setFont(0, negrita)
            g.setExpanded(True)
            return g

        for titulo, claves in (("🆕 Nuevas", ("nuevas_sesion", "nuevas_7", "nuevas_30")),
                               ("✎ Por revisar", ("sugeridas", "elegir", "fecha_cd", "sin_titulo", "sin_artista",
                                                  "pendientes")),
                               ("📚 Toda la música", ("todas", "perfectas", "notocar"))):
            g = grupo(titulo)
            for clave in claves:
                texto, mascara = listas[clave]
                it = QTreeWidgetItem(g, [f"{texto}   ({int(mascara.sum()):,})".replace(",", ".")])
                it.setData(0, Qt.UserRole, ("lista", clave))
                if clave == "fecha_cd":
                    it.setForeground(0, QColor("#777"))
                if ("lista", clave) == self.lista_actual:
                    elegido = it

        # Colecciones y carpetas (con lo que hay dentro, subcarpetas incluidas)
        g = grupo("🗂 Colecciones")
        for coleccion, dc in self.df.groupby("coleccion", sort=True):
            it_col = QTreeWidgetItem(g, [f"{coleccion}   ({len(dc):,})".replace(",", ".")])
            it_col.setData(0, Qt.UserRole, ("coleccion", coleccion, ""))
            if ("coleccion", coleccion, "") == self.lista_actual:
                elegido = it_col
            # Subcarpetas dentro de la colección (ruta relativa a la carpeta de la colección)
            cuenta = {}
            for c in dc["sub"]:
                partes = [p for p in c.split(os.sep) if p]
                for i in range(1, len(partes) + 1):
                    clave = os.sep.join(partes[:i])
                    cuenta[clave] = cuenta.get(clave, 0) + 1
            nodos = {"": it_col}
            for clave in sorted(cuenta, key=str.lower):
                padre = nodos.get(os.path.dirname(clave), it_col)
                it = QTreeWidgetItem(padre, [f"{os.path.basename(clave)}   ({cuenta[clave]:,})".replace(",", ".")])
                it.setData(0, Qt.UserRole, ("coleccion", coleccion, clave))
                nodos[clave] = it
                if ("coleccion", coleccion, clave) == self.lista_actual:
                    elegido = it
        g.setExpanded(True)
        for i in range(g.childCount()):
            g.child(i).setExpanded(False)
        self.arbol.blockSignals(False)
        if elegido is not None:
            elegido.setSelected(True)
            self.arbol.scrollToItem(elegido)

    def lista_elegida(self):
        items = self.arbol.selectedItems()
        if items and items[0].data(0, Qt.UserRole):
            self.lista_actual = items[0].data(0, Qt.UserRole)
            self.filtrar()

    def filas_lista(self):
        if self.df.empty:
            return self.df
        tipo = self.lista_actual[0]
        if tipo == "lista":
            mascara = self.mascaras.get(self.lista_actual[1])
            return self.df[mascara] if mascara is not None else self.df.iloc[0:0]
        _, coleccion, sub = self.lista_actual
        d = self.df[self.df["coleccion"] == coleccion]
        if sub:
            d = d[(d["sub"] == sub) | d["sub"].str.startswith(sub + os.sep)]
        return d

    def nombre_lista(self):
        if self.lista_actual[0] == "lista":
            return self.listas()[self.lista_actual[1]][0] if not self.df.empty else ""
        _, coleccion, sub = self.lista_actual
        return f"{coleccion}{(' › ' + sub.replace(os.sep, ' › ')) if sub else ''}"

    def filtrar(self):
        texto = self.caja.text().strip()
        if texto and not self.df.empty and "_buscar" not in self.df:      # se prepara la primera vez que se busca
            self.df["_buscar"] = self._texto_busqueda(self.df)
        d = self.filas_lista()
        if texto and not d.empty:
            palabras, desde, hasta = interpretar_consulta(texto)
            for p in (normalizar(x) for x in palabras):
                if p:
                    d = d[d["_buscar"].str.contains(p, regex=False)]
            if desde is not None:
                d = d[(d["_ano"] >= desde) & (d["_ano"] <= hasta)]
        if self.lista_actual[0] == "lista" and self.lista_actual[1].startswith("nuevas"):
            d = d.sort_values("visto_primera", ascending=False)
        self.modelo.poner(d)
        self.tabla.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)     # lista nueva: sin orden marcado
        self.titulo.setText(self.nombre_lista())
        self.actualizar_botones()

    # ------------------------------------------------------------------ acciones
    def seleccionadas(self):
        return sorted({i.row() for i in self.tabla.selectionModel().selectedRows()})

    def actualizar_botones(self):
        n_lista, n_sel = self.modelo.rowCount(), len(self.seleccionadas())
        n = n_sel or n_lista
        self.boton_revisar.setText(f"✎  Revisar {'las seleccionadas' if n_sel else 'estas'} ({n:,})".replace(",", "."))
        self.boton_revisar.setEnabled(n > 0)
        resumen = f"{n_lista:,} canciones".replace(",", ".")
        if n_sel:
            resumen += f" · {n_sel} seleccionadas"
        if self.biblioteca.actualizando():
            resumen += " · buscando cambios…"
        self.info.setText(resumen + "   (doble clic: revisar esa · Espacio: escuchar · clic derecho: más)")

    def revisar(self, solo=None):
        filas = solo if solo is not None else (self.seleccionadas() or list(range(self.modelo.rowCount())))
        if not filas:
            return
        if len(filas) > LIMITE_REVISAR:
            caja = QMessageBox(self)
            caja.setWindowTitle("Revisar")
            caja.setText(f"Son {len(filas):,} canciones. Cargarlas todas en la tabla puede tardar "
                         f"({len(filas) // 120} s aprox.) y es incómodo de revisar.".replace(",", "."))
            primeras = caja.addButton(f"Las primeras {LIMITE_REVISAR}", QMessageBox.AcceptRole)
            todas = caja.addButton("Todas", QMessageBox.DestructiveRole)
            caja.addButton("Cancelar", QMessageBox.RejectRole)
            caja.exec_()
            if caja.clickedButton() is primeras:
                filas = filas[:LIMITE_REVISAR]
            elif caja.clickedButton() is not todas:
                return
        self.revisar_cb(self.modelo.df.iloc[filas], self.nombre_lista())

    def escuchar(self):
        filas = self.seleccionadas()
        if filas:
            f = self.modelo.fila(filas[0])
            self.reproductor.alternar(("archivo", f["ruta"]), f["ruta"],
                                      f"Tu archivo: {f['title'] or os.path.basename(f['ruta'])} — {f['artist']}")

    def eventFilter(self, objeto, evento):
        if objeto is self.tabla and evento.type() == QEvent.KeyPress:
            if evento.key() == Qt.Key_Space:
                self.escuchar()
                return True
            if evento.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.revisar()
                return True
        return super().eventFilter(objeto, evento)

    def menu(self, pos):
        filas = self.seleccionadas()
        if not filas:
            return
        primera = self.modelo.fila(filas[0])
        m = QMenu(self)
        m.addAction(f"✎ Revisar ({len(filas)})", lambda: self.revisar())
        m.addAction("▶ Escuchar", self.escuchar)
        m.addAction("📂 Abrir carpeta", lambda: subprocess.Popen(["explorer", "/select,", os.path.normpath(primera["ruta"])]))
        m.addSeparator()
        m.addAction(f"Marcar «No tocar» ({len(filas)})", lambda: self.marcar_no_tocar(filas, True))
        m.addAction(f"Quitar «No tocar» ({len(filas)})", lambda: self.marcar_no_tocar(filas, False))
        m.exec_(self.tabla.viewport().mapToGlobal(pos))

    def marcar_no_tocar(self, filas, marcar):
        df = self.modelo.df.iloc[filas]
        if marcar:
            no_tocar.marcar(list(zip(df["ruta"], df["title"])))
        else:
            no_tocar.desmarcar(list(df["ruta"]))
        self.refrescar_no_tocar()
