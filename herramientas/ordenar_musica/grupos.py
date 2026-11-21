"""
Fase 2 de PLAN_ORDENAR_MUSICA.md: grupos de archivos que SUENAN IGUAL (copias de la misma grabación),
con las huellas de huellas_todas.py. No mira tags ni carpetas.

    python grupos.py [--muestra 8] [--votos 12] [--parte 0]

Cómo: de cada huella se hacen «tríos» (dos parejas que salen del mismo pico) y se queda 1 de cada --muestra
(los mismos en todos los archivos, por su valor); se ordenan y cada pareja de archivos que comparte trío vota
por (A, B, desfase). Dos copias de la misma grabación suman votos con el MISMO desfase; distintas, 2–5 como mucho.
Igual = votos ≥ --votos Y votos ≥ --parte × (códigos del más corto). Un trozo cortado cuenta como igual.

Escribe en huellas.sqlite: tabla `parejas` (a, b, votos, parte, desfase en s) y `grupos` (rel, grupo).
Informe: _GRUPOS.txt (aquí al lado).
"""
import argparse
import os
import sqlite3
import time

import numpy as np

from huellas_todas import BD, MUSICA, desempaquetar, AQUI

MAX_CUBO = 40          # un código que sale en más entradas que esto es demasiado común: no vota
SEG_COL = 256 / 8000   # segundos por columna de la huella


def cargar(muestra):
    con = sqlite3.connect(BD)
    filas = con.execute("SELECT rel, bytes, duracion, n, codigos FROM huellas WHERE error='' AND n>0").fetchall()
    rels, codigos, archivos, tiempos, cuantos = [], [], [], [], []
    for i, (rel, _b, _d, n, blob) in enumerate(filas):
        c, t = desempaquetar(blob, n)
        # Tríos: dos parejas seguidas que salen del mismo pico (mismo instante) → clave de 48 bits.
        # Con 66.000 archivos, las parejas solas (24 bits) se repetían demasiado y casi no votaban.
        mismo = t[1:] == t[:-1]
        c = (c[:-1].astype(np.uint64) << np.uint64(24)) | c[1:].astype(np.uint64)
        c, t = c[mismo], t[:-1][mismo]
        sel = ((c * np.uint64(0x9E3779B97F4A7C15)) >> np.uint64(40)) % np.uint64(muestra) == 0  # mismos en todos
        c, t = c[sel], t[sel]
        # cada código una vez por instante (las repeticiones exactas no aportan)
        rels.append(rel)
        codigos.append(c)
        tiempos.append(t)
        archivos.append(np.full(len(c), i, np.uint32))
        cuantos.append(len(c))
    return (rels, np.concatenate(codigos), np.concatenate(archivos), np.concatenate(tiempos).astype(np.int32),
            np.array(cuantos), filas)


