"""SRS test-case coverage (section 8).

Covers the runnable categories: audio formats, silence, clipping, noise,
preprocessing, feature extraction, alert rules, duplicate detection,
low-confidence handling, overlap, database, security, negative/boundary.

Mic and real-GTM tests are skipped with a clear reason (need a device / a
browser-exported GTM model) — they are not faked.
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "webapp"))

from sonic.config import load_config          # noqa: E402
from sonic.features import extract_features    # noqa: E402
from sonic.preprocessing import AudioSettings, load_audio  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def _write_wav(path, y, sr=22050):
    y16 = np.clip(y, -1, 1)
    y16 = (y16 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(y16.tobytes())


# ---- Audio format / preprocessing ----
def test_preprocessing_fixed_length(cfg, tmp_path):
    s = AudioSettings.from_config(cfg)
    p = tmp_path / "tone.wav"
    _write_wav(p, 0.5 * np.sin(2 * np.pi * 440 * np.arange(s.sample_rate * 3) / s.sample_rate), s.sample_rate)
    y = load_audio(p, s)
    assert len(y) == int(s.duration * s.sample_rate)  # padded/truncated to fixed length
    assert y.dtype == np.float32


def test_silence_rejected(cfg, tmp_path):
    s = AudioSettings.from_config(cfg)
    p = tmp_path / "silent.wav"
    _write_wav(p, np.zeros(s.sample_rate * 2, dtype=np.float32), s.sample_rate)
    with pytest.raises(ValueError):
        load_audio(p, s)


def test_feature_vector_deterministic_length(cfg, tmp_path):
    s = AudioSettings.from_config(cfg)
    p = tmp_path / "t.wav"
    _write_wav(p, 0.3 * np.sin(2 * np.pi * 300 * np.arange(s.sample_rate * 2) / s.sample_rate), s.sample_rate)
    y = load_audio(p, s)
    v1 = extract_features(y, s.sample_rate, cfg)
    v2 = extract_features(y, s.sample_rate, cfg)
    assert v1.shape == v2.shape and v1.ndim == 1
    assert np.allclose(v1, v2)  # deterministic


# ---- Audio quality: clipping / noise ----
def test_clipping_detected(cfg):
    from services.audio_io import assess_quality
    sr = 22050
    clipped = np.ones(sr, dtype=np.float32)  # fully clipped
    q = assess_quality(clipped, sr)
    assert q["clipping_ratio"] > 0


def test_noise_quality_label(cfg):
    from services.audio_io import assess_quality
    sr = 22050
    noisy = (np.random.default_rng(0).normal(0, 0.3, sr)).astype(np.float32)
    q = assess_quality(noisy, sr)
    assert q["quality"] in {"Good", "Acceptable", "Poor", "Unusable"}


# ---- Validation: negative / boundary ----
def test_unsupported_format_rejected():
    from services.audio_io import SUPPORTED_EXTS
    assert ".txt" not in SUPPORTED_EXTS
    assert ".exe" not in SUPPORTED_EXTS


def test_duration_bounds_exist():
    from services import audio_io
    assert audio_io.MAX_DURATION_S > audio_io.MIN_DURATION_S > 0
    assert audio_io.MAX_SIZE_BYTES > 0


# ---- Alert rules: severity + low confidence + agreement ----
def test_low_confidence_routes_to_review(cfg):
    from services.alerts import AlertEngine
    eng = AlertEngine.from_file(cfg.path("alert_rules"))
    d = eng.decide("gunshot", confidence=20, top_two_margin=2,
                   audio_quality="Poor", agreement="Model Disagreement", consecutive=1)
    assert d["manual_review"] is True
    assert d["alert_fires"] is False


def test_model_disagreement_flagged(cfg):
    from services.alerts import AlertEngine
    eng = AlertEngine.from_file(cfg.path("alert_rules"))
    d = eng.decide("glass_breaking", confidence=90, top_two_margin=40,
                   audio_quality="Good", agreement="Model Disagreement")
    assert "model disagreement" in d["reasons"]


# ---- Database + security ----
def test_database_crud_and_hashing(tmp_path):
    from services.database import Database
    db = Database(tmp_path / "t.db")
    db.init_db(seed=False)
    u = db.create_user("T", "t@example.com", "pw123", "administrator", "Ops")
    assert u is not None
    # password is hashed, not plaintext
    assert db.get_user_by_email("t@example.com")["password_hash"] != "pw123"
    assert db.verify_login("t@example.com", "pw123") is not None
    assert db.verify_login("t@example.com", "wrong") is None
    # duplicate email rejected
    assert db.create_user("T2", "t@example.com", "x", "administrator", "Ops") is None


def test_duplicate_detection_by_hash(tmp_path):
    from services.database import Database
    db = Database(tmp_path / "d.db")
    db.init_db(seed=False)
    eid = db.insert_event({"filename": "a.wav", "sha256": "deadbeef", "final_class": "gunshot",
                           "severity": "Critical"})
    found = db.find_by_hash("deadbeef")
    assert found and found["id"] == eid


# ---- Overlap / uncertainty (inference) ----
@pytest.mark.skipif(
    not (load_config().path("models_dir") / "sonicsentinel_model.joblib").exists(),
    reason="Python model not trained yet.")
def test_overlap_and_topk_present(cfg):
    from services.inference import InferenceService
    svc = InferenceService(cfg)
    sample = ROOT / "sample_audio" / "glass_breaking.wav"
    if not sample.exists():
        pytest.skip("sample missing")
    r = svc.classify_file(sample)
    assert "overlap" in r and "top3_python" in r
    assert isinstance(r["comparison"]["top_two_margin"], (int, float))


# ---- Microphone (cannot run headless) ----
@pytest.mark.skip(reason="Live microphone requires a device; verified manually via Live Monitor.")
def test_microphone_capture():
    pass


# ---- Real GTM (needs browser export) ----
@pytest.mark.skipif(
    True, reason="Requires a human-exported GTM model in models/gtm/export/ (browser-only).")
def test_gtm_real_prediction():
    pass
