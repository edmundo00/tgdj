"""
La noche: las pistas (temas y cortinas) agrupadas en bloques (tandas y cortinas) y las horas previstas.

    pistas = pistas_de(tandas)                 # de generador.agrupar_tandas
    bloques(pistas)                            # [{tipo, numero, indices, …}]
    horas(pistas, indice, segundo, estado, ahora, silencio)   # hora (time.time()) de inicio de cada pista + fin
"""
from src.diapos.web import _genero

CORTINA_PREVISTA = 60.0              # para las horas: la cortina se corta más o menos al minuto


def pistas_de(tandas):
    """Lista plana de pistas (lo que el motor va a sonar), con su tanda."""
    pistas, numero = [], 0
    for t in tandas:
        if not t.es_cortina:
            numero += 1
        for _, c in t.canciones.iterrows():
            pistas.append({
                "ruta": c["ruta"], "titulo": c["title"], "artista": c["artist"], "ano": c["ano"],
                "duracion": float(c["duration"] or 0), "cortina": t.es_cortina,
                "tanda": None if t.es_cortina else numero, "orquesta": t.titulo_orquesta,
                "subtitulo": t.subtitulo, "genero": "cortina" if t.es_cortina else _genero(t.genero),
            })
    return pistas


def bloques(pistas):
    """Tandas y cortinas seguidas: [{tipo: 'tanda'|'cortina', numero, orquesta, subtitulo, genero, indices}]."""
    salida = []
    for i, p in enumerate(pistas):
        clave = ("cortina", None) if p["cortina"] else ("tanda", p["tanda"])
        ultimo = salida[-1] if salida else None
        if ultimo and (ultimo["tipo"], ultimo["numero"]) == clave and not p["cortina"]:
            ultimo["indices"].append(i)
            continue
        salida.append({"tipo": clave[0], "numero": clave[1], "orquesta": p["orquesta"], "subtitulo": p["subtitulo"],
                       "genero": p["genero"], "indices": [i]})
    return salida


def duracion_prevista(p, cortina=CORTINA_PREVISTA):
    return min(p["duracion"], cortina) if p["cortina"] and cortina else p["duracion"]


def horas(pistas, indice, segundo, estado, ahora, silencio, cortina=CORTINA_PREVISTA, empezadas=None,
          hueco=0.0, inicio_previsto=None):
    """
    (inicios, fin): hora a la que empieza (o empezó) cada pista y a la que acabará la noche, siguiendo lo que
    suena ahora. Las ya sonadas, cuando empezaron de verdad (empezadas = {índice: hora}); None si no se sabe.
    Parado: como si se empezara ahora (o a `inicio_previsto`, si es más tarde).
    """
    n = len(pistas)
    inicios = [None] * n
    if not n:
        return inicios, ahora
    empezadas = empezadas or {}
    for i in range(indice):
        inicios[i] = empezadas.get(i)
    actual = pistas[indice]
    if estado in ("parado",):
        inicios[indice] = max(ahora, inicio_previsto or ahora)
        t = inicios[indice] + duracion_prevista(actual, cortina)
    elif estado == "hueco":                      # el silencio antes de `indice`
        inicios[indice] = ahora + hueco
        t = inicios[indice] + duracion_prevista(actual, cortina)
    elif estado == "fin":
        inicios[indice] = empezadas.get(indice)
        return inicios, ahora
    else:                                        # sonando o en pausa (como si siguiera ya)
        inicios[indice] = empezadas.get(indice, ahora - segundo)
        t = ahora + max(0.0, duracion_prevista(actual, cortina) - segundo)
    for j in range(indice + 1, n):
        t += silencio
        inicios[j] = t
        t += duracion_prevista(pistas[j], cortina)
    return inicios, t
