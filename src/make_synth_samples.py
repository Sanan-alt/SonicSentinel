"""Generate placeholder audio for SRS classes that have no real recordings yet.

Some mandatory classes (e.g. gunshot, panic_scream) ship with NO real audio in
this repository. Training a 10-class model still needs at least a few examples
per class, so this script writes acoustically-plausible SYNTHETIC clips into the
dataset folders for any class that is currently empty.

These clips are clearly synthetic and are tagged ``synthetic`` in the dataset
metadata (see organize.py, which records the ``source`` folder key). Replace
them with real, ethically-sourced recordings whenever available: just drop real
files into the same ``Dataset/<Folder>`` and re-run the pipeline - the synthetic
placeholders can then be deleted.

Usage:
    python src/make_synth_samples.py            # fill only empty classes
    python src/make_synth_samples.py --count 60 # N clips per empty class
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sonic.config import load_config  # noqa: E402
from sonic.labels import MP3_FOLDER_TO_SRS  # noqa: E402

SR = 22050
DUR = 5.0


def _env(n: int, attack: float, decay: float) -> np.ndarray:
    """A simple attack/decay amplitude envelope of length n."""
    a = int(n * attack)
    d = n - a
    return np.concatenate([np.linspace(0, 1, max(a, 1)),
                           np.exp(-np.linspace(0, 6, max(d, 1)) / decay)])


def gunshot(rng: np.random.Generator) -> np.ndarray:
    """Impulsive muzzle blast: a burst of shaped noise with a sharp transient."""
    n = int(SR * DUR)
    y = np.zeros(n, dtype=np.float32)
    # 1-3 shots at random offsets
    for _ in range(rng.integers(1, 4)):
        start = rng.integers(0, int(n * 0.7))
        blen = int(SR * rng.uniform(0.08, 0.18))
        burst = rng.normal(0, 1, blen).astype(np.float32)
        # sharp transient + fast decay
        burst *= np.exp(-np.linspace(0, 12, blen))
        # low-pass-ish weighting for the "boom"
        burst = np.convolve(burst, np.ones(8) / 8, mode="same").astype(np.float32)
        end = min(start + blen, n)
        y[start:end] += burst[: end - start]
    y = np.clip(y * rng.uniform(1.2, 2.0), -1.0, 1.0)
    return y


def panic_scream(rng: np.random.Generator) -> np.ndarray:
    """High-pitch human distress: a rising, vibrato, harmonic-rich tone in noise."""
    n = int(SR * DUR)
    t = np.arange(n) / SR
    f0 = rng.uniform(500, 1100)                    # high fundamental
    glide = np.linspace(1.0, rng.uniform(1.1, 1.6), n)
    vibrato = 1 + 0.03 * np.sin(2 * np.pi * rng.uniform(4, 8) * t)
    phase = 2 * np.pi * np.cumsum(f0 * glide * vibrato) / SR
    y = np.zeros(n, dtype=np.float32)
    for k, amp in enumerate([1.0, 0.5, 0.3, 0.15], start=1):
        y += amp * np.sin(k * phase)
    y = y.astype(np.float32)
    y += rng.normal(0, 0.05, n).astype(np.float32)  # breath noise
    y *= _env(n, 0.1, 1.5).astype(np.float32)
    y = np.clip(y / (np.max(np.abs(y)) + 1e-9) * rng.uniform(0.6, 0.9), -1.0, 1.0)
    return y


GENERATORS = {
    "gunshot": gunshot,
    "panic_scream": panic_scream,
}

# SRS class -> the Dataset folder key that should receive synthetic clips.
CLASS_TO_FOLDER = {v: k for k, v in MP3_FOLDER_TO_SRS.items()}


def main() -> None:
    count = 40
    if "--count" in sys.argv:
        count = int(sys.argv[sys.argv.index("--count") + 1])

    cfg = load_config()

    rng = np.random.default_rng(1234)
    made = 0
    for cls, gen in GENERATORS.items():
        folder_key = CLASS_TO_FOLDER.get(cls, cls)
        # Use the exact folder path configured for this key (handles spaces).
        folder = cfg.path("mp3_folders", folder_key)
        folder.mkdir(parents=True, exist_ok=True)
        # Only fill if the folder has no non-synthetic audio worth keeping.
        existing = [p for p in folder.glob("*.wav") if p.name.startswith("synthetic_")]
        real = [p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
                and not p.name.startswith("synthetic_")]
        if real:
            print(f"{cls}: {len(real)} real clip(s) present -> skipping synthetic fill.")
            continue
        for p in existing:  # refresh
            p.unlink()
        for i in range(count):
            y = gen(rng)
            out = folder / f"synthetic_{cls}_{i:03d}.wav"
            sf.write(out, y, SR)
            made += 1
        print(f"{cls}: wrote {count} synthetic clips into {folder}")

    print(f"\nDone. {made} synthetic clips created. Re-run: python src/run_pipeline.py --force")


if __name__ == "__main__":
    main()
