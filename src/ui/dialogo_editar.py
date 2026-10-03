"""Editar a mano las tags de una canción (para las que no están en la base de datos)."""
import os
import subprocess

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QLabel, QDialogButtonBox, QPushButton, QHBoxLayout,
)

from src.utils.buscar_artista import separar_orquesta_cantor
from src.utils.formato_tags import (
    formatear_artista, formatear_fecha, formatear_estilo, formatear_compositor, separar_compositor_autor,
    formatear_titulo,
)

ESTILOS = ["tango", "tango vals", "tango milonga", "candombe", "foxtrot", "ranchera", "pasodoble", "canción", ""]


class DialogoEditar(QDialog):
    def __init__(self, parent, ruta, actuales, reproductor=None):
        """actuales: {'title','artist','year','genre','composer'} del archivo."""
        super().__init__(parent)
        self.setWindowTitle("Editar tags a mano")
        self.setMinimumWidth(640)
        self.ruta, self.actuales = ruta, actuales
        lay = QVBoxLayout(self)
        cabecera = QLabel(f"<b>{os.path.basename(ruta)}</b><br><span style='color:#777'>{os.path.dirname(ruta)}</span>")
        cabecera.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(cabecera)

        orquesta, cantor = separar_orquesta_cantor(actuales.get("artist", ""))
        musica, letra = separar_compositor_autor(actuales.get("composer", ""))
        form = QFormLayout()
        self.titulo = QLineEdit(actuales.get("title", ""))
        self.orquesta = QLineEdit(orquesta)
        self.cantor = QLineEdit(cantor)
        self.cantor.setPlaceholderText("vacío = instrumental · varios: «A y B»")
        self.fecha = QLineEdit(formatear_fecha(actuales.get("year", "")) or actuales.get("year", ""))
        self.fecha.setPlaceholderText("AAAA-MM-DD, AAAA-MM o AAAA")
        self.estilo = QComboBox()
        self.estilo.setEditable(True)
        self.estilo.addItems(ESTILOS)
        self.estilo.setCurrentText(formatear_estilo(actuales.get("genre", "")))
        self.musica = QLineEdit(musica)
        self.letra = QLineEdit(letra)
        for nombre, campo in (("Título", self.titulo), ("Orquesta", self.orquesta), ("Cantor", self.cantor),
                              ("Fecha de grabación", self.fecha), ("Estilo", self.estilo),
                              ("Música", self.musica), ("Letra", self.letra)):
            form.addRow(nombre + ":", campo)
        lay.addLayout(form)

        self.vista = QLabel()
        self.vista.setWordWrap(True)
        self.vista.setStyleSheet("background:#f5f5f5; border-radius:6px; padding:8px;")
        lay.addWidget(self.vista)
        for campo in (self.titulo, self.orquesta, self.cantor, self.fecha, self.musica, self.letra):
            campo.textChanged.connect(self.actualizar_vista)
        self.estilo.currentTextChanged.connect(self.actualizar_vista)

        botones = QHBoxLayout()
        carpeta = QPushButton("Abrir carpeta")
        carpeta.clicked.connect(lambda: subprocess.Popen(["explorer", "/select,", os.path.normpath(ruta)]))
        botones.addWidget(carpeta)
        if reproductor is not None:
            escuchar = QPushButton("▶ / ■  Escuchar")
            escuchar.clicked.connect(lambda: reproductor.alternar(("archivo", ruta), ruta,
                                                                    f"Tu archivo: {os.path.basename(ruta)}"))
            botones.addWidget(escuchar)
        botones.addStretch(1)
        self.caja = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.caja.button(QDialogButtonBox.Save).setText("Guardar en el archivo")
        self.caja.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.caja.accepted.connect(self.accept)
        self.caja.rejected.connect(self.reject)
        botones.addWidget(self.caja)
        lay.addLayout(botones)
        self.actualizar_vista()

    def nuevas(self):
        return {
            "title": formatear_titulo(self.titulo.text()),
            "artist": formatear_artista(self.orquesta.text(), self.cantor.text()),
            "year": formatear_fecha(self.fecha.text()),
            "genre": formatear_estilo(self.estilo.currentText()),
            "composer": formatear_compositor(self.musica.text(), self.letra.text()),
        }

    def cambios(self):
        """Solo los campos con valor y distintos de lo que ya tiene el archivo."""
        return {k: v for k, v in self.nuevas().items() if v and v != self.actuales.get(k, "")}

    def actualizar_vista(self):
        fecha_mala = bool(self.fecha.text().strip()) and not formatear_fecha(self.fecha.text())
        self.fecha.setStyleSheet("background:#ffcdd2;" if fecha_mala else "")
        cambios = self.cambios()
        filas = "".join(
            f"<tr><td style='color:#777; padding-right:10px'>{k}</td><td>{self.actuales.get(k) or '<i>(vacío)</i>'}</td>"
            f"<td style='padding:0 8px'>→</td><td><b>{v}</b></td></tr>" for k, v in cambios.items())
        texto = ("<b>Fecha no válida</b> (usa AAAA-MM-DD, AAAA-MM o AAAA)<br>" if fecha_mala else "")
        texto += (f"Se escribirá:<table>{filas}</table>" if cambios else "<i>No hay cambios.</i>")
        self.vista.setText(texto)
        self.caja.button(QDialogButtonBox.Save).setEnabled(bool(cambios) and not fecha_mala)
