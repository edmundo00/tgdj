"""
Columnas a tu gusto en cualquier tabla: clic derecho en la cabecera para ocultar/mostrar,
arrastrar el borde para cambiar el ancho. Todo se recuerda (QSettings) entre sesiones.
"""
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtWidgets import QHeaderView, QMenu


def preparar_columnas(tabla, nombre, anchos_por_defecto, siempre_visibles=()):
    """
    tabla: QTableWidget o QTableView ya con sus columnas. nombre: clave para recordar la configuración.
    anchos_por_defecto: {columna: ancho}. siempre_visibles: columnas que no se pueden ocultar.
    """
    settings = QSettings("TangoTags", "TangoTags")
    cabecera = tabla.horizontalHeader()
    modelo = tabla.model()
    n = modelo.columnCount()
    cabecera.setSectionResizeMode(QHeaderView.Interactive)
    cabecera.setStretchLastSection(False)
    cabecera.setMinimumSectionSize(28)

    guardados = settings.value(f"columnas/{nombre}/anchos", {}) or {}
    ocultas = set(int(c) for c in (settings.value(f"columnas/{nombre}/ocultas", []) or []))
    for col in range(n):
        ancho = guardados.get(str(col)) if isinstance(guardados, dict) else None
        tabla.setColumnWidth(col, int(ancho) if ancho else anchos_por_defecto.get(col, 120))
        tabla.setColumnHidden(col, col in ocultas and col not in siempre_visibles)

    # Guardar anchos (agrupando los cambios mientras se arrastra)
    temporizador = QTimer(tabla, singleShot=True, interval=500)

    def guardar():
        settings.setValue(f"columnas/{nombre}/anchos",
                          {str(c): tabla.columnWidth(c) for c in range(n) if not tabla.isColumnHidden(c)})
        settings.setValue(f"columnas/{nombre}/ocultas", [c for c in range(n) if tabla.isColumnHidden(c)])

    temporizador.timeout.connect(guardar)
    cabecera.sectionResized.connect(lambda *_: temporizador.start())

    def menu(pos):
        m = QMenu(tabla)
        m.addSection("Columnas visibles")
        for col in range(n):
            titulo = modelo.headerData(col, Qt.Horizontal, Qt.DisplayRole) or f"Columna {col + 1}"
            accion = m.addAction(str(titulo))
            accion.setCheckable(True)
            accion.setChecked(not tabla.isColumnHidden(col))
            accion.setEnabled(col not in siempre_visibles)
            accion.toggled.connect(lambda visible, c=col: (tabla.setColumnHidden(c, not visible), guardar()))
        m.addSeparator()
        m.addAction("Anchos por defecto", lambda: (
            [tabla.setColumnWidth(c, anchos_por_defecto.get(c, 120)) for c in range(n)], guardar()))
        m.addAction("Mostrar todas", lambda: ([tabla.setColumnHidden(c, False) for c in range(n)], guardar()))
        m.exec_(cabecera.mapToGlobal(pos))

    cabecera.setContextMenuPolicy(Qt.CustomContextMenu)
    cabecera.customContextMenuRequested.connect(menu)
    for col in range(n):
        item = tabla.horizontalHeaderItem(col) if hasattr(tabla, "horizontalHeaderItem") else None
        if item is not None and not item.toolTip():
            item.setToolTip("Clic derecho: ocultar/mostrar columnas · arrastra el borde para cambiar el ancho")
