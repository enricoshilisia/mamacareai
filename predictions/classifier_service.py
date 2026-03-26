import numpy as np
import librosa
import joblib
import tensorflow as tf
from pathlib import Path

_MODEL_DIR = Path(__file__).resolve().parent / "ml_models"

try:
    _model         = tf.keras.models.load_model(str(_MODEL_DIR / "cry_classifier.h5"))
    _scaler        = joblib.load(_MODEL_DIR / "scaler.joblib")
    _label_classes = np.load(_MODEL_DIR / "label_classes.npy", allow_pickle=True)
    _MODEL_READY   = True
    print(f"[CryClassifier] Model loaded. Classes: {list(_label_classes)}")
except Exception as e:
    _MODEL_READY = False
    print(f"[CryClassifier] WARNING: Model not loaded — {e}")

SR            = 16000
N_MELS        = 128
N_FFT         = 400
HOP_LENGTH    = 160
TARGET_FRAMES = 701
TARGET_SECS   = 7.0


def _load_audio(file_path: str) -> np.ndarray:
    """
    Load audio robustly without requiring ffmpeg.
    Priority: soundfile → wave module → pydub
    """

    # ── 1. Standard librosa (uses soundfile internally) ──────────────────────
    try:
        y, _ = librosa.load(file_path, sr=SR, mono=True, duration=TARGET_SECS + 1)
        if len(y) > 0:
            print(f"[CryClassifier] Loaded via librosa/soundfile: {len(y)} samples")
            return y
    except Exception as e:
        print(f"[CryClassifier] soundfile failed: {e}")

    # ── 2. Raw WAV PCM via stdlib wave module ─────────────────────────────────
    try:
        import wave
        with wave.open(file_path, 'rb') as wf:
            frames    = wf.readframes(wf.getnframes())
            n_ch      = wf.getnchannels()
            sw        = wf.getsampwidth()
            sr_native = wf.getframerate()

        # Support 16-bit and 32-bit PCM
        if sw == 2:
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif sw == 4:
            samples = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Unsupported sample width: {sw}")

        if n_ch > 1:
            samples = samples.reshape(-1, n_ch).mean(axis=1)
        if sr_native != SR:
            samples = librosa.resample(samples, orig_sr=sr_native, target_sr=SR)

        if len(samples) > 0:
            print(f"[CryClassifier] Loaded via wave module: {len(samples)} samples")
            return samples
    except Exception as e:
        print(f"[CryClassifier] wave module failed: {e}")

    # ── 3. Pydub (pure Python, no ffmpeg needed for WAV/raw formats) ──────────
    try:
        from pydub import AudioSegment

        # Detect format from file header
        with open(file_path, 'rb') as f:
            header = f.read(12)

        if header[:4] == b'RIFF':
            fmt = 'wav'
        elif header[:4] == b'fLaC':
            fmt = 'flac'
        elif header[:3] == b'ID3' or header[:2] == b'\xff\xfb':
            fmt = 'mp3'
        elif header[4:8] == b'ftyp':
            fmt = 'm4a'
        else:
            fmt = 'wav'  # best guess

        audio   = AudioSegment.from_file(file_path, format=fmt)
        audio   = audio.set_frame_rate(SR).set_channels(1).set_sample_width(2)
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0

        if len(samples) > 0:
            print(f"[CryClassifier] Loaded via pydub: {len(samples)} samples, fmt={fmt}")
            return samples
    except Exception as e:
        print(f"[CryClassifier] pydub failed: {e}")

    # ── 4. AudioContext WAV: try scipy as last resort ─────────────────────────
    try:
        from scipy.io import wavfile
        sr_native, data = wavfile.read(file_path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        if data.dtype == np.int16:
            samples = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            samples = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.float32:
            samples = data
        else:
            samples = data.astype(np.float32)
        if sr_native != SR:
            samples = librosa.resample(samples, orig_sr=sr_native, target_sr=SR)
        if len(samples) > 0:
            print(f"[CryClassifier] Loaded via scipy: {len(samples)} samples")
            return samples
    except Exception as e:
        print(f"[CryClassifier] scipy failed: {e}")

    raise ValueError(f"Could not load audio from {file_path} — all backends failed")


def _preprocess_audio(file_path: str) -> np.ndarray:
    y = _load_audio(file_path)

    # Pad or truncate to exactly 7 seconds
    target_samples = int(TARGET_SECS * SR)
    if len(y) < target_samples:
        y = np.pad(y, (0, target_samples - len(y)), mode='constant')
    else:
        y = y[:target_samples]

    # Mel-Spectrogram
    S    = librosa.feature.melspectrogram(
               y=y, sr=SR, n_fft=N_FFT, hop_length=HOP_LENGTH, n_mels=N_MELS
           )
    S_db = librosa.power_to_db(S, ref=np.max)

    # Force shape (128, 701)
    if S_db.shape[1] < TARGET_FRAMES:
        S_db = np.pad(S_db, ((0, 0), (0, TARGET_FRAMES - S_db.shape[1])),
                      mode='constant', constant_values=S_db.min())
    else:
        S_db = S_db[:, :TARGET_FRAMES]

    # Scale and reshape for CNN
    flat   = S_db.reshape(1, -1)
    scaled = _scaler.transform(flat)
    shaped = scaled.reshape(1, N_MELS, TARGET_FRAMES, 1)

    return shaped


def classify_audio(file_path: str) -> dict:
    if not _MODEL_READY:
        return {
            "success": False,
            "error": "Model not loaded. Place model files in predictions/ml_models/"
        }

    try:
        # Debug: log file info
        import os
        size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            header = f.read(4)
        print(f"[CryClassifier] Processing file: {file_path} | size={size}B | header={header}")

        X      = _preprocess_audio(file_path)
        probs  = _model.predict(X, verbose=0)[0]

        top_idx    = int(np.argmax(probs))
        cry_type   = str(_label_classes[top_idx])
        confidence = float(probs[top_idx])

        all_probs = {
            str(_label_classes[i]): round(float(probs[i]), 4)
            for i in range(len(_label_classes))
        }

        serious_types = {"belly_pain", "cold_hot"}
        is_serious    = cry_type in serious_types and confidence > 0.65

        return {
            "success":    True,
            "cry_type":   cry_type,
            "confidence": confidence,
            "all_probs":  all_probs,
            "is_serious": is_serious,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}