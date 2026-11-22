"""Hace «Elegir efectos.html» con efectos de Freesound (solo CC0: libres para pinchar en público, sin citar a nadie),
los más descargados de cada tipo, para escuchar y marcar. Suenan desde Freesound: no se baja nada hasta que Edmundo
elige. Lleva también, sin marcar, los aplausos que ya tiene (para comparar).

Datos: _freesound_datos.json (sacado de las búsquedas de freesound.org, licencia CC0, 22-11-2026).
"""
import json
from pathlib import Path

AQUI = Path(__file__).parent
SALIDA = Path(r"D:\Dropbox\TDJ\MUSICA\Elegir efectos.html")
EFECTOS = Path(r"D:\Dropbox\TDJ\MUSICA\Edmundo\Efectos")

GRUPOS = {
    "Aplausos grandes": "👏 Aplausos y público", "Ovación con vítores": "👏 Aplausos y público",
    "Público «oooh»": "👏 Aplausos y público", "Risas del público": "😂 Bromas",
    "Bocina de DJ (air horn)": "🎧 De DJ", "Scratch de DJ": "🎧 De DJ", "Vinilo": "🎧 De DJ", "Rebobinar": "🎧 De DJ",
    "Redoble": "🥁 Tambores y fanfarrias", "Ba-dum-tss (chiste)": "😂 Bromas", "Platillo": "🥁 Tambores y fanfarrias",
    "Ta-dá": "🥁 Tambores y fanfarrias", "Fanfarria": "🥁 Tambores y fanfarrias",
    "Campana de iglesia": "🔔 Campanas", "Campana de boxeo": "🔔 Campanas", "Gong": "🔔 Campanas",
    "Cuenco tibetano": "🔔 Campanas", "Carillón de viento": "🔔 Campanas",
    "Corcho de champán": "🥂 Fiesta", "Brindis de copas": "🥂 Fiesta", "Matasuegras / fiesta": "🥂 Fiesta",
    "Confeti (lanzador)": "🥂 Fiesta", "Fuegos artificiales": "🥂 Fiesta", "Silbato de árbitro": "📣 Silbatos",
}
# propuestos: lo más descargado de cada tipo que tiene sentido en una milonga
PROPUESTOS = {334941, 478415, 346689, 264377, 264499, 333403, 131930, 151822, 162493, 117512, 77305, 383898, 397355,
              242207, 554655, 520998, 486629, 439235, 239040, 708201, 673315, 218318, 170583, 26349, 347119}

datos = json.loads((AQUI / "_freesound_datos.json").read_text(encoding="utf-8"))
filas = []
for tipo, lista in datos.items():
    for x in sorted(lista, key=lambda x: -x["n"]):
        filas.append(dict(id=f"FS-{x['id']}", nombre=f"{tipo} · {x['t'].strip()}", grupo=GRUPOS.get(tipo, "Otros"),
                          original=f"Freesound #{x['id']} · {x['u']} · {x['n']:,} descargas".replace(",", "."),
                          url=x["mp3"], seg=x["s"], suena=x["s"], mb=round(max(0.1, x["s"] * 0.03), 1),
                          marcado=x["id"] in PROPUESTOS))
# los aplausos que ya tiene, para comparar (sin marcar)
for f in sorted(EFECTOS.glob("*plaus*")) + sorted(EFECTOS.glob("*vación*")):
    filas.append(dict(id=f"YA-{f.stem}", nombre=f"(ya lo tienes) {f.stem}", grupo="📁 Los aplausos que ya tienes",
                      original="tu carpeta Efectos", url="Edmundo/Efectos/" + f.name, seg=0, suena=0, mb=0,
                      marcado=False))
grupos = list(dict.fromkeys(f["grupo"] for f in filas))
html = (AQUI / "plantilla_efectos.html").read_text(encoding="utf-8")
html = html.replace("tdj_elegir_efectos", "tdj_elegir_efectos_freesound")
ayuda_vieja = html[html.index('<p class="ayuda">'):html.index("</p>", html.index('<p class="ayuda">')) + 4]
html = html.replace(ayuda_vieja, """<p class="ayuda">Efectos de <b>Freesound</b>, los más descargados de cada tipo y solo los
    <b>CC0</b> (libres: se pueden pinchar en público sin citar a nadie). Suenan desde su web (hace falta internet).
    ▶ para escuchar (otra vez = parar; espacio = parar lo que suena). Ya van marcados ☑ los que te propongo: quita o
    pon los que quieras y cambia el nombre si quieres. Al final, <b>los aplausos que ya tienes</b>, para comparar.
    Al acabar, <b>📋 Copiar la lista para Claude</b> y pégala en el chat. Se acuerda de lo marcado aunque cierres.</p>""")
html = html.replace("__DATOS__", json.dumps(filas, ensure_ascii=False)).replace("__GRUPOS__", json.dumps(grupos, ensure_ascii=False))
SALIDA.write_text(html, encoding="utf-8")
print(len(filas), "efectos;", sum(f["marcado"] for f in filas), "marcados")
print(SALIDA.as_uri())