def votar(cod, arch, t, trozos=16):
    """dict (a, b) -> (votos, desfase) sumando los votos de cada desfase con sus vecinos (±1 columna·2)."""
    orden = np.lexsort((arch, cod))
    cod, arch, t = cod[orden], arch[orden], t[orden]
    # quitar códigos demasiado comunes
    cambio = np.flatnonzero(np.diff(cod)) + 1
    inicio = np.concatenate(([0], cambio))
    tam = np.diff(np.concatenate((inicio, [len(cod)])))
    buenos = np.repeat(tam <= MAX_CUBO, tam)
    cod, arch, t = cod[buenos], arch[buenos], t[buenos]
    claves_tot, votos_tot = [], []
    limites = np.linspace(0, len(cod), trozos + 1).astype(int)
    for k in range(trozos):
        a0, a1 = limites[k], limites[k + 1]
        # no partir un código entre dos trozos
        while a0 > 0 and a0 < len(cod) and cod[a0] == cod[a0 - 1]:
            a0 += 1
        while a1 < len(cod) and cod[a1] == cod[a1 - 1]:
            a1 += 1
        c, a, tt = cod[a0:a1], arch[a0:a1], t[a0:a1]
        claves = []
        for s in range(1, MAX_CUBO):
            m = c[:-s] == c[s:]
            if not m.any():
                break
            i = np.flatnonzero(m)
            x, y = a[i].astype(np.int64), a[i + s].astype(np.int64)
            d = tt[i + s].astype(np.int64) - tt[i]
            otro = x != y
            x, y, d = x[otro], y[otro], d[otro]
            # siempre a < b (ya vienen ordenados por archivo dentro del código)
            claves.append((x << 36) | (y << 18) | ((d // 2) + 131072))
        if not claves:
            continue
        u, n = np.unique(np.concatenate(claves), return_counts=True)
        quedan = n >= 2
        claves_tot.append(u[quedan])
        votos_tot.append(n[quedan])
    u, inv = np.unique(np.concatenate(claves_tot), return_inverse=True)
    votos = np.bincount(inv, weights=np.concatenate(votos_tot)).astype(np.int64)
    par = u >> 18
    d = (u & 0x3FFFF).astype(np.int64)
    # desfase vecino: sumar d-1 y d+1 de la misma pareja
    resultado = {}
    vecino = {}
    for p, dd, v in zip(par.tolist(), d.tolist(), votos.tolist()):
        vecino[(p, dd)] = v
    for (p, dd), v in vecino.items():
        tot = v + vecino.get((p, dd - 1), 0) + vecino.get((p, dd + 1), 0)
        if tot > resultado.get(p, (0, 0))[0]:
            resultado[p] = (tot, dd)
    return {(p >> 18, p & 0x3FFFF): (v, (dd - 131072) * 2) for p, (v, dd) in resultado.items()}


def unir(n, parejas):
    padre = list(range(n))

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x
    for a, b in parejas:
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[max(ra, rb)] = min(ra, rb)
    return [raiz(i) for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=8)
    # Medido con las 66.326 (20-11-2026): el ruido da 2–5 votos; con 10–15 votos el nombre coincide el 93–97 %
    # y el año el 86 %, igual que con 300+ (el resto son tags mal puestos). Por eso basta con 12 votos.
    ap.add_argument("--votos", type=int, default=12)
    ap.add_argument("--parte", type=float, default=0.0)
    a = ap.parse_args()
    t0 = time.time()
    rels, cod, arch, t, cuantos, filas = cargar(a.muestra)
    print(f"{len(rels)} huellas, {len(cod):,} códigos elegidos ({time.time() - t0:.0f} s)", flush=True)
    votos = votar(cod, arch, t)
    print(f"{len(votos):,} parejas con algún voto ({time.time() - t0:.0f} s)", flush=True)

    filas_par = []
    for (x, y), (v, d) in votos.items():
        parte = v / max(1, min(cuantos[x], cuantos[y]))
        filas_par.append((rels[x], rels[y], int(v), round(float(parte), 3), round(d * SEG_COL, 2)))
    dur = [f[2] or 0 for f in filas]
    parecidas = [(x, y) for (x, y), (v, d) in votos.items()
                 if v >= a.votos and v / max(1, min(cuantos[x], cuantos[y])) >= a.parte]

    def recopilacion(x, y):
        """Un archivo largo (disco entero en un archivo) que CONTIENE al otro: no son la misma grabación.
        Si se juntaran, encadenaría todas las canciones del disco en un solo grupo."""
        largo, corto = max(dur[x], dur[y]), min(dur[x], dur[y])
        return largo > 420 and largo > 1.6 * corto
    iguales = [(x, y) for x, y in parecidas if not recopilacion(x, y)]
    contenedores = {}
    for x, y in parecidas:
        if recopilacion(x, y):
            g = x if dur[x] > dur[y] else y
            contenedores[g] = contenedores.get(g, 0) + 1
    grupo = unir(len(rels), iguales)

    con = sqlite3.connect(BD, timeout=120)
    con.execute("DROP TABLE IF EXISTS parejas")
    con.execute("CREATE TABLE parejas (a TEXT, b TEXT, votos INTEGER, parte REAL, desfase REAL)")
    con.executemany("INSERT INTO parejas VALUES (?,?,?,?,?)", [f for f in filas_par if f[2] >= 10])
    con.execute("DROP TABLE IF EXISTS grupos")
    con.execute("CREATE TABLE grupos (rel TEXT PRIMARY KEY, grupo INTEGER)")
    con.executemany("INSERT INTO grupos VALUES (?,?)", [(r, g) for r, g in zip(rels, grupo)])
    con.commit()

    # informe
    tam = {f[0]: f[1] for f in filas}
    miembros = {}
    for r, g in zip(rels, grupo):
        miembros.setdefault(g, []).append(r)
    con_copias = {g: m for g, m in miembros.items() if len(m) > 1}
    sobran = sum(len(m) - 1 for m in con_copias.values())
    gb = sum(sum(tam[r] for r in m) - max(tam[r] for r in m) for m in con_copias.values()) / 1e9
    ed = [m for m in miembros.values() if any(r.lower().startswith("edmundo" + os.sep) for r in m)]
    ed_sobran = sum(sum(r.lower().startswith("edmundo" + os.sep) for r in m) - 1 for m in ed)
    hist = np.histogram([v for v, _ in votos.values()], bins=[2, 5, 10, 20, 40, 80, 160, 320, 10 ** 9])
    txt = [f"Grupos «suenan igual» · {time.strftime('%d-%m-%Y %H:%M')} · {(time.time() - t0) / 60:.1f} min",
           f"Archivos con huella: {len(rels)}",
           f"Grabaciones distintas (grupos): {len(miembros)}",
           f"Grupos con copias: {len(con_copias)} · archivos que sobran: {sobran} · {gb:.1f} GB",
           f"Carpeta Edmundo: {sum(r.lower().startswith('edmundo' + os.sep) for r in rels)} archivos, "
           f"sobran {ed_sobran} (copias dentro de la propia carpeta)",
           f"Regla: votos ≥ {a.votos} y parte ≥ {a.parte} (muestra 1/{a.muestra})",
           "Votos de las parejas (cuántas parejas hay en cada tramo):"]
    for i, n in enumerate(hist[0]):
        txt.append(f"  {hist[1][i]:>5}–{hist[1][i + 1]:<10} {n}")
    txt.append(f"\nRecopilaciones (un archivo largo con varias canciones dentro; no se juntan): {len(contenedores)}")
    for g, k in sorted(contenedores.items(), key=lambda x: -x[1])[:30]:
        txt.append(f"  {dur[g] / 60:.0f} min, contiene {k}: {rels[g]}")
    txt.append("\nLos 30 grupos más grandes:")
    for g, m in sorted(con_copias.items(), key=lambda x: -len(x[1]))[:30]:
        txt.append(f"  [{len(m)}] " + " | ".join(m[:4]) + (" …" if len(m) > 4 else ""))
    with open(os.path.join(AQUI, "_GRUPOS.txt"), "w", encoding="utf8") as f:
        f.write("\n".join(txt) + "\n")
    print("\n".join(txt[:7]))


if __name__ == "__main__":
    main()
