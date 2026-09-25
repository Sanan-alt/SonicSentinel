"""Audio upload validation, storage, and metadata extraction.

Covers SRS Step 3 (validation), Step 13 (quality), and requirement x
(metadata extraction). Works on the real audio bytes, not client metadata.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

SUPPORTED_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
MAX_SIZE_BYTES = 25 * 1024 * 1024   # 25 MB
MAX_DURATION_S = 180.0              # 3 minutes
MIN_DURATION_S = 0.3


class AudioValidationError(Exception):
    """Raised when an uploaded clip is rejected."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_upload(file_storage, uploads_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Validate and save a Werkzeug FileStorage. Returns (path, info)."""
    from werkzeug.utils import secure_filename

    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise AudioValidationError("No filename provided.")
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise AudioValidationError(f"Unsupported format '{ext}'. Allowed: {sorted(SUPPORTED_EXTS)}")

    data = file_storage.read()
    if not data:
        raise AudioValidationError("File is empty.")
    if len(data) > MAX_SIZE_BYTES:
        raise AudioValidationError(f"File too large ({len(data)/1e6:.1f} MB > 25 MB).")

    uploads_dir.mkdir(parents=True, exist_ok=True)
    digest = sha256_bytes(data)
    stored_name = f"{digest[:12]}_{filename}"
    dest = uploads_dir / stored_name
    dest.write_bytes(data)

    info = {
        "filename": filename,
        "stored_path": str(dest),
        "file_size": len(data),
        "sha256": digest,
        "upload_time": datetime.now(timezone.utc).isoformat(),
    }
    return dest, info


def extract_metadata(path: Path) -> dict[str, Any]:
    """Read audio metadata + basic integrity (SRS requirement x)."""
    try:
        with sf.SoundFile(str(path)) as f:
            channels = f.channels
            sr = f.samplerate
            frames = len(f)
            subtype = f.subtype
        duration = frames / float(sr) if sr else 0.0
        readable = True
    except Exception:
        # soundfile can't read mp3/m4a directly on some systems; fall back to librosa.
        try:
            import librosa

            y, sr = librosa.load(str(path), sr=None, mono=False)
            channels = 1 if y.ndim == 1 else y.shape[0]
            duration = librosa.get_duration(y=y, sr=sr)
            frames = int(duration * sr)
            subtype = "decoded"
            readable = True
        except Exception as error:  # noqa: BLE001
            raise AudioValidationError(f"Could not decode audio: {error}")

    if duration < MIN_DURATION_S:
        raise AudioValidationError(f"Recording too short ({duration:.2f}s).")
    if duration > MAX_DURATION_S:
        raise AudioValidationError(f"Recording too long ({duration:.1f}s > {MAX_DURATION_S:.0f}s).")

    # Derive bit depth from the subtype where possible (SRS requirement x).
    bit_depth_map = {
        "PCM_16": 16, "PCM_24": 24, "PCM_32": 32, "PCM_S8": 8, "PCM_U8": 8,
        "FLOAT": 32, "DOUBLE": 64,
    }
    bit_depth = bit_depth_map.get(str(subtype).upper())

    return {
        "duration": round(duration, 3),
        "sample_rate": sr,
        "channels": channels,
        "frames": frames,
        "subtype": subtype,
        "bit_depth": bit_depth,
        "readable": readable,
    }


def assess_quality(y: np.ndarray, sr: int) -> dict[str, Any]:
    """Classify audio quality: Good / Acceptable / Poor / Unusable (SRS Step 13)."""
    if y.size == 0:
        return {"quality": "Unusable", "reason": "empty", "snr_db": 0.0,
                "clipping_ratio": 0.0, "rms": 0.0}

    peak = float(np.max(np.abs(y)))
    rms = float(np.sqrt(np.mean(y ** 2)))
    clipping_ratio = float(np.mean(np.abs(y) > 0.99) * 100.0)

    # Rough SNR: signal frames vs. quiet frames.
    frame = max(1, sr // 50)
    energies = np.array([
        np.mean(y[i:i + frame] ** 2) for i in range(0, len(y) - frame, frame)
    ]) if len(y) > frame else np.array([rms ** 2])
    energies = energies[energies > 0]
    if energies.size:
        noise_floor = np.percentile(energies, 10) + 1e-10
        signal = np.percentile(energies, 90)
        snr_db = float(10 * np.log10(signal / noise_floor))
    else:
        snr_db = 0.0

    # Decide.
    if peak < 1e-3 or rms < 1e-4:
        quality, reason = "Unusable", "silent"
    elif clipping_ratio > 5.0:
        quality, reason = "Poor", "severe clipping"
    elif snr_db < 8.0:
        quality, reason = "Poor", "low SNR"
    elif snr_db < 15.0 or clipping_ratio > 1.0:
        quality, reason = "Acceptable", "moderate noise/clipping"
    else:
        quality, reason = "Good", "clean"

    # Background-noise level estimate (SRS requirement xiv): the quiet-frame
    # energy floor, expressed on a 0-100 relative scale.
    if energies.size:
        noise_floor = float(np.percentile(energies, 10))
        background_noise_level = round(min(100.0, noise_floor ** 0.5 * 300), 1)
    else:
        background_noise_level = 0.0

    return {
        "quality": quality,
        "reason": reason,
        "snr_db": round(snr_db, 1),
        "clipping_ratio": round(clipping_ratio, 2),
        "rms": round(rms, 4),
        "background_noise_level": background_noise_level,
    }
