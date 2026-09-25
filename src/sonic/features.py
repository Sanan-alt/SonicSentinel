"""Acoustic feature extraction (SRS Step 6 / requirement xx).

Produces a fixed-length feature vector per clip by summarising frame-level
librosa features with mean + standard deviation. Features included:

    MFCC (+delta), Mel spectrogram (dB), Chroma, Zero-crossing rate,
    RMS energy, Spectral centroid, Spectral bandwidth, Spectral roll-off.

The vector length is deterministic given the config, so train/predict stay
consistent.
"""

from __future__ import annotations

import librosa
import numpy as np


def _stats(matrix: np.ndarray) -> np.ndarray:
    """Mean and std across the time axis of a (features, frames) matrix."""
    return np.concatenate([matrix.mean(axis=1), matrix.std(axis=1)])


def extract_features(y: np.ndarray, sr: int, cfg) -> np.ndarray:
    """Return a 1-D feature vector for a preprocessed signal ``y``."""
    f = cfg["features"]
    n_mfcc = int(f["n_mfcc"])
    n_mels = int(f["n_mels"])
    n_fft = int(f["n_fft"])
    hop = int(f["hop_length"])

    parts: list[np.ndarray] = []

    # MFCC + delta.
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc, n_fft=n_fft, hop_length=hop)
    parts.append(_stats(mfcc))
    parts.append(_stats(librosa.feature.delta(mfcc)))

    # Mel spectrogram (dB).
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, n_fft=n_fft, hop_length=hop)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    parts.append(_stats(mel_db))

    # Chroma.
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=n_fft, hop_length=hop)
    parts.append(_stats(chroma))

    # Zero-crossing rate.
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop)
    parts.append(_stats(zcr))

    # RMS energy.
    rms = librosa.feature.rms(y=y, hop_length=hop)
    parts.append(_stats(rms))

    # Spectral centroid / bandwidth / roll-off.
    parts.append(_stats(librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop)))
    parts.append(_stats(librosa.feature.spectral_bandwidth(y=y, sr=sr, n_fft=n_fft, hop_length=hop)))
    parts.append(_stats(librosa.feature.spectral_rolloff(y=y, sr=sr, n_fft=n_fft, hop_length=hop)))

    return np.concatenate(parts).astype(np.float32)


def feature_names(cfg) -> list[str]:
    """Human-readable names for each feature dimension (for reports)."""
    f = cfg["features"]
    names: list[str] = []

    def add(prefix: str, count: int) -> None:
        names.extend(f"{prefix}_mean_{i}" for i in range(count))
        names.extend(f"{prefix}_std_{i}" for i in range(count))

    add("mfcc", int(f["n_mfcc"]))
    add("mfcc_delta", int(f["n_mfcc"]))
    add("mel_db", int(f["n_mels"]))
    add("chroma", 12)
    add("zcr", 1)
    add("rms", 1)
    add("spectral_centroid", 1)
    add("spectral_bandwidth", 1)
    add("spectral_rolloff", 1)
    return names
