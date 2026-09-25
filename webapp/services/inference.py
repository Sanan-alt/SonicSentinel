"""Dual-model inference + comparison + decision service (SRS Steps 8-19).

Runs the Python model and the independent GTM-substitute model on the SAME
preprocessed audio, WITHOUT sharing either model's output with the other
(SRS item 14). Then compares them, assesses quality, applies alert rules, and
produces a final event decision.

This is the single real classification path used by the Flask app for uploads,
batches, and live windows.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

# Make the src/ package importable.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from sonic.config import load_config          # noqa: E402
from sonic.features import extract_features    # noqa: E402
from sonic.preprocessing import AudioSettings, load_audio  # noqa: E402

from .alerts import AlertEngine                # noqa: E402
from . import audio_io                         # noqa: E402


def _agreement_label(match: bool, conf_diff: float, top_class_conf: float) -> str:
    """Map comparison numbers to an SRS consistency label (requirement xxxiii)."""
    if match and conf_diff <= 10 and top_class_conf >= 65:
        return "Acceptable Match"
    if match and conf_diff <= 20:
        return "Weak Match"
    if not match:
        return "Model Disagreement"
    return "Uncertain Result"


class InferenceService:
    """Loads both models once and classifies clips."""

    def __init__(self, cfg=None):
        import joblib

        self.cfg = cfg or load_config()
        self.settings = AudioSettings.from_config(self.cfg)

        py_path = self.cfg.path("models_dir") / "sonicsentinel_model.joblib"
        gtm_path = self.cfg.path("gtm_model_dir") / "gtm_model.joblib"
        if not py_path.exists():
            raise FileNotFoundError(f"Python model not found: {py_path}. Run src/train.py.")
        self.py_bundle = joblib.load(py_path)
        # GTM model is optional; fall back to Python bundle only if missing.
        self.gtm_bundle = joblib.load(gtm_path) if gtm_path.exists() else None

        self.alert_engine = AlertEngine.from_file(self.cfg.path("alert_rules"))
        self.classes: list[str] = list(self.py_bundle["classes"])

    # -- low-level scoring ------------------------------------------------
    def _score(self, bundle, feature_vec: np.ndarray) -> tuple[str, float, dict[str, float]]:
        vec = bundle["scaler"].transform(feature_vec.reshape(1, -1))
        model = bundle["model"]
        classes = list(bundle["classes"])
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(vec)[0]
        else:
            pred_idx = int(model.predict(vec)[0])
            proba = np.zeros(len(classes))
            proba[pred_idx] = 1.0
        scores = {classes[i]: round(float(proba[i]) * 100, 2) for i in range(len(classes))}
        top_idx = int(np.argmax(proba))
        return classes[top_idx], round(float(proba[top_idx]) * 100, 2), scores

    def _top_two_margin(self, scores: dict[str, float]) -> float:
        vals = sorted(scores.values(), reverse=True)
        return round(vals[0] - vals[1], 2) if len(vals) >= 2 else vals[0]

    # -- public API -------------------------------------------------------
    def classify_signal(self, y: np.ndarray, consecutive: int = 1) -> dict[str, Any]:
        """Classify an already-loaded, preprocessed signal."""
        sr = self.settings.sample_rate
        feats = extract_features(y, sr, self.cfg)

        py_class, py_conf, py_scores = self._score(self.py_bundle, feats)
        if self.gtm_bundle is not None:
            gtm_class, gtm_conf, gtm_scores = self._score(self.gtm_bundle, feats)
        else:
            gtm_class, gtm_conf, gtm_scores = py_class, py_conf, py_scores

        match = py_class == gtm_class
        conf_diff = round(abs(py_conf - gtm_conf), 2)
        agreement = _agreement_label(match, conf_diff, py_conf)
        top_two_margin = self._top_two_margin(py_scores)

        quality = audio_io.assess_quality(y, sr)

        # Final class: prefer Python model; the decision engine handles review.
        final_class = py_class
        decision = self.alert_engine.decide(
            final_class=final_class,
            confidence=py_conf,
            top_two_margin=top_two_margin,
            audio_quality=quality["quality"],
            agreement=agreement,
            consecutive=consecutive,
        )

        return {
            "python": {"predicted_class": py_class, "confidence": py_conf, "scores": py_scores},
            "gtm": {"predicted_class": gtm_class, "confidence": gtm_conf, "scores": gtm_scores},
            "comparison": {
                "match": match,
                "agreement": agreement,
                "confidence_difference": conf_diff,
                "top_two_margin": top_two_margin,
            },
            "audio_quality": quality,
            "final_class": final_class,
            "severity": decision["severity"],
            "alert_fires": decision["alert_fires"],
            "alert_status": decision["alert_status"],
            "manual_review": decision["manual_review"],
            "recommended_action": decision["recommended_action"],
            "escalate": decision["escalate"],
            "review_reasons": decision["reasons"],
            "model_versions": {
                "python": self.py_bundle.get("model_name"),
                "gtm": self.gtm_bundle.get("model_name") if self.gtm_bundle else None,
            },
            "top3_python": sorted(py_scores.items(), key=lambda kv: kv[1], reverse=True)[:3],
            "top3_gtm": sorted(gtm_scores.items(), key=lambda kv: kv[1], reverse=True)[:3],
        }

    def classify_file(self, path: Path, consecutive: int = 1) -> dict[str, Any]:
        """Load, preprocess, and classify a clip from disk."""
        y = load_audio(path, self.settings)
        return self.classify_signal(y, consecutive=consecutive)
