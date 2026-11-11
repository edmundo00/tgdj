"""Paso 1: separar un tango en pistas (contrabajo, piano, voz, bandoneones, violines).

El separador (BS-RoFormer de 6 pistas) saca bajo, piano, voz, batería, guitarra y «otros».
En tango no hay batería ni guitarra: lo que cae ahí son bandoneones y violines, así que se suman a «otros»
para formar «resto». Luego «resto» se parte en lo marcado (bandoneones) y lo ligado (violines).
Los archivos ya separados se reutilizan: separar una canción solo se hace una vez.
"""
import os, glob
import numpy as np, librosa, soundfile as sf

SR = 44100
MODELO = "BS-Roformer-SW.ckpt"
# nombre que pone el separador -> nuestro nombre
NOMBRES = {"bass": "contrabajo", "piano": "piano", "vocals": "voz",
           "other": "otros", "guitar": "otros", "drums": "otros"}


def _separar_con_modelo(audio, carpeta_modelo, dir_tmp):
    from audio_separator.separator import Separator
    sep = Separator(output_dir=dir_tmp, output_format="FLAC", model_file_dir=carpeta_modelo)
    sep.load_model(model_filename=MODELO)
    salidas = sep.separate(audio)
    return [os.path.join(dir_tmp, os.path.basename(f)) for f in salidas]


def _cargar(f):
    y, _ = librosa.load(f, sr=SR, mono=True)
    return y


def _asegurar_contrabajo(pistas, dir_pistas):
    """En grabaciones antiguas con pocos graves el separador puede dejar el contrabajo mudo.
    Entonces se saca filtrando los graves (45-220 Hz) de la orquesta: es aproximado (entra la mano izquierda del piano)."""
    from scipy.signal import butter, sosfiltfilt
    marca = os.path.join(dir_pistas, "contrabajo_aproximado.txt")
    if np.sqrt(np.mean(pistas["contrabajo"] ** 2)) > 1e-4 and not os.path.exists(marca):
        return False
    if not os.path.exists(marca):
        sos = butter(4, [45, 220], btype="band", fs=SR, output="sos")
        y = sosfiltfilt(sos, pistas["resto"] + pistas["piano"])
        y = y / (np.abs(y).max() + 1e-9) * 0.5
        pistas["contrabajo"] = y
        sf.write(os.path.join(dir_pistas, "contrabajo.flac"), y, SR)
        open(marca, "w", encoding="utf-8").write("El separador dejó el contrabajo mudo; se ha sacado filtrando los graves.\n")
    return True


def separar(audio, dir_pistas, carpeta_modelo):
    """Devuelve {nombre: señal mono} y deja las pistas en dir_pistas."""
    os.makedirs(dir_pistas, exist_ok=True)
    finales = ["contrabajo", "piano", "voz", "resto", "bandoneones", "violines"]
    if all(os.path.exists(os.path.join(dir_pistas, f"{n}.flac")) for n in finales):
        pistas = {n: _cargar(os.path.join(dir_pistas, f"{n}.flac")) for n in finales}
        pistas["_contrabajo_aprox"] = _asegurar_contrabajo(pistas, dir_pistas)
        return pistas

    tmp = os.path.join(dir_pistas, "_separador")
    os.makedirs(tmp, exist_ok=True)
    salidas = glob.glob(os.path.join(tmp, "*.flac")) or _separar_con_modelo(audio, carpeta_modelo, tmp)

    pistas = {}
    for f in salidas:
        clave = next((k for k in NOMBRES if f"({k})" in os.path.basename(f).lower()), None)
        if clave is None:
            continue
        n = NOMBRES[clave]
        y = _cargar(f)
        pistas[n] = pistas[n] + y[:len(pistas[n])] if n in pistas else y
    pistas["resto"] = pistas.pop("otros")

    # bandoneones (cortado, marcado) frente a violines (ligado, sostenido)
    D = librosa.stft(pistas["resto"], n_fft=4096, hop_length=512)
    H, P = librosa.decompose.hpss(D, kernel_size=(41, 31), margin=(1.5, 1.5))
    L = len(pistas["resto"])
    pistas["bandoneones"] = librosa.istft(P, hop_length=512, length=L)
    pistas["violines"] = librosa.istft(H, hop_length=512, length=L)

    for n, y in pistas.items():
        sf.write(os.path.join(dir_pistas, f"{n}.flac"), y, SR)
    pistas["_contrabajo_aprox"] = _asegurar_contrabajo(pistas, dir_pistas)
    return pistas
