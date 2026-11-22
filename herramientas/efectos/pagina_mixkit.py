"""Hace «Elegir efectos.html» con efectos de Mixkit (gratis, sin atribución, licencia Mixkit) para escuchar y marcar.

Suenan desde la web de Mixkit (no se baja nada hasta que Edmundo elige). Lleva también, sin marcar, los 25 de la
Valentino que había marcado antes, para comparar.
"""
import json
import re
from pathlib import Path

AQUI = Path(__file__).parent
SALIDA = Path(r"D:\Dropbox\TDJ\MUSICA\Elegir efectos.html")

# (id de Mixkit, nombre en español, grupo, segundos, propuesto)
MIXKIT = [
    (478, "Aplausos al final del espectáculo", "👏 Aplausos", 24, True),
    (502, "Aplausos y vítores en auditorio", "👏 Aplausos", 17, True),
    (485, "Aplausos de un grupo mediano", "👏 Aplausos", 11, True),
    (437, "Pequeña ovación", "👏 Aplausos", 6, True),
    (610, "Público aplaudiendo con silbido fuerte", "👏 Aplausos", 14, True),
    (504, "Aplausos rítmicos y vítores", "👏 Aplausos", 14, False),
    (507, "Aplausos con zapateo (sala de conciertos)", "👏 Aplausos", 16, False),
    (519, "Aplausos suaves de teatro", "👏 Aplausos", 8, False),
    (3039, "Aplausos en sala", "👏 Aplausos", 22, False),
    (501, "Aplausos suaves en iglesia", "👏 Aplausos", 9, False),
    (422, "Risas y aplausos", "👏 Aplausos", 5, False),
    (974, "Vítores de cumpleaños", "🎂 Cumpleaños y fiesta", 5, True),
    (531, "Vítores de fiesta de cumpleaños", "🎂 Cumpleaños y fiesta", 5, False),
    (975, "Público contento", "🎂 Cumpleaños y fiesta", 4, True),
    (530, "Matasuegras alegre", "🎂 Cumpleaños y fiesta", 2, True),
    (977, "Trompetilla de fiesta", "🎂 Cumpleaños y fiesta", 2, False),
    (980, "Doble trompetilla de fiesta", "🎂 Cumpleaños y fiesta", 1, False),
    (525, "Botellas brindando", "🎂 Cumpleaños y fiesta", 1, True),
    (3106, "Cohetes con silbido y explosión", "🎂 Cumpleaños y fiesta", 8, True),
    (976, "Fuegos artificiales con gente", "🎂 Cumpleaños y fiesta", 6, False),
    (527, "Matasuegras triste (de broma)", "🎂 Cumpleaños y fiesta", 1, False),
    (931, "Timbre de mostrador (atención)", "🔔 Avisos y campanas", 1, True),
    (586, "Campanilla de atención", "🔔 Avisos y campanas", 1, True),
    (1569, "Ding de aeropuerto (antes de un anuncio)", "🔔 Avisos y campanas", 4, True),
    (112, "Campanas de aviso (ascensor)", "🔔 Avisos y campanas", 5, False),
    (224, "Aviso elegante", "🔔 Avisos y campanas", 5, False),
    (109, "Timbre din-don", "🔔 Avisos y campanas", 4, True),
    (600, "Campana de premio", "🔔 Avisos y campanas", 2, False),
    (930, "Campana solemne", "🔔 Avisos y campanas", 8, False),
    (617, "Campana de iglesia melódica", "🔔 Avisos y campanas", 6, True),
    (587, "Campana de catedral", "🔔 Avisos y campanas", 28, False),
    (627, "Campanas de iglesia (final)", "🔔 Avisos y campanas", 22, False),
    (3108, "Carillón de cristal", "🔔 Avisos y campanas", 2, False),
    (2014, "Carillón de viento", "🔔 Avisos y campanas", 2, True),
    (1069, "Reloj dando la hora (campanas)", "🕛 Reloj", 6, True),
    (1057, "Reloj melódico dando la hora", "🕛 Reloj", 15, False),
    (1071, "Reloj antiguo grande dando la hora", "🕛 Reloj", 26, False),
    (1066, "Gong de reloj", "🕛 Reloj", 7, True),
    (1067, "Gong largo de reloj", "🕛 Reloj", 9, False),
    (614, "Silbato de policía", "📣 Silbatos", 1, True),
    (615, "Silbato corto", "📣 Silbatos", 1, True),
    (613, "Silbido largo (de persona)", "📣 Silbatos", 2, False),
    (605, "Silbido (de persona)", "📣 Silbatos", 1, False),
    (606, "Silbato de dibujos «se acabó»", "📣 Silbatos", 3, True),
    (616, "Silbato de juguete", "📣 Silbatos", 1, False),
    (2293, "Fanfarria de trompeta", "🎺 Fanfarrias", 8, True),
    (631, "Gran fanfarria de metales", "🎺 Fanfarrias", 5, True),
    (226, "Fanfarria de anuncio (medieval)", "🎺 Fanfarrias", 8, True),
    (722, "Bocinas de éxito", "🎺 Fanfarrias", 3, False),
    (629, "Fanfarria majestuosa lenta", "🎺 Fanfarrias", 11, False),
    (2292, "Final de trompetas de orquesta", "🎺 Fanfarrias", 4, False),
    (566, "Redoble de tambor", "🥁 Redobles", 5, True),
    (573, "Redoble suave", "🥁 Redobles", 6, False),
    (555, "Tambores de victoria", "🥁 Redobles", 5, True),
    (578, "Ba-dum-tss (chiste)", "🥁 Redobles", 2, True),
    (2893, "Tambores de chiste malo", "🥁 Redobles", 2, False),
    (701, "Aguja cayendo en el vinilo", "💿 Vinilo (DJ)", 1, True),
    (704, "Vinilo que se para de golpe", "💿 Vinilo (DJ)", 3, True),
    (711, "Vinilo que se va frenando", "💿 Vinilo (DJ)", 9, True),
    (702, "Scratch de vinilo", "💿 Vinilo (DJ)", 1, False),
    (708, "Golpe de vinilo (swipe)", "💿 Vinilo (DJ)", 1, False),
    (2195, "Beso largo", "😄 Humor", 1, True),
    (2196, "Doble beso coqueto", "😄 Humor", 1, False),
    (715, "Bocina de payaso", "😄 Humor", 2, True),
    (716, "Bocina de bici antigua", "😄 Humor", 2, False),
    (2015, "Campanitas de ganador", "😄 Humor", 2, True),
    (2068, "Logro conseguido", "😄 Humor", 3, False),
]
VALENTINO_ELEGIDOS = """VAL12-22 VAL02-38 VAL02-39 VAL02-42 VAL02-45 VAL12-73 VAL12-10 VAL12-76 VAL12-66 VAL01-87 VAL24-67 VAL01-90
VAL12-53 VAL10-24 VAL10-27 VAL21-28 VAL02-26 VAL24-52 VAL08-04 VAL21-74 VAL27-07 VAL27-52 VAL27-56 VAL27-59 VAL24-74""".split()

