"""Waveform and (Mel) spectrogram generation (SRS requirements xxi, xxii).

Renders PNGs from the real audio signal and returns their paths.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def _use_agg():
    import matplotlib
    matplotlib.use("Agg")


def generate_waveform(y: np.ndarray, sr: int, out_path: Path) -> Path:
    _use_agg()
    import matplotlib.pyplot as plt

    out_path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0, len(y) / sr, num=len(y))
    fig, ax = plt.subplots(figsize=(8, 2.2))
    ax.plot(t, y, color="#00e5ff", linewidth=0.6)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title("Waveform")
    ax.margins(x=0)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    for spine in ax.spines.values():
        spine.set_color("#30363d")
    ax.tick_params(colors="#8b949e")
    ax.xaxis.label.set_color("#8b949e")
    ax.yaxis.label.set_color("#8b949e")
    ax.title.set_color("#c9d1d9")
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def generate_spectrogram(y: np.ndarray, sr: int, out_path: Path,
                         n_mels: int = 128, n_fft: int = 2048, hop: int = 512) -> Path:
    _use_agg()
    import librosa
    import librosa.display
    import matplotlib.pyplot as plt

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, n_fft=n_fft, hop_length=hop)
    mel_db = librosa.power_to_db(mel, ref=np.max)

    fig, ax = plt.subplots(figsize=(8, 3))
    img = librosa.display.specshow(mel_db, sr=sr, hop_length=hop, x_axis="time",
                                   y_axis="mel", ax=ax, cmap="magma")
    ax.set_title("Mel Spectrogram")
    fig.colorbar(img, ax=ax, format="%+2.0f dB")
    fig.patch.set_facecolor("#0d1117")
    ax.title.set_color("#c9d1d9")
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path
