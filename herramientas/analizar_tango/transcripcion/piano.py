"""Pasa a MIDI una pista de piano con piano_transcription_inference (ByteDance, Kong 2020), en el procesador.
Uso (con el python de venvs\\yourmt3):  python piano.py <audio> <salida.mid>
El modelo (172 MB) está en %USERPROFILE%\\piano_transcription_inference_data.
"""
import sys, time
import librosa
from piano_transcription_inference import PianoTranscription, sample_rate

audio, salida = sys.argv[1], sys.argv[2]
y, _ = librosa.load(audio, sr=sample_rate, mono=True)
t = time.time()
PianoTranscription(device="cpu").transcribe(y, salida)
print(f"piano: {time.time() - t:.0f} s para {len(y) / sample_rate:.0f} s de audio -> {salida}")
