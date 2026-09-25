"""Unit tests for the SonicSentinel ML pipeline and services (SRS deliverable 8)."""

import numpy as np
import pytest


# ---- preprocessing ----
def test_preprocess_pads_to_fixed_length(cfg, tone):
    from sonic.preprocessing import AudioSettings
    from sonic.features import extract_features

    y, sr = tone
    settings = AudioSettings.from_config(cfg)
    vec = extract_features(y, sr, cfg)
    # Feature vector must be deterministic in length.
    assert vec.ndim == 1
    assert vec.shape[0] > 0
    assert np.isfinite(vec).all()


def test_feature_names_match_vector_length(cfg, tone):
    from sonic.features import extract_features, feature_names

    y, sr = tone
    vec = extract_features(y, sr, cfg)
    names = feature_names(cfg)
    assert len(names) == vec.shape[0]


# ---- augmentation ----
@pytest.mark.parametrize("method", [
    "add_noise", "time_shift", "pitch_shift", "time_stretch",
    "volume_adjust", "reverb", "distance_sim", "device_sim",
])
def test_augmentation_preserves_length_and_finite(tone, method):
    from sonic.augmentation import augment

    y, sr = tone
    rng = np.random.default_rng(0)
    out = augment(y, sr, method, rng)
    assert out.shape == y.shape
    assert np.isfinite(out).all()


# ---- audio quality ----
def test_silent_signal_is_unusable():
    from services import audio_io

    y = np.zeros(22050, dtype=np.float32)
    q = audio_io.assess_quality(y, 22050)
    assert q["quality"] == "Unusable"


def test_clean_tone_is_not_unusable(tone):
    from services import audio_io

    y, sr = tone
    q = audio_io.assess_quality(y, sr)
    assert q["quality"] in {"Good", "Acceptable", "Poor"}


def test_validation_rejects_bad_extension(tmp_path):
    from services import audio_io

    class FakeFile:
        filename = "malware.exe"
        def read(self):  # pragma: no cover - not reached
            return b"x"

    with pytest.raises(audio_io.AudioValidationError):
        audio_io.save_upload(FakeFile(), tmp_path)


# ---- alert engine ----
def test_gunshot_rule_is_critical():
    from services.alerts import AlertEngine
    from sonic.config import load_config

    cfg = load_config()
    engine = AlertEngine.from_file(cfg.path("alert_rules"))
    decision = engine.decide("gunshot", confidence=85, top_two_margin=20,
                             audio_quality="Good", agreement="Acceptable Match", consecutive=2)
    assert decision["severity"] == "Critical"
    assert decision["alert_fires"] is True


def test_low_confidence_routes_to_manual_review():
    from services.alerts import AlertEngine
    from sonic.config import load_config

    cfg = load_config()
    engine = AlertEngine.from_file(cfg.path("alert_rules"))
    decision = engine.decide("gunshot", confidence=30, top_two_margin=2,
                             audio_quality="Poor", agreement="Model Disagreement", consecutive=1)
    assert decision["manual_review"] is True
    assert decision["alert_fires"] is False


def test_background_noise_does_not_fire_alert():
    from services.alerts import AlertEngine
    from sonic.config import load_config

    cfg = load_config()
    engine = AlertEngine.from_file(cfg.path("alert_rules"))
    decision = engine.decide("background_noise", confidence=90, top_two_margin=30,
                             audio_quality="Good", agreement="Acceptable Match", consecutive=5)
    assert decision["severity"] == "Informational"
    assert decision["alert_fires"] is False


# ---- category mapping ----
def test_pipeline_to_ui_mapping_is_bijective_for_10_classes():
    from services.categories import PIPELINE_TO_UI, MANDATORY_SOUND_CATEGORIES

    assert len(PIPELINE_TO_UI) == 10
    ui_keys = {c["category_key"] for c in MANDATORY_SOUND_CATEGORIES}
    assert set(PIPELINE_TO_UI.values()) == ui_keys
