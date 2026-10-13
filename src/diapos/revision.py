"""
Revisión de la playlist antes de crear las diapos (sin interfaz).

    avisos = revisar(tandas, faltan, inicio="21:00", fin="00:00")

Cada Aviso dice su gravedad, el texto y a qué fila de `tandas` se refiere (None = a toda la playlist):
  ERROR  algo que en la milonga falla (no está en el portátil, falta una cortina, tema repetido…)
  AVISO  algo que rompe las reglas de las tandas (cantores mezclados, años lejanos, orquesta repetida cerca…)
  INFO   para tenerlo en cuenta (duración total, Pugliese pronto, pocas instrumentales…)
"""
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from unidecode import unidecode

from src.config.config import carpeta_portatil
from src.diapos import caracter
from src.diapos.generador import compositor_para_diapo, es_cumparsita
from src.utils.buscar_artista import normalizar_nombre

ERROR, AVISO, INFO = "error", "aviso", "info"

TEMAS_POR_TANDA = (3, 4)
MAX_ANOS_EN_TANDA = 8          # más años de diferencia dentro de una tanda -> aviso
DISTANCIA_ORQUESTA = 4         # la misma orquesta / cantor a menos de estas tandas -> aviso
SEGUNDOS_CORTINA = 60          # lo mismo que estima la ventana de diapos
MINUTOS_SIN_MILONGA = 40       # al final de la noche no se ponen milongas

# Patrones de bloques: tandas de tango entre cada vals o milonga (el ciclo se repite)
PATRONES = {
    "2-1-2-1": ((2,), "T-T-V-T-T-M"),
    "3-1-3-1": ((3,), "T-T-T-V-T-T-T-M"),
    "4-1-4-1": ((4,), "T-T-T-T-V-T-T-T-T-M"),
    "2-1-1-1": ((2, 1), "T-T-V-T-M"),
}
AUTO, LIBRE = "auto", "libre"
# Si la orquesta no está en la tabla de carácter: las que exigen mucho a la pista
DIFICILES = {"pugliese", "salgan", "piazzolla", "gobbi", "basso"}
SEGUIDAS_IGUAL_ENERGIA = 3     # tantas tandas seguidas muy tranquilas o muy enérgicas -> consejo
TOLERANCIA_BPM = 0.10          # un tema más de un 10 % más rápido o lento que el resto de su tanda -> aviso
BAJADA_BPM = 0.05              # la tanda "baja" si el último tema es un 5 % más lento que el primero
REFERENCIA_BPM = {"tango": 120, "vals": 205, "milonga": 100}   # para comparar la energía de tandas
_EN_NUBE = 0x400000 | 0x1000   # Dropbox "solo en la nube" (como en la biblioteca)


@dataclass
class Aviso:
    nivel: str
    texto: str
    fila: int = None           # índice en la lista de tandas (incluidas las cortinas)


def _genero_corto(genero):
    if "vals" in genero:
        return "vals"
    if "milonga" in genero:
        return "milonga"
    return "tango"


def _personas(cantor):
    """'Lita Morales y Horacio Lagos' -> {'lita morales', 'horacio lagos'}."""
    return {normalizar_nombre(p) for p in re.split(r"\s+y\s+|,\s*|\s*/\s*", cantor or "") if p.strip()}


def _titulo(t):
    t = re.sub(r"\(.*?\)", "", unidecode(str(t or "")).lower())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _dentro_de(ruta, carpeta):
    ruta, carpeta = os.path.normcase(os.path.abspath(ruta)), os.path.normcase(os.path.abspath(carpeta))
    return ruta.startswith(carpeta.rstrip("\\/") + os.sep)


def _en_nube(ruta):
    try:
        return bool(getattr(os.stat(ruta), "st_file_attributes", 0) & _EN_NUBE)
    except OSError:
        return False


