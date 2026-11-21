"""
Manejar TangoTags SIN ventana en pantalla (para que Claude lo pruebe sin molestar) y SIN escribir nada.

    .venv\\Scripts\\python.exe probar_tangotags.py <pasos…>

Los pasos se hacen en orden:
    --boton "Por sonido"        pulsa un botón o una opción de menú (el texto, sin saltos de línea; vale un trozo)
    --elegir "Edmundo"          la próxima lista para elegir (QInputDialog) coge la opción que contenga ese texto
    --archivo "ruta"            el próximo «abrir archivo/carpeta» devuelve esta ruta
    --pestana "Revisar"         cambia de pestaña
    --solo "texto"              deja en la tabla solo las canciones con ese texto en la ruta o el álbum («a|b» = cualquiera)
    --marcar N                  marca «Usar» solo en las N primeras canciones (desmarca las demás)
    --tabla N                   escribe las N primeras filas de la tabla (y las sugeridas/perfectas)
    --foto salida.png           foto de la ventana entera (para mirarla)
    --esperar S                 deja correr la app S segundos (cosas en segundo plano)
Opciones (en cualquier sitio):
    --escribir                  SÍ escribe tags de verdad al «Aplicar» (sin esto, se simula y no se toca nada)
    --con-biblioteca            arranca también la puesta al día de Mi biblioteca (como al abrir la app)
Mi biblioteca es una copia de la de Edmundo (en %TEMP%\\tangotags_prueba): lo que cambie aquí no le llega.

Los avisos y preguntas salen escritos; las preguntas se contestan «Sí» y las ventanas propias (resumen de
«Aplicar», buscador…) se fotografían en %TEMP%\\_probar_tt_dialogo_N.png y se cierran con «Aceptar».
No suena nada (audio de mentira) ni se abre nada en la pantalla.

Ejemplo: python probar_tangotags.py --elegir Edmundo --boton "Por sonido" --tabla 15 --foto x.png
"""
import os
import sys

sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")   # al final se sale con os._exit
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")  # sin esto, sin letras
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["SDL_AUDIODRIVER"] = "dummy"
AQUI = os.path.dirname(os.path.abspath(__file__))
os.chdir(AQUI)

# Mi biblioteca: una COPIA de la de verdad de Edmundo. Lo que un programa lanzado por Claude escribe o lee en
# AppData va a una carpeta escondida de la app de Claude (Packages\Claude_…\LocalCache), distinta de la suya;
# por \\localhost\C$ se llega a la de verdad. Se copia para no tocarla mientras su TangoTags está abierto.
import shutil  # noqa: E402
_real = os.path.join(r"\\localhost\C$", os.environ["LOCALAPPDATA"][3:], "TangoTags")
_copia = os.path.join(os.environ.get("TEMP", AQUI), "tangotags_prueba", "Local")
os.makedirs(os.path.join(_copia, "TangoTags"), exist_ok=True)
for _n in ("biblioteca.sqlite", "bpm.sqlite"):
    try:
        shutil.copy2(os.path.join(_real, _n), os.path.join(_copia, "TangoTags", _n))
        for _x in ("-wal", "-shm"):
            if os.path.exists(os.path.join(_copia, "TangoTags", _n + _x)):
                os.remove(os.path.join(_copia, "TangoTags", _n + _x))
    except OSError as _e:
        print(f"(sin copia de {_n}: {_e})")
os.environ["LOCALAPPDATA"] = _copia
sys.path.insert(0, AQUI)

import PyQt5.QtCore as _qtcore  # noqa: E402


class _AjustesDePrueba(_qtcore.QSettings):
    """Los ajustes de la prueba van aparte: no se tocan los de Edmundo (filtros, columnas, carpetas)."""
    def __init__(self, *a, **k):
        super().__init__("TangoTags", "TangoTags_prueba")


_qtcore.QSettings = _AjustesDePrueba          # antes de importar la app (hace «from PyQt5.QtCore import QSettings»)
from PyQt5.QtCore import QTimer  # noqa: E402
from PyQt5.QtWidgets import (QApplication, QAction, QDialog, QFileDialog, QInputDialog,  # noqa: E402
                             QMessageBox, QTabWidget)

