"""Feature-extraction scripts (SRS submission section 2).

Implementation: ``src/sonic/features.py`` (MFCC + delta, mel spectrogram,
chroma, ZCR, RMS, spectral centroid/bandwidth/roll-off). Re-exported here so the
feature-extraction code is discoverable under the SRS-required folder name.
The batch extractor CLI is ``src/extract_features.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sonic.features import extract_features, feature_names  # noqa: E402,F401

__all__ = ["extract_features", "feature_names"]
