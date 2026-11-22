"""Avisos hablados para la milonga (última tanda, La Cumparsita…) con voces de Microsoft (edge-tts) → FLAC en
MUSICA\\Edmundo\\Efectos, «Voz <quién> - <aviso>.flac».

    %USERPROFILE%\\venvs\\voces\\Scripts\\python.exe voces.py              # todos, con Álvaro y Tomás
    ... voces.py "Media hora" --voz alvaro                                # solo uno

Para añadir un aviso: una línea más en AVISOS.
"""
import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts

DESTINO = Path(r"D:\Dropbox\TDJ\MUSICA\Edmundo\Efectos")
VOCES = {"Álvaro": "es-ES-AlvaroNeural", "Tomás": "es-AR-TomasNeural"}
# un poco más lento y más grave que como viene: suena más a locutor
RITMO, TONO = "-8%", "-6Hz"
AVISOS = {
    "Bienvenida": "Buenas noches... ¡Bienvenidos a la milonga!",
    "Quedan dos tandas": "Quedan dos tandas.",
    "Última tanda": "¡Última tanda!",
    "La Cumparsita": "Y para despedir la noche... ¡La Cumparsita!",
    "Despedida": "Gracias por venir. ¡Buenas noches, y hasta la próxima!",
    "Exhibición": "Atención, por favor: les pedimos que despejen la pista para la exhibición.",
    "Un fuerte aplauso": "¡Un fuerte aplauso!",
    "Cumpleaños": "¡Feliz cumpleaños! Vals para el cumpleañero.",
    "Queda media hora": "Queda media hora de milonga.",
    "Sorteo": "Atención... ¡llega el sorteo!",
}


async def grabar(texto, voz, mp3):
    await edge_tts.Communicate(texto, voz, rate=RITMO, pitch=TONO).save(str(mp3))


def a_flac(mp3, flac, titulo):
    # sin silencio al principio ni al final, y todos al mismo volumen (−16 LUFS, como un anuncio de radio)
    filtro = ("silenceremove=start_periods=1:start_threshold=-60dB,areverse,"
              "silenceremove=start_periods=1:start_threshold=-60dB:start_silence=0.2,areverse,"
              "loudnorm=I=-16:TP=-1.5:LRA=11")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp3), "-af", filtro,
                    "-ar", "44100", "-c:a", "flac", "-metadata", f"title={titulo}", "-metadata", "genre=Efecto",
                    str(flac)], check=True)


def main():
    solo = [a for a in sys.argv[1:] if not a.startswith("--")]
    voces = VOCES
    if "--voz" in sys.argv:
        q = sys.argv[sys.argv.index("--voz") + 1].lower()
        voces = {k: v for k, v in VOCES.items() if k.lower().startswith(q[:3])}
        solo = [a for a in solo if a.lower() != q]
    avisos = {k: v for k, v in AVISOS.items() if not solo or k in solo}
    DESTINO.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="voces_"))
    for quien, voz in voces.items():
        for nombre, texto in avisos.items():
            mp3 = tmp / f"{quien}_{nombre}.mp3"
            asyncio.run(grabar(texto, voz, mp3))
            flac = DESTINO / f"Voz {quien} - {nombre}.flac"
            a_flac(mp3, flac, f"Voz {quien} - {nombre}")
            print(f"{flac.stat().st_size / 1e3:6.0f} KB  {flac.name}")


if __name__ == "__main__":
    main()