args = sys.argv[1:]
ESCRIBIR = "--escribir" in args
CON_BIBLIOTECA = "--con-biblioteca" in args
args = [a for a in args if a not in ("--escribir", "--con-biblioteca")]
pasos = []
while args:
    clave = args.pop(0)
    if not clave.startswith("--") or not args:
        sys.exit(f"Paso no entendido: {clave}\n{__doc__}")
    pasos.append((clave[2:], args.pop(0)))

app = QApplication(sys.argv[:1])
app.setStyle("Fusion")
estado = {"elegir": None, "archivo": None, "dialogos": 0}


# ---- respuestas automáticas a las ventanitas -------------------------------------------------------
def _aviso(tipo):
    def f(_padre, titulo, texto, *a, **k):
        print(f"[{tipo}] {titulo}: {texto}")
        return QMessageBox.Yes if tipo == "pregunta" else QMessageBox.Ok
    return staticmethod(f)


QMessageBox.information = _aviso("info")
QMessageBox.warning = _aviso("aviso")
QMessageBox.critical = _aviso("ERROR")
QMessageBox.question = _aviso("pregunta")


def _elegir(_padre, titulo, texto, opciones, *a, **k):
    quiero = estado["elegir"]
    elegida = next((o for o in opciones if quiero and quiero.lower() in o.lower()), opciones[0] if opciones else "")
    print(f"[elegir] {titulo}: {texto!r}\n         opciones: {opciones}\n         → {elegida}")
    estado["elegir"] = None
    return elegida, True


QInputDialog.getItem = staticmethod(_elegir)
QInputDialog.getText = staticmethod(lambda *a, **k: (estado.pop("archivo", "") or "", True))


def _archivo(*a, **k):
    r = estado["archivo"]
    print(f"[abrir] → {r}")
    return r


QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (_archivo(), ""))
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([_archivo()] if estado["archivo"] else [], ""))
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: _archivo() or "")

_exec_original = QDialog.exec_


def _exec(self):
    """Ventanas propias (resumen de Aplicar, buscador…): foto y «Aceptar»."""
    if isinstance(self, QMessageBox):
        print(f"[mensaje] {self.windowTitle()}: {self.text()} {self.informativeText()}")
        return QMessageBox.Ok
    estado["dialogos"] += 1
    ruta = os.path.join(os.environ.get("TEMP", AQUI), f"_probar_tt_dialogo_{estado['dialogos']}.png")
    self.resize(max(self.width(), 900), max(self.height(), 500))
    self.show()
    app.processEvents()
    self.grab().save(ruta)
    print(f"[ventana] «{self.windowTitle()}» → foto {ruta} → Aceptar")
    self.hide()
    self.accept()
    return QDialog.Accepted


QDialog.exec_ = _exec
QDialog.exec = _exec

# ---- nada se escribe sin --escribir ------------------------------------------------------------------
import src.utils.utils as utils  # noqa: E402
from src.utils import historial  # noqa: E402

if not ESCRIBIR:
    def _no_escribir(ruta, valores, borrar_vacios=False):
        print(f"[simulado, NO escrito] {os.path.basename(ruta)}: {valores}")
        return True
    utils.escribir_tags = _no_escribir
    historial.guardar_backup = lambda *a, **k: "(copia simulada)"

# ---- arrancar la app como tangotags.py ---------------------------------------------------------------
from src.config.config import DB_CSV_PATH  # noqa: E402
from src.config.database import Database  # noqa: E402
import src.ui.tango_tags_qt_ventana as V  # noqa: E402

Database().load_data(DB_CSV_PATH)
if not CON_BIBLIOTECA:
    V.tango_tags_qt_ventana.iniciar_biblioteca = lambda self: self.vista_biblioteca.cargar()
