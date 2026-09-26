"""Audio preprocessing pipeline (SRS Step 4 / requirement xi).

Steps applied to every clip before feature extraction:
    load -> mono -> resample -> silence trim -> normalise -> pad/truncate
"""

from __future__ import annotations

from dataclasses import dataclass

import librosa
import numpy as np


@dataclass
class AudioSettings:
    sample_rate: int = 22050
    mono: bool = True
    duration: float = 5.0
    top_db: float = 30.0
    normalize: bool = True

    @classmethod
    def from_config(cls, cfg) -> "AudioSettings":
        a = cfg["audio"]
        return cls(
            sample_rate=int(a["sample_rate"]),
            mono=bool(a["mono"]),
            duration=float(a["duration"]),
            top_db=float(a["top_db"]),
            normalize=bool(a["normalize"]),
        )


# Never load more than this many seconds into memory at once. Some source
# clips are several minutes long; we only need a short window for a fixed-size
# feature vector, so loading the whole thing wastes memory (and can OOM).
MAX_LOAD_SECONDS = 30.0


def load_audio(path, settings: AudioSettings) -> np.ndarray:
    """Load a clip and apply the full preprocessing chain.

    Returns a 1-D float32 array of exactly ``duration * sample_rate`` samples.
    Raises ValueError for silent / empty signals so callers can reject them.
    Only the first MAX_LOAD_SECONDS are read to keep memory bounded.
    """
    y, _ = librosa.load(path, sr=settings.sample_rate, mono=settings.mono,
                        duration=MAX_LOAD_SECONDS)
    if y.size == 0:
        raise ValueError("empty audio signal")

    # Silence trimming (leading/trailing).
    y_trimmed, _ = librosa.effects.trim(y, top_db=settings.top_db)
    if y_trimmed.size > 0:
        y = y_trimmed

    # Reject near-silent recordings (SRS silence detection).
    if float(np.max(np.abs(y))) < 1e-4:
        raise ValueError("signal is silent or near-silent")

    # Peak normalisation.
    if settings.normalize:
        peak = float(np.max(np.abs(y)))
        if peak > 0:
            y = y / peak

    # Pad or truncate to a fixed length.
    target_len = int(settings.duration * settings.sample_rate)
    if y.shape[0] < target_len:
        y = np.pad(y, (0, target_len - y.shape[0]), mode="constant")
    else:
        y = y[:target_len]

    return y.astype(np.float32)


def load_raw(path, settings: AudioSettings) -> np.ndarray:
    """Load + mono + resample only (no trim/pad) - for segmentation.

    Capped to MAX_LOAD_SECONDS so a multi-minute clip yields a bounded number
    of segments and stays within memory.
    """
    y, _ = librosa.load(path, sr=settings.sample_rate, mono=settings.mono,
                        duration=MAX_LOAD_SECONDS)
    return y.astype(np.float32)


def segment_signal(y: np.ndarray, settings: AudioSettings):
    """Split a long signal into fixed-duration segments (SRS requirement xv/xxii).

    Yields (segment_signal, start_sec, end_sec). Each segment is padded/truncated
    to the fixed clip length. Short signals yield a single segment.
    """
    sr = settings.sample_rate
    win = int(settings.duration * sr)
    total = y.shape[0]
    if total <= win:
        seg = np.pad(y, (0, win - total), mode="constant") if total < win else y[:win]
        yield seg.astype(np.float32), 0.0, round(total / sr, 3)
        return
    start = 0
    while start < total:
        chunk = y[start:start + win]
        if chunk.shape[0] < win:
            chunk = np.pad(chunk, (0, win - chunk.shape[0]), mode="constant")
        yield chunk.astype(np.float32), round(start / sr, 3), round(min(start + win, total) / sr, 3)
        start += win
