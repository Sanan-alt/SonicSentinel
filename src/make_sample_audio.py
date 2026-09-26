"""Refresh sample_audio/ demo clips so each file matches its label.

The shipped sample_audio/gunshot.mp3 was actually a copy of the aggression clip.
This writes a correctly-labelled synthetic gunshot and panic_scream demo clip
(and leaves the real ones - glass, alarm, animal, etc. - untouched).

Usage: python src/make_sample_audio.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_synth_samples import gunshot, panic_scream, SR  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "sample_audio"


def main() -> None:
    SAMPLE_DIR.mkdir(exist_ok=True)
    rng = np.random.default_rng(7)
    # Overwrite the mislabelled gunshot.mp3 placeholder with a real gunshot .wav.
    old_mp3 = SAMPLE_DIR / "gunshot.mp3"
    if old_mp3.exists():
        old_mp3.unlink()
    sf.write(SAMPLE_DIR / "gunshot.wav", gunshot(rng), SR)
    sf.write(SAMPLE_DIR / "panic_scream.wav", panic_scream(rng), SR)
    print(f"Wrote correctly-labelled demo clips into {SAMPLE_DIR}:")
    print("  gunshot.wav, panic_scream.wav")


if __name__ == "__main__":
    main()