w = V.tango_tags_qt_ventana()
w.resize(1700, 900)
w.show()
w.iniciar_biblioteca()
app.processEvents()
print(f"TangoTags abierto (oculto). Escribir tags: {'SÍ' if ESCRIBIR else 'no (simulado)'}")


def esperar(seg):
    fin = {"ya": False}
    QTimer.singleShot(int(seg * 1000), lambda: fin.update(ya=True))
    while not fin["ya"]:
        app.processEvents()


def texto_accion(a):
    return " ".join(a.text().replace("&", "").split())


def pulsar(nombre):
    acciones = [a for a in w.findChildren(QAction) if a.text()]
    exacta = [a for a in acciones if texto_accion(a).lower() == nombre.lower()]
    trozo = [a for a in acciones if nombre.lower() in texto_accion(a).lower()]
    elegidas = exacta or trozo
    if not elegidas:
        print(f"[botón] No hay «{nombre}». Hay: {sorted({texto_accion(a) for a in acciones})}")
        return
    print(f"[botón] {texto_accion(elegidas[0])}")
    elegidas[0].trigger()
    app.processEvents()


def tabla(n):
    t = w.tabla
    print(f"[tabla] {w.statusBar().currentMessage()}")
    if not t.isVisible():
        print("        (tabla oculta: " + w.mensaje_inicial.text()[:200] + ")")
        return
    cab = [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]
    for f in range(min(n, t.rowCount())):
        celdas = []
        for c, nombre in enumerate(cab):
            it = t.item(f, c)
            if it is None or nombre.startswith("▶"):
                continue
            txt = it.text()
            if nombre == "Usar":
                txt = "☑" if it.checkState() else "☐"
            if txt:
                celdas.append(f"{nombre}={txt}")
        print(f"  {f + 1:>3}. " + " | ".join(celdas))


def marcar(n):
    vistos = 0
    for a in w.archivos:
        if vistos < n and a.categoria != "perfecta" and not w.coincidencias(a).empty:
            a.seleccion = 0 if a.seleccion is None else a.seleccion
            vistos += 1
        else:
            a.seleccion = None
    w.rellenar_tabla()
    print(f"[marcar] {vistos} canciones marcadas en «Usar»")


for clave, valor in pasos:
    if clave == "boton":
        pulsar(valor)
    elif clave == "elegir":
        estado["elegir"] = valor
    elif clave == "archivo":
        estado["archivo"] = valor
    elif clave == "pestana":
        tabs = w.findChild(QTabWidget)
        for i in range(tabs.count()):
            if valor.lower() in tabs.tabText(i).lower():
                tabs.setCurrentIndex(i)
        app.processEvents()
    elif clave == "solo":
        # deja en la tabla solo las canciones cuya ruta o álbum contienen el texto
        textos = [t.lower() for t in valor.split("|")]      # varios: «a|b|c» (vale cualquiera)
        w.archivos = [a for a in w.archivos if any(t in a.ruta_archivo.lower()
                      or t in str(getattr(a.tags, "album", "") or "").lower() for t in textos)]
        w.actualizar_contadores()
        w.rellenar_tabla()
        print(f"[solo] «{valor}»: quedan {len(w.archivos)} canciones "
              f"({sum(a.seleccion is not None for a in w.archivos)} marcadas)")
    elif clave == "marcar":
        marcar(int(valor))
    elif clave == "tabla":
        tabla(int(valor))
    elif clave == "foto":
        app.processEvents()
        w.grab().save(valor)
        print(f"[foto] {valor}")
        # ventanas aparte abiertas (Duplicados, Estado, diapos…): una foto más cada una
        otras = [x for x in app.topLevelWidgets() if x.isVisible() and x is not w and x.width() > 200]
        for k, x in enumerate(otras, 1):
            ruta = os.path.splitext(valor)[0] + f"_ventana{k}.png"
            x.grab().save(ruta)
            print(f"[foto] «{x.windowTitle()}» → {ruta}")
    elif clave == "esperar":
        esperar(float(valor))
    else:
        print(f"Paso desconocido: --{clave}")
print("Fin.")
os._exit(0)
