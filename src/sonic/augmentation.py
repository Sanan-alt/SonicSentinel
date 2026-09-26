"""Training-time audio augmentation (SRS requirement xix / Step: augmentation).

All augmentations operate on a preprocessed 1-D signal and return a new signal
of the same length. They are applied ONLY to training-split clips. Augmented
clips inherit the split and Audio ID of their parent and are never counted as
unique originals (SRS rule).

Available augmentations:
    add_noise          background-noise addition
    time_shift         circular time shift
    pitch_shift        pitch shifting (semitones)
    time_stretch       time stretching (then re-fit to length)
    volume_adjust      volume/gain change
    reverb             limited reverberation (simple decaying echo)
    distance_sim       distance simulation (attenuation + low-pass)
    device_sim         recording-device simulation (band-limit + mild noise)
"""

from __future__ import annotations

import numpy as np


def _fit_length(y: np.ndarray, length: int) -> np.ndarray:
    if y.shape[0] < length:
        return np.pad(y, (0, length - y.shape[0]), mode="constant")
    return y[:length]


def add_noise(y: np.ndarray, rng: np.random.Generator, snr_db: float = 15.0) -> np.ndarray:
    """Add Gaussian noise at an approximate signal-to-noise ratio."""
    signal_power = np.mean(y ** 2) + 1e-12
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = rng.normal(0.0, np.sqrt(noise_power), size=y.shape).astype(np.float32)
    return (y + noise).astype(np.float32)


def time_shift(y: np.ndarray, rng: np.random.Generator, max_frac: float = 0.25) -> np.ndarray:
    shift = int(rng.uniform(-max_frac, max_frac) * y.shape[0])
    return np.roll(y, shift).astype(np.float32)


def pitch_shift(y: np.ndarray, sr: int, rng: np.random.Generator, max_steps: float = 3.0) -> np.ndarray:
    import librosa

    steps = float(rng.uniform(-max_steps, max_steps))
    out = librosa.effects.pitch_shift(y=y, sr=sr, n_steps=steps)
    return _fit_length(out.astype(np.float32), y.shape[0])


def time_stretch(y: np.ndarray, rng: np.random.Generator, rate_range=(0.85, 1.15)) -> np.ndarray:
    import librosa

    rate = float(rng.uniform(*rate_range))
    out = librosa.effects.time_stretch(y=y, rate=rate)
    return _fit_length(out.astype(np.float32), y.shape[0])


def volume_adjust(y: np.ndarray, rng: np.random.Generator, gain_range=(0.5, 1.6)) -> np.ndarray:
    gain = float(rng.uniform(*gain_range))
    out = np.clip(y * gain, -1.0, 1.0)
    return out.astype(np.float32)


def reverb(y: np.ndarray, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Simple limited reverb: sum of a few decaying delayed copies."""
    delay_ms = rng.uniform(20, 60)
    decay = rng.uniform(0.2, 0.4)
    delay = int(sr * delay_ms / 1000.0)
    out = y.copy()
    tap = y.copy()
    for _ in range(3):
        tap = np.roll(tap, delay) * decay
        out = out + tap
    out = np.clip(out, -1.0, 1.0)
    return _fit_length(out.astype(np.float32), y.shape[0])


def distance_sim(y: np.ndarray, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Simulate a more distant source: attenuate + soft low-pass (moving average)."""
    atten = float(rng.uniform(0.3, 0.7))
    win = int(rng.integers(3, 9))
    kernel = np.ones(win, dtype=np.float32) / win
    filtered = np.convolve(y * atten, kernel, mode="same")
    return _fit_length(filtered.astype(np.float32), y.shape[0])


def device_sim(y: np.ndarray, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Simulate a different recording device: mild band-limiting + faint noise."""
    win = int(rng.integers(2, 5))
    kernel = np.ones(win, dtype=np.float32) / win
    band = np.convolve(y, kernel, mode="same")
    band = add_noise(band, rng, snr_db=float(rng.uniform(20, 30)))
    return _fit_length(band.astype(np.float32), y.shape[0])


def pitch_up(y: np.ndarray, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Shift pitch UP by 2-5 semitones (higher-frequency variant)."""
    import librosa

    steps = float(rng.uniform(2.0, 5.0))
    out = librosa.effects.pitch_shift(y=y, sr=sr, n_steps=steps)
    return _fit_length(out.astype(np.float32), y.shape[0])


def pitch_down(y: np.ndarray, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Shift pitch DOWN by 2-5 semitones (lower-frequency variant)."""
    import librosa

    steps = float(rng.uniform(2.0, 5.0))
    out = librosa.effects.pitch_shift(y=y, sr=sr, n_steps=-steps)
    return _fit_length(out.astype(np.float32), y.shape[0])


def speed_change(y: np.ndarray, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Speed up / slow down by resampling (changes tempo AND pitch)."""
    factor = float(rng.uniform(0.8, 1.25))
    idx = np.round(np.arange(0, len(y), factor)).astype(int)
    idx = idx[idx < len(y)]
    out = y[idx] if idx.size else y
    return _fit_length(out.astype(np.float32), y.shape[0])


def _biquad(y, sr, cutoff, kind):
    """First-order high/low-pass filter (dependency-free)."""
    rc = 1.0 / (2 * np.pi * cutoff)
    dt = 1.0 / sr
    out = np.zeros_like(y)
    if kind == "low":
        alpha = dt / (rc + dt)
        out[0] = y[0] * alpha
        for i in range(1, len(y)):
            out[i] = out[i - 1] + alpha * (y[i] - out[i - 1])
    else:  # high-pass
        alpha = rc / (rc + dt)
        out[0] = y[0]
        for i in range(1, len(y)):
            out[i] = alpha * (out[i - 1] + y[i] - y[i - 1])
    return out.astype(np.float32)


def freq_filter(y: np.ndarray, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Apply a random low-pass or high-pass filter (frequency-content variation)."""
    if rng.random() < 0.5:
        cutoff = float(rng.uniform(1500, 5000))   # low-pass: keep lows
        out = _biquad(y, sr, cutoff, "low")
    else:
        cutoff = float(rng.uniform(200, 1200))    # high-pass: keep highs
        out = _biquad(y, sr, cutoff, "high")
    return _fit_length(out, y.shape[0])


# Registry of augmentations that need only (y, rng) vs (y, sr, rng).
_NEEDS_SR = {
    "pitch_shift", "reverb", "distance_sim", "device_sim",
    "pitch_up", "pitch_down", "speed_change", "freq_filter",
}
_AUG_FUNCS = {
    "add_noise": add_noise,
    "time_shift": time_shift,
    "pitch_shift": pitch_shift,
    "pitch_up": pitch_up,
    "pitch_down": pitch_down,
    "time_stretch": time_stretch,
    "speed_change": speed_change,
    "volume_adjust": volume_adjust,
    "reverb": reverb,
    "distance_sim": distance_sim,
    "device_sim": device_sim,
    "freq_filter": freq_filter,
}


def augment(y: np.ndarray, sr: int, name: str, rng: np.random.Generator) -> np.ndarray:
    """Apply a single named augmentation."""
    func = _AUG_FUNCS[name]
    if name in _NEEDS_SR:
        return func(y, sr, rng)
    return func(y, rng)


def all_augmentation_names() -> list[str]:
    return list(_AUG_FUNCS.keys())
