"""Pasa a MIDI un audio con MuScriptor (2026, pesos CC-BY-NC: solo uso no comercial), en el procesador.
Uso (python de venvs\\transcribir):  python muscriptor_tr.py <audio> <salida.mid> [--modelo large] [--instrumentos a,b]
La primera vez baja el modelo (~5 GB) a %USERPROFILE%\\.cache\\huggingface: hace falta haber aceptado las
condiciones en huggingface.co/muscriptor/muscriptor-large y tener el token guardado (hf auth login).
Sube el volumen hasta un pico de 0,95 (las pistas separadas suenan mucho más flojo que la mezcla).
"""
import os, sys, time, tempfile, argparse
from pathlib import Path
import numpy as np, soundfile as sf, librosa

ap = argparse.ArgumentParser()
ap.add_argument("audio"); ap.add_argument("salida")
ap.add_argument("--modelo", default="large")
ap.add_argument("--instrumentos", default=None, help="p. ej. acoustic_piano,acoustic_bass,accordion")
a = ap.parse_args()

import subprocess
y, sr = librosa.load(a.audio, sr=16000, mono=True)
y = (0.95 * y / (np.abs(y).max() + 1e-9)).astype("float32")
tmp = os.path.join(tempfile.mkdtemp(prefix="muscriptor_"), "entrada.wav")
sf.write(tmp, y, sr)
# la versión instalada (18-11-2026) ya no tiene transcribe_to_midi en Python: se usa su programa
exe = os.path.join(os.path.dirname(sys.executable), "muscriptor")
orden = [exe, "transcribe", "--model", a.modelo, tmp, "-o", a.salida]
if a.instrumentos:
    orden += ["--instruments", a.instrumentos]
t = time.time()
subprocess.run(orden, check=True)
print(f"MuScriptor ({a.modelo}): {time.time() - t:.0f} s para {len(y) / sr:.0f} s de audio -> {a.salida}")