def _bloques_orquesta(df):
    """Trozos seguidos de la misma orquesta: [(orquesta, n_temas), …]."""
    bloques = []
    for orq in df["artist1"]:
        if bloques and normalizar_nombre(bloques[-1][0]) == normalizar_nombre(orq):
            bloques[-1][1] += 1
        else:
            bloques.append([orq, 1])
    return bloques


def minutos(segundos):
    return int(round(segundos / 60))


def horas_de_inicio(tandas, inicio):
    """Hora a la que empieza cada fila ('21:37'), estimando SEGUNDOS_CORTINA por cortina."""
    try:
        t = datetime.strptime(inicio, "%H:%M")
    except (TypeError, ValueError):
        return [""] * len(tandas)
    horas = []
    for tanda in tandas:
        horas.append(t.strftime("%H:%M"))
        t += timedelta(seconds=SEGUNDOS_CORTINA * len(tanda.canciones) if tanda.es_cortina else tanda.duracion)
    return horas


def segundos_de_inicio(tandas):
    """Segundos desde el principio a los que empieza cada fila."""
    t, salida = 0.0, []
    for tanda in tandas:
        salida.append(t)
        t += SEGUNDOS_CORTINA * len(tanda.canciones) if tanda.es_cortina else tanda.duracion
    return salida


def _dificultad(tanda, car):
    """1 fácil … 3 exige mucho: de la tabla de carácter o, si no está, de DIFICILES."""
    if car is not None:
        return car.dificultad
    return 3 if set(normalizar_nombre(tanda.orquesta).split()) & DIFICILES else 1


def bpms(tanda):
    """BPM de cada canción de la tanda (None si no se calculó)."""
    if "bpm" not in tanda.canciones:
        return [None] * len(tanda.canciones)
    return [float(v) if v is not None and v == v and v else None for v in tanda.canciones["bpm"]]


