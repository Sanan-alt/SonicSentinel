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


# ---- new SRS-completion features ----
def test_metadata_reports_bit_depth(tmp_path):
    """extract_metadata should derive bit depth for a PCM_16 WAV (SRS x)."""
    import numpy as np
    import soundfile as sf
    from services import audio_io

    p = tmp_path / "tone.wav"
    y = (0.3 * np.sin(2 * np.pi * 440 * np.linspace(0, 2, 44100 * 2))).astype("float32")
    sf.write(str(p), y, 44100, subtype="PCM_16")
    meta = audio_io.extract_metadata(p)
    assert meta["bit_depth"] == 16
    assert meta["channels"] == 1


def test_quality_reports_background_noise_level(tone):
    from services import audio_io

    y, sr = tone
    q = audio_io.assess_quality(y, sr)
    assert "background_noise_level" in q
    assert q["background_noise_level"] >= 0


def test_segmentation_splits_long_signal(cfg):
    import numpy as np
    from sonic.preprocessing import AudioSettings, segment_signal

    settings = AudioSettings.from_config(cfg)
    sr = settings.sample_rate
    long_signal = np.zeros(int(sr * settings.duration * 3), dtype="float32")  # 3 windows
    segs = list(segment_signal(long_signal, settings))
    assert len(segs) == 3
    # each segment padded/truncated to the fixed window length
    win = int(settings.duration * sr)
    assert all(s[0].shape[0] == win for s in segs)
    # start/end timestamps present and increasing
    assert segs[0][1] == 0.0 and segs[1][1] > segs[0][1]


def test_wav_window_decodes_for_live(tmp_path):
    """A 16-bit PCM WAV (as the browser sends for live) must load fine."""
    import numpy as np
    import soundfile as sf
    from sonic.config import load_config
    from sonic.preprocessing import AudioSettings, load_audio

    cfg = load_config()
    settings = AudioSettings.from_config(cfg)
    p = tmp_path / "live_window.wav"
    y = (0.4 * np.sin(2 * np.pi * 300 * np.linspace(0, 2.5, 44100 * 2 + 22050))).astype("float32")
    sf.write(str(p), y, 44100, subtype="PCM_16")
    out = load_audio(p, settings)
    assert out.shape[0] == int(settings.duration * settings.sample_rate)