filas = []
for id_, nombre, grupo, seg, propuesto in MIXKIT:
    filas.append(dict(id=f"MIX-{id_}", nombre=nombre, grupo=grupo, original=f"Mixkit #{id_}",
                      url=f"https://assets.mixkit.co/active_storage/sfx/{id_}/{id_}-preview.mp3",
                      seg=seg, suena=seg, mb=round(max(0.1, seg * 0.12), 1), marcado=propuesto))
# los de la Valentino que se marcaron antes (de la página anterior), sin marcar, para comparar
anterior = AQUI / "_valentino_datos.json"
if anterior.exists():
    for f in json.loads(anterior.read_text(encoding="utf-8")):
        if f["id"] in VALENTINO_ELEGIDOS:
            f.update(grupo="📼 Los de la Valentino que marcaste", marcado=False)
            filas.append(f)
grupos = list(dict.fromkeys(f["grupo"] for f in filas))
html = (AQUI / "plantilla_efectos.html").read_text(encoding="utf-8")
html = html.replace("tdj_elegir_efectos", "tdj_elegir_efectos_mixkit")
html = html.replace("__DATOS__", json.dumps(filas, ensure_ascii=False)).replace("__GRUPOS__", json.dumps(grupos, ensure_ascii=False))
SALIDA.write_text(html, encoding="utf-8")
print(len(filas), "efectos;", sum(f["marcado"] for f in filas), "marcados")
print(SALIDA.as_uri())