def bpm_tanda(tanda):
    valores = sorted(v for v in bpms(tanda) if v)
    return valores[len(valores) // 2] if valores else None


def energia(tanda, car):
    """Energía para comparar tandas: la de la tabla de carácter, afinada con el BPM (±0,5 cada 10 %)."""
    if car is None:
        return None
    valor = float(car.energia)
    medio = bpm_tanda(tanda)
    if medio:
        valor += max(-1.0, min(1.0, (medio / REFERENCIA_BPM[_genero_corto(tanda.genero)] - 1) * 5))
    return valor


def _tramos(generos):
    """[(filas de tango, fila de la alternativa, 'vals'|'milonga'), …] y las filas de tango del final."""
    tramos, tangos = [], []
    for fila, g in generos:
        if g == "tango":
            tangos.append(fila)
        else:
            tramos.append((tangos, fila, g))
            tangos = []
    return tramos, tangos


def _desajustes(tramos, ciclo, desfase):
    """Tramos cuyo número de tangos no es el del patrón: [(k, esperado)]. El primero puede ser más largo."""
    errores = []
    for k, (tangos, _, _) in enumerate(tramos):
        esperado = ciclo[(k + desfase) % len(ciclo)]
        if not tangos or (k == 0 and len(tangos) >= esperado):
            continue
        if len(tangos) != esperado:
            errores.append((k, esperado))
    return errores


def detectar_patron(generos):
    """El patrón de PATRONES que mejor encaja: (nombre, desfase) o None si hay pocas tandas o no sigue ninguno."""
    tramos, _ = _tramos(generos)
    if len(tramos) < 2:
        return None
    mejor = None
    for nombre, (ciclo, _) in PATRONES.items():
        for desfase in range(len(ciclo)):
            fallos = len(_desajustes(tramos, ciclo, desfase))
            if mejor is None or fallos < mejor[0]:
                mejor = (fallos, nombre, desfase)
    fallos, nombre, desfase = mejor
    return (nombre, desfase) if fallos <= len(tramos) // 2 else None


def dibujo_noche(generos):
    """'TTV TTM TTV TT' (un grupo por cada vals o milonga)."""
    letras = "".join({"tango": "T", "vals": "V", "milonga": "M"}[g] for _, g in generos)
    return re.sub(r"([VM])", r"\1 ", letras).strip()


def _revisar_patron(generos, patron, nombre, cuando, en_zona_final):
    avisos = []
    tramos, cola = _tramos(generos)
    if patron == LIBRE or not generos:
        return avisos
    if patron == AUTO:
        detectado = detectar_patron(generos)
        if detectado is None:
            if len(tramos) >= 2:
                avisos.append(Aviso(INFO, f"No sigues un patrón fijo de bloques ({dibujo_noche(generos)}): "
                                          f"a la pista le ayuda saber qué viene"))
            return avisos
        patron, desfase = detectado
        como = "detectado"
    else:
        desfase = min(range(len(PATRONES[patron][0])),
                      key=lambda d: len(_desajustes(tramos, PATRONES[patron][0], d)))
        como = "elegido"
    ciclo, dibujo = PATRONES[patron]
    avisos.append(Aviso(INFO, f"Patrón {como}: {patron} ({dibujo}). Tu noche: {dibujo_noche(generos)}"))

    def toca(k):
        if k > 0:
            return "milonga" if tramos[k - 1][2] == "vals" else "vals"
        return "vals o milonga"

    for k, esperado in _desajustes(tramos, ciclo, desfase):
        tangos, alt, g = tramos[k]
        if len(tangos) < esperado:
            if not en_zona_final(alt):
                avisos.append(Aviso(AVISO, f"{nombre(alt)}: {g}{cuando(alt)} tras solo {len(tangos)} tanda(s) de "
                                           f"tango; en tu patrón {patron} son {esperado}", alt))
        else:
            fila = tangos[esperado]
            if not en_zona_final(fila):
                avisos.append(Aviso(AVISO, f"{nombre(fila)}{cuando(fila)}: en tu patrón {patron} aquí tocaría "
                                           f"{toca(k)} (van {len(tangos)} tandas de tango seguidas)", fila))
    if tramos and len(tramos[0][0]) > ciclo[desfase % len(ciclo)]:
        avisos.append(Aviso(INFO, f"Empiezas con {len(tramos[0][0])} tandas de tango antes del primer "
                                  f"{tramos[0][2]}: está bien para calentar la pista", tramos[0][1]))
    for k in range(1, len(tramos)):
        tangos, alt, g = tramos[k]
        if tangos and g == tramos[k - 1][2]:
            avisos.append(Aviso(AVISO, f"{nombre(alt)}: otra vez {g}{cuando(alt)}; la anterior ({nombre(tramos[k - 1][1])}) "
                                       f"también lo fue, tocaría {toca(k)}", alt))
    if tramos and cola:
        esperado = ciclo[(len(tramos) + desfase) % len(ciclo)]
        if len(cola) > esperado and not en_zona_final(cola[esperado]):
            avisos.append(Aviso(AVISO, f"{nombre(cola[esperado])}{cuando(cola[esperado])}: en tu patrón {patron} aquí "
                                       f"tocaría {toca(len(tramos))} (van {len(cola)} tandas de tango seguidas)",
                                cola[esperado]))
    return avisos


def revisar(tandas, faltan=(), inicio=None, fin=None, carpeta=carpeta_portatil, patron=AUTO,
            minutos_sin_milonga=MINUTOS_SIN_MILONGA, archivo_caracter=None):
    """patron: AUTO (detectarlo), LIBRE (no mirar) o una clave de PATRONES."""
    avisos = []
    nombre_carpeta = os.path.relpath(carpeta, os.path.dirname(os.path.dirname(carpeta))) if carpeta else ""

    for ruta in faltan:
        avisos.append(Aviso(ERROR, f"No existe el archivo: {ruta}"))

    reales = [(i, t) for i, t in enumerate(tandas) if not t.es_cortina and not t.es_cumparsita]
    numero = {i: n for n, (i, _) in enumerate(reales, 1)}      # fila -> número de tanda

    def nombre(i):
        if i in numero:
            return f"Tanda {numero[i]}"
        return "La Cumparsita" if tandas[i].es_cumparsita else "Cortina"

    # --- Archivos: en el portátil, descargados, una sola vez
    vistas = {}
    for i, t in enumerate(tandas):
        for _, c in t.canciones.iterrows():
            ruta = c["ruta"]
            if carpeta and not _dentro_de(ruta, carpeta):
                avisos.append(Aviso(ERROR, f"{nombre(i)}: «{c['title']}» no está en {nombre_carpeta} "
                                           f"(no estará en el portátil): {ruta}", i))
            elif _en_nube(ruta):
                avisos.append(Aviso(AVISO, f"{nombre(i)}: «{c['title']}» está solo en la nube en este ordenador", i))
            clave = os.path.normcase(ruta)
            if clave in vistas and not t.es_cortina:
                avisos.append(Aviso(ERROR, f"{nombre(i)}: «{c['title']}» ya suena en {nombre(vistas[clave])}", i))
            vistas.setdefault(clave, i)

    # --- Estructura: cortina entre tandas, nada de cortinas dobles
    if tandas and tandas[0].es_cortina:
        avisos.append(Aviso(INFO, "La playlist empieza con una cortina", 0))
    for i, t in enumerate(tandas):
        siguiente = tandas[i + 1] if i + 1 < len(tandas) else None
        if not t.es_cortina and siguiente is not None and not siguiente.es_cortina and not siguiente.es_cumparsita:
            avisos.append(Aviso(ERROR, f"Falta una cortina entre la {nombre(i)} ({t.genero}) y la "
                                       f"{nombre(i + 1)} ({siguiente.genero})", i))
        if t.es_cortina:
            n = len(t.canciones)
            ultima = i == len(tandas) - 1
            if n > 1 and not ultima:
                avisos.append(Aviso(AVISO, f"{n} cortinas seguidas", i))
            elif n > 1 and ultima:
                avisos.append(Aviso(INFO, f"Acaba con {n} cortinas seguidas (¿de reserva?)", i))
            if "cortina" not in t.genero:
                avisos.append(Aviso(AVISO, f"«{t.canciones['title'].iloc[0]}» no tiene género de tango, vals ni "
                                           f"milonga: ¿es una cortina? (género: «{t.genero or 'vacío'}»)", i))

    # --- La Cumparsita: sola y al final (el último baile), nunca dentro de una tanda
    for i, t in enumerate(tandas):
        if t.es_cumparsita:
            c = t.canciones.iloc[0]
            avisos.append(Aviso(INFO, f"Cierre con La Cumparsita ({c['artist1']}, {c['ano'] or 'sin año'})", i))
        elif not t.es_cortina and any(map(es_cumparsita, t.canciones["title"])):
            avisos.append(Aviso(AVISO, f"{nombre(i)}: tiene La Cumparsita; va sola al final de la noche, "
                                       f"como último baile, no dentro de una tanda", i))

    # --- Cada tanda por dentro
    for i, t in reales:
        df = t.canciones
        bloques = _bloques_orquesta(df)
        if len(bloques) > 1 and all(n >= 2 for _, n in bloques):
            avisos.append(Aviso(ERROR, f"{nombre(i)}: parecen {len(bloques)} tandas sin cortina en medio ("
                                       + " · ".join(f"{o}, {n} temas" for o, n in bloques) + ")", i))
        elif not t.misma_orquesta:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: mezcla orquestas: "
                                       + ", ".join(dict.fromkeys(df["artist1"])), i))
        elif len(df) not in TEMAS_POR_TANDA:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: tiene {len(df)} temas", i))
        if not t.genero:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: sin género", i))

        cantores = [c.strip() for c in df["artist2"]]
        con_voz = [c for c in cantores if c]
        if con_voz and len(con_voz) < len(cantores):
            avisos.append(Aviso(AVISO, f"{nombre(i)}: mezcla instrumentales y cantadas", i))
        distintos = list(dict.fromkeys(con_voz))
        if len(distintos) > 1:
            comunes = set.intersection(*(_personas(c) for c in distintos))
            nivel = INFO if comunes else AVISO
            avisos.append(Aviso(nivel, f"{nombre(i)}: cantores distintos: " + " · ".join(distintos), i))

        anos = sorted(int(a) for a in df["ano"] if str(a).isdigit())
        if len(anos) < len(df):
            sin = [c["title"] for _, c in df.iterrows() if not str(c["ano"]).isdigit()]
            avisos.append(Aviso(AVISO, f"{nombre(i)}: sin año: " + ", ".join(sin), i))
        if anos and anos[-1] - anos[0] > MAX_ANOS_EN_TANDA:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: años muy separados ({anos[0]} – {anos[-1]})", i))

        titulos = [_titulo(x) for x in df["title"]]
        if len(set(titulos)) < len(titulos):
            avisos.append(Aviso(ERROR, f"{nombre(i)}: tiene un tema repetido", i))
        if not all(str(a).strip() for a in df["artist"]):
            avisos.append(Aviso(AVISO, f"{nombre(i)}: alguna canción sin artista", i))
        sin_compositor = [c["title"] for _, c in df.iterrows() if not compositor_para_diapo(c["composer"])]
        if sin_compositor:
            avisos.append(Aviso(INFO, f"{nombre(i)}: sin compositor en la diapo: " + ", ".join(sin_compositor), i))

    # --- Entre tandas
    generos = [(i, _genero_corto(t.genero)) for i, t in reales]
    for (i, g1), (j, g2) in zip(generos, generos[1:]):
        if g1 != "tango" and g2 != "tango":
            avisos.append(Aviso(AVISO, f"{nombre(i)} ({g1}) y {nombre(j)} ({g2}) seguidas, sin tango en medio", j))
    if generos and generos[0][1] != "tango":
        avisos.append(Aviso(INFO, f"Empieza con {generos[0][1]}: lo normal es abrir con tango", generos[0][0]))

    # --- Patrón de bloques y final de la noche
    empieza = segundos_de_inicio(tandas)
    fin_musica = sum(SEGUNDOS_CORTINA * len(t.canciones) if t.es_cortina else t.duracion for t in tandas)
    zona_final = fin_musica - minutos_sin_milonga * 60 if minutos_sin_milonga else float("inf")
    horas = horas_de_inicio(tandas, inicio) if inicio else [""] * len(tandas)

    def cuando(i):
        return f" ({horas[i]})" if horas[i] else ""

    avisos += _revisar_patron(generos, patron, nombre, cuando, lambda i: empieza[i] >= zona_final)
    if minutos_sin_milonga:
        for i, g in generos:
            if g == "milonga" and empieza[i] >= zona_final:
                avisos.append(Aviso(AVISO, f"{nombre(i)}: milonga{cuando(i)} en los últimos {minutos_sin_milonga} min; "
                                           f"al final mejor tango o vals, que los cuerpos ya están cansados", i))

    # --- Carácter de cada tanda (data/caracter_orquestas.csv)
    car = {i: caracter.de_tanda(t, archivo_caracter) for i, t in reales}
    dificil = {i: _dificultad(t, car[i]) for i, t in reales}
    if reales and dificil[reales[0][0]] >= 2:
        i, t = reales[0]
        avisos.append(Aviso(INFO, f"Abrir con {t.orquesta} puede costar a quien llega: mejor algo rítmico y fácil "
                                  f"(Canaro años 30, Donato, D'Arienzo, Firpo, OTV…)", i))
    for i, t in reales:
        por_cancion = {}
        for _, c in t.canciones.iterrows():
            ca = caracter.de_cancion(c, archivo_caracter)
            if ca is not None:
                por_cancion.setdefault(ca.caracter, []).append(c["title"])
        if len(por_cancion) > 1:
            avisos.append(Aviso(AVISO, f"{nombre(i)}: mezcla carácter: " + " · ".join(
                f"{caracter.CARACTERES.get(k, k)} ({', '.join(v)})" for k, v in por_cancion.items()), i))
    for nivel_energia, texto in ((lambda e: e <= 2, "tranquilas"), (lambda e: e >= 5, "de mucha energía")):
        racha = []
        for i, _ in reales + [(None, None)]:
            if i is not None and car[i] is not None and nivel_energia(car[i].energia):
                racha.append(i)
                continue
            if len(racha) >= SEGUIDAS_IGUAL_ENERGIA:
                consejo = ("la pista puede dormirse; un D'Arienzo o un Biagi la despierta" if texto == "tranquilas"
                           else "la pista se cansa; un Di Sarli o un Fresedo la calma")
                avisos.append(Aviso(INFO, f"{len(racha)} tandas {texto} seguidas ({nombre(racha[0])} a "
                                          f"{nombre(racha[-1])}): {consejo}", racha[-1]))
            racha = []
    # --- Velocidad y curva dentro de cada tanda (con el BPM calculado del audio)
    for i, t in reales:
        valores = bpms(t)
        conocidos = [v for v in valores if v]
        if len(conocidos) < 2:
            continue
        g = _genero_corto(t.genero)
        nivel = INFO if g == "milonga" else AVISO          # en milonga el BPM es menos fiable
        medio = sorted(conocidos)[len(conocidos) // 2]
        # solo el que más se aparta (si se apartan varios, es que la tanda entera es irregular)
        k = max(range(len(valores)), key=lambda n: abs(valores[n] / medio - 1) if valores[n] else -1)
        v = valores[k]
        if abs(v / medio - 1) > TOLERANCIA_BPM:
            otros = [x for n, x in enumerate(valores) if x and n != k]
            resto = f"{min(otros):.0f}" if min(otros) == max(otros) else f"{min(otros):.0f}–{max(otros):.0f}"
            como = "más rápido" if v > medio else "más lento"
            avisos.append(Aviso(nivel, f"{nombre(i)}: «{t.canciones['title'].iloc[k]}» ({v:.0f} BPM) va bastante "
                                       f"{como} que el resto ({resto})", i))
        baja = valores[0] and valores[-1] and valores[-1] < valores[0] * (1 - BAJADA_BPM)
        if baja and valores[-1] == min(conocidos):
            avisos.append(Aviso(INFO, f"{nombre(i)}: la tanda baja, cierra con el tema más lento "
                                      f"(«{t.canciones['title'].iloc[-1]}», {valores[-1]:.0f} BPM); "
                                      f"suele funcionar mejor que suba o se mantenga", i))

    # --- Energía en cada bloque: de menos a más, y la milonga por encima del vals
    ener = {i: energia(t, car[i]) for i, t in reales}
    tramos, cola = _tramos(generos)
    for tangos in [tr[0] for tr in tramos] + [cola]:
        if len(tangos) < 2 or ener[tangos[0]] is None or ener[tangos[-1]] is None:
            continue
        if ener[tangos[-1]] < ener[tangos[0]] - 0.5 and not any(empieza[x] >= zona_final for x in tangos):
            avisos.append(Aviso(INFO, f"{nombre(tangos[-1])}: el bloque de tangos baja de energía "
                                      f"({nombre(tangos[0])} {ener[tangos[0]]:.1f} → {ener[tangos[-1]]:.1f}); "
                                      f"suele ir de menos a más", tangos[-1]))
    for (_, vals, g1), (_, milonga, g2) in zip(tramos, tramos[1:]):
        if g1 == "vals" and g2 == "milonga" and ener[vals] is not None and ener[milonga] is not None:
            if ener[milonga] < ener[vals] - 0.5:
                avisos.append(Aviso(INFO, f"{nombre(milonga)}: esta milonga tiene menos energía ({ener[milonga]:.1f}) "
                                          f"que el vals de la {nombre(vals)} ({ener[vals]:.1f}); "
                                          f"la milonga suele ser el pico del ciclo", milonga))

    sin_tabla = list(dict.fromkeys(t.orquesta for i, t in reales if car[i] is None and t.orquesta))
    if sin_tabla:
        avisos.append(Aviso(INFO, "Sin carácter en la tabla (puedes añadirlas): " + ", ".join(sin_tabla)))

    for n, (i, t) in enumerate(reales):
        for m in range(n + 1, min(n + DISTANCIA_ORQUESTA, len(reales))):
            j, u = reales[m]
            if t.orquesta and normalizar_nombre(t.orquesta) == normalizar_nombre(u.orquesta):
                avisos.append(Aviso(AVISO, f"{t.orquesta} en la {nombre(i)} y otra vez en la {nombre(j)}", j))
            comunes = set().union(*map(_personas, t.canciones["artist2"])) & \
                      set().union(*map(_personas, u.canciones["artist2"]))
            if comunes and not (t.orquesta and normalizar_nombre(t.orquesta) == normalizar_nombre(u.orquesta)):
                avisos.append(Aviso(AVISO, f"Cantor repetido muy cerca ({', '.join(sorted(comunes)).title()}): "
                                           f"{nombre(i)} y {nombre(j)}", j))

    vistos = {}
    for i, t in reales:
        for titulo, original in zip(map(_titulo, t.canciones["title"]), t.canciones["title"]):
            if titulo in vistos and vistos[titulo] != i:
                avisos.append(Aviso(AVISO, f"«{original}» suena dos veces: {nombre(vistos[titulo])} y {nombre(i)}", i))
            vistos.setdefault(titulo, i)

    if len(reales) >= 6:
        tercio = reales[:len(reales) // 3]
        for i, t in tercio[1:] if dificil[reales[0][0]] >= 2 else tercio:
            if dificil[i] >= 3:
                avisos.append(Aviso(INFO, f"{t.orquesta} muy pronto ({nombre(i)}): exige mucho a la pista, "
                                          f"mejor en el último tercio", i))
        instrumentales = sum(1 for _, t in reales if not any(c.strip() for c in t.canciones["artist2"]))
        if instrumentales * 3 < len(reales):
            avisos.append(Aviso(INFO, f"Pocas tandas instrumentales: {instrumentales} de {len(reales)}"))

    # --- Duración
    if inicio and fin:
        try:
            h1, h2 = datetime.strptime(inicio, "%H:%M"), datetime.strptime(fin, "%H:%M")
            if h2 <= h1:
                h2 += timedelta(days=1)
            disponible = (h2 - h1).total_seconds()
        except ValueError:
            disponible = None
        if disponible:
            musica = sum(t.duracion for _, t in reales)
            cortinas = sum(len(t.canciones) for t in tandas if t.es_cortina)
            total = musica + cortinas * SEGUNDOS_CORTINA
            diferencia = minutos(total - disponible)
            texto = f"Música {minutos(musica)} min + cortinas ≈ {minutos(total)} min, para {minutos(disponible)} min"
            if diferencia > 0:
                avisos.append(Aviso(AVISO, f"{texto}: sobran {diferencia} min"))
            else:
                avisos.append(Aviso(INFO, f"{texto}: quedan {-diferencia} min libres (charla, cumpleaños…)"))

    orden = {ERROR: 0, AVISO: 1, INFO: 2}
    return sorted(avisos, key=lambda a: (orden[a.nivel], a.fila if a.fila is not None else -1))
