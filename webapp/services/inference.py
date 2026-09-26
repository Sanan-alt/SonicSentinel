"""Dual-model inference + comparison + decision service (SRS Steps 8-19).

Runs the Python model and, independently, the real Google Teachable Machine
(GTM) model (loaded via ``gtm_service.py`` from a human-exported artefact) on
the SAME preprocessed audio, WITHOUT sharing either model's output with the
other (SRS item 14). Then compares them, assesses quality, applies alert rules,
and produces a final event decision.

If no valid GTM export is configured, GTM predictions are reported as "not
available" and the comparison is marked BLOCKED — the Python model is never
presented as GTM (SRS anti-shortcut rules).

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
        if not py_path.exists():
            raise FileNotFoundError(f"Python model not found: {py_path}. Run src/train.py.")
        self.py_bundle = joblib.load(py_path)
        self.classes: list[str] = list(self.py_bundle["classes"])

        self.alert_engine = AlertEngine.from_file(self.cfg.path("alert_rules"))

        # Google Teachable Machine (SRS Step 9-11). This is a REAL, human-exported
        # GTM audio model loaded from models/gtm/export/. It is NOT the Python
        # model in disguise: when no valid export is present the service reports
        # GTM_NOT_CONFIGURED and the comparison is marked BLOCKED. The Python
        # prediction is NEVER copied into the GTM result (SRS anti-shortcut).
        try:
            from .gtm_service import GTMService
            self.gtm = GTMService(self.cfg.path("gtm_model_dir") / "export", self.classes)
        except Exception:  # noqa: BLE001
            self.gtm = None

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

        # GTM runs independently on the SAME preprocessed signal. It NEVER
        # receives the Python prediction. If no valid GTM model is configured,
        # gtm_result is None and the comparison is BLOCKED (not faked).
        gtm_result = self.gtm.predict(y, sr) if (self.gtm and self.gtm.configured) else None
        gtm_available = gtm_result is not None

        if gtm_available:
            gtm_class = gtm_result["predicted_class"]
            gtm_conf = gtm_result["confidence"]
            gtm_scores = gtm_result["scores"]
            match = py_class == gtm_class
            conf_diff = round(abs(py_conf - gtm_conf), 2)
            agreement = _agreement_label(match, conf_diff, py_conf)
        else:
            gtm_class, gtm_conf, gtm_scores = None, None, {}
            match = None
            conf_diff = None
            agreement = "GTM Not Available"

        top_two_margin = self._top_two_margin(py_scores)

        # Overlapping-sound detection (SRS requirement xxxix): more than one
        # class receives significant confidence.
        significant = [c for c, s in py_scores.items() if s >= 25.0]
        overlapping = len(significant) >= 2
        overlap_classes = sorted(
            [(c, py_scores[c]) for c in significant], key=lambda kv: kv[1], reverse=True
        )

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

        gtm_state = self.gtm.state if self.gtm else "GTM_NOT_CONFIGURED"
        return {
            "python": {"predicted_class": py_class, "confidence": py_conf, "scores": py_scores},
            "gtm": {
                "predicted_class": gtm_class,
                "confidence": gtm_conf,
                "scores": gtm_scores,
                "available": gtm_available,
                "state": gtm_state,
            },
            "comparison": {
                "match": match,
                "agreement": agreement,
                "confidence_difference": conf_diff,
                "top_two_margin": top_two_margin,
                # When GTM is not configured the comparison cannot be performed;
                # it is BLOCKED, never silently satisfied with the Python result.
                "status": "OK" if gtm_available else "BLOCKED — GTM model unavailable",
            },
            "overlap": {
                "overlapping": overlapping,
                "classes": overlap_classes,
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
                "gtm": "Google Teachable Machine" if gtm_available else None,
            },
            "top3_python": sorted(py_scores.items(), key=lambda kv: kv[1], reverse=True)[:3],
            "top3_gtm": (sorted(gtm_scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
                         if gtm_available else []),
        }

    def classify_file(self, path: Path, consecutive: int = 1) -> dict[str, Any]:
        """Load, preprocess, and classify a clip from disk.

        For clips longer than the fixed window, the clip is segmented (SRS xv):
        each segment is classified, per-segment results are attached, and the
        overall result uses the highest-severity / highest-confidence segment.
        """
        from sonic.preprocessing import load_raw, segment_signal

        raw = load_raw(path, self.settings)
        segments = list(segment_signal(raw, self.settings))

        if len(segments) <= 1:
            result = self.classify_signal(segments[0][0] if segments else load_audio(path, self.settings),
                                          consecutive=consecutive)
            result["segments"] = [{
                "start": segments[0][1] if segments else 0.0,
                "end": segments[0][2] if segments else 0.0,
                "class": result["final_class"],
                "confidence": result["python"]["confidence"],
            }]
            return result

        seg_results = []
        for seg, start, end in segments:
            r = self.classify_signal(seg, consecutive=consecutive)
            seg_results.append((r, start, end))

        severity_rank = {"Critical": 5, "High": 4, "Medium": 3, "Low": 2, "Informational": 1}
        best = max(seg_results, key=lambda t: (
            severity_rank.get(t[0]["severity"], 0), t[0]["python"]["confidence"]))
        result = best[0]
        result["segments"] = [{
            "start": s, "end": e, "class": r["final_class"],
            "confidence": r["python"]["confidence"], "severity": r["severity"],
        } for (r, s, e) in seg_results]
        return result
