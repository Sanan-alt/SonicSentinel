"""Audio augmentation scripts (SRS submission section 2 / requirement xix).

Implementation: ``src/sonic/augmentation.py`` (noise, time shift, pitch shift
up/down, time stretch, speed change, volume, reverb, distance/device simulation,
frequency filtering). Applied to TRAIN-split clips only. Re-exported here so the
augmentation code is discoverable under the SRS-required folder name.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sonic.augmentation import (  # noqa: E402,F401
    all_augmentation_names,
    augment,
)

__all__ = ["augment", "all_augmentation_names"]
