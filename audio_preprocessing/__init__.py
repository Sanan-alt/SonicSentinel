"""Audio preprocessing scripts (SRS submission section 2).

The implementation lives in ``src/sonic/preprocessing.py`` (single source of
truth used by both training and the web app). This package re-exports it so the
preprocessing code is discoverable under the SRS-required folder name.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sonic.preprocessing import (  # noqa: E402,F401
    AudioSettings,
    load_audio,
    load_raw,
    segment_signal,
)

__all__ = ["AudioSettings", "load_audio", "load_raw", "segment_signal"]
