"""Pasa a MIDI un audio con YourMT3+ (YPTF.MoE+Multi noPS), en el procesador.
Uso (python de venvs\\yourmt3; el código del modelo está en venvs\\yourmt3_code):
    python yourmt3.py <audio> <salida.mid> [inicio_s fin_s]
Sube el volumen hasta un pico de 0,95 antes de transcribir. OJO: con las pistas separadas YourMT3+ casi no saca
notas (88 en 3 min de contrabajo, con o sin subir el volumen, 18-11-2026): pasarle la MEZCLA.
Tarda unas 3 veces la duración del audio con la mezcla, algo menos con una pista suelta.
"""
import os, sys, time, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rutas
CODIGO = os.path.join(rutas.VENVS, "yourmt3_code")
os.chdir(CODIGO)
sys.path[:0] = [CODIGO, os.path.join(CODIGO, "amt", "src")]
import numpy as np, torch, librosa
from model_helper import load_model_checkpoint
from utils.audio import slice_padded_array
from utils.note2event import mix_notes
from utils.event2note import merge_zipped_note_events_and_ties_to_notes
from utils.utils import write_model_output_as_midi

audio, salida = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
t1 = float(sys.argv[4]) if len(sys.argv) > 4 else None
torch.set_num_threads(os.cpu_count() or 8)
ckpt = "mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops@last.ckpt"
args = [ckpt, '-p', '2024', '-tk', 'mc13_full_plus_256', '-dec', 'multi-t5',
        '-nl', '26', '-enc', 'perceiver-tf', '-sqr', '1', '-ff', 'moe',
        '-wf', '4', '-nmoe', '8', '-kmoe', '2', '-act', 'silu', '-epe', 'rope',
        '-rp', '1', '-ac', 'spec', '-hop', '300', '-atc', '1', '-pr', '32']
model = load_model_checkpoint(args=args, device="cpu")
sr = model.audio_cfg['sample_rate']
y, _ = librosa.load(audio, sr=sr, mono=True, offset=t0, duration=None if t1 is None else t1 - t0)
# afinación: los discos viejos suelen estar un poco altos o bajos (El Huracán: −0,3 semitonos) y el modelo duda
# entre dos notas (salía «Sol#» por «La»). Se corrige antes de transcribir (19-11-2026).
afin = float(librosa.estimate_tuning(y=y, sr=sr))
if abs(afin) > 0.08:
    y = librosa.effects.pitch_shift(y, sr=sr, n_steps=-afin)
print(f"afinación del disco: {afin:+.2f} semitonos" + (" (corregida)" if abs(afin) > 0.08 else ""), flush=True)
y = (0.95 * y / (np.abs(y).max() + 1e-9)).astype("float32")
seg = slice_padded_array(y[None, :], model.audio_cfg['input_frames'], model.audio_cfg['input_frames'])
seg = torch.from_numpy(seg.astype('float32')).unsqueeze(1)
tt = time.time()
with torch.no_grad():
    pred, _ = model.inference_file(bsz=8, audio_segments=seg)
starts = [t0 + model.audio_cfg['input_frames'] * i / sr for i in range(seg.shape[0])]
notas = []
for ch in range(model.task_manager.num_decoding_channels):
    z, _, _ = model.task_manager.detokenize_list_batches([p[:, ch, :] for p in pred], starts, return_events=True)
    nn_, _ = merge_zipped_note_events_and_ties_to_notes(z)
    notas.append(nn_)
notas = mix_notes(notas)
nombre = "tmp_" + str(os.getpid())
write_model_output_as_midi(notas, './', nombre, model.midi_output_inverse_vocab)
shutil.move(f'./model_output/{nombre}.mid', salida)
print(f"YourMT3+: {time.time() - tt:.0f} s para {len(y) / sr:.0f} s de audio · {len(notas)} notas -> {salida}")
