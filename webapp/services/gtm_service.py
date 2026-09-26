"""Google Teachable Machine (GTM) integration service.

The SRS requires a SECOND, independently-trained audio model produced with
Google Teachable Machine (GTM). GTM is a browser-based tool: its audio model
cannot be created programmatically from Python, so the trained artefact must be
exported by a human and placed under ``models/gtm/export/``.

This service is deliberately HONEST about that boundary:

  * It NEVER presents the Python model as if it were GTM.
  * It NEVER copies Python predictions into the GTM result.
  * When no valid GTM export is present it reports state ``GTM_NOT_CONFIGURED``
    and returns "not available" for GTM predictions, so the comparison is
    marked BLOCKED rather than silently satisfied.

Explicit states (SRS anti-shortcut, item 45):
    GTM_NOT_CONFIGURED   no export folder / no model files
    GTM_MODEL_INVALID    files present but unreadable / wrong classes
    GTM_MODEL_READY      a valid export is loaded and usable

Supported export layouts under ``models/gtm/export/``:
  1. TensorFlow.js audio export: ``model.json`` + ``metadata.json`` (+ weights).
     metadata.json must contain a "labels"/"wordLabels" list of the 10 classes.
  2. Keras export: ``model.h5`` (or ``model.savedmodel/``) + ``labels.txt``.

If TensorFlow / tfjs runtimes are not installed, a valid-but-unloadable export
is reported as GTM_MODEL_READY (files validated) with ``runtime_available=False``
so the UI can explain exactly what is missing without faking a prediction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Canonical pipeline class order is owned by the config; GTM must use the SAME
# class names (SRS Step 9). We validate the export's labels against these.
STATE_NOT_CONFIGURED = "GTM_NOT_CONFIGURED"
STATE_INVALID = "GTM_MODEL_INVALID"
STATE_READY = "GTM_MODEL_READY"


class GTMService:
    """Loads and runs a real, human-exported Google Teachable Machine model."""

    def __init__(self, export_dir: Path | str, expected_classes: list[str]):
        self.export_dir = Path(export_dir)
        self.expected_classes = list(expected_classes)
        self.state = STATE_NOT_CONFIGURED
        self.detail = "No GTM export found."
        self.labels: list[str] = []
        self.runtime_available = False
        self._model = None
        self._layout = None
        self._validate()

    # -- discovery / validation ------------------------------------------
    def _validate(self) -> None:
        if not self.export_dir.exists():
            self.state = STATE_NOT_CONFIGURED
            self.detail = f"Export folder missing: {self.export_dir}"
            return

        files = {p.name.lower(): p for p in self.export_dir.iterdir() if p.is_file()}
        dirs = {p.name.lower(): p for p in self.export_dir.iterdir() if p.is_dir()}

        # Layout 1: TensorFlow.js (model.json + metadata.json)
        if "model.json" in files and "metadata.json" in files:
            self._layout = "tfjs"
            try:
                meta = json.loads(files["metadata.json"].read_text(encoding="utf-8"))
                self.labels = meta.get("labels") or meta.get("wordLabels") or []
            except Exception as error:  # noqa: BLE001
                self.state = STATE_INVALID
                self.detail = f"metadata.json unreadable: {error}"
                return
            self._finish_validation()
            return

        # Layout 2: Keras (model.h5 or savedmodel dir) + labels.txt
        has_keras = ("model.h5" in files) or ("model.savedmodel" in dirs)
        if has_keras and "labels.txt" in files:
            self._layout = "keras"
            try:
                raw = files["labels.txt"].read_text(encoding="utf-8").splitlines()
                # Teachable Machine labels.txt lines look like "0 Gunshot"
                self.labels = [ln.split(" ", 1)[-1].strip() for ln in raw if ln.strip()]
            except Exception as error:  # noqa: BLE001
                self.state = STATE_INVALID
                self.detail = f"labels.txt unreadable: {error}"
                return
            self._finish_validation()
            return

        self.state = STATE_INVALID
        self.detail = ("Export present but unrecognised. Expected TensorFlow.js "
                       "(model.json + metadata.json) or Keras (model.h5 + labels.txt).")

    def _finish_validation(self) -> None:
        """Check labels cover the expected classes, then try to load a runtime."""
        norm = {self._norm(x) for x in self.labels}
        expected = {self._norm(x) for x in self.expected_classes}
        missing = expected - norm
        if missing:
            self.state = STATE_INVALID
            self.detail = (f"GTM export labels do not match the 10 required classes. "
                           f"Missing: {sorted(missing)}")
            return
        # Files + labels are valid.
        self.state = STATE_READY
        self.detail = f"Valid GTM export ({self._layout}) with {len(self.labels)} labels."
        self._try_load_runtime()

    def _try_load_runtime(self) -> None:
        """Attempt to load an actual inference runtime; do NOT fake if absent."""
        if self._layout == "keras":
            try:
                import tensorflow as tf  # noqa: F401
                from tensorflow import keras

                h5 = self.export_dir / "model.h5"
                sm = self.export_dir / "model.savedmodel"
                self._model = keras.models.load_model(str(h5 if h5.exists() else sm))
                self.runtime_available = True
                self.detail += " Keras runtime loaded."
            except Exception as error:  # noqa: BLE001
                self.runtime_available = False
                self.detail += (f" Files valid but Keras/TensorFlow runtime not usable "
                                f"({error}). Install tensorflow to enable GTM inference.")
        else:  # tfjs
            # tfjs models run in the browser. Server-side use needs a converter.
            self.runtime_available = False
            self.detail += (" TensorFlow.js export detected. For server-side inference, "
                            "convert to Keras/SavedModel, or run GTM in the browser client.")

    @staticmethod
    def _norm(name: str) -> str:
        return name.strip().lower().replace(" ", "_").replace("-", "_")

    # -- public API -------------------------------------------------------
    @property
    def configured(self) -> bool:
        return self.state == STATE_READY

    def status(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "detail": self.detail,
            "labels": self.labels,
            "runtime_available": self.runtime_available,
            "layout": self._layout,
            "export_dir": str(self.export_dir),
        }

    def predict(self, y, sr: int) -> dict[str, Any] | None:
        """Run the real GTM model on a preprocessed signal.

        Returns None when GTM cannot produce an HONEST prediction (not
        configured, invalid, or no server-side runtime). Callers must treat
        None as "GTM not available" and NEVER substitute the Python result.
        """
        if self.state != STATE_READY or not self.runtime_available or self._model is None:
            return None
        try:
            import numpy as np

            # GTM audio models expect their own front-end; this path is only
            # reached when a Keras runtime is loaded. We feed the mel/log-mel
            # front-end GTM uses (43x232-ish). Because the exact front-end is
            # model-specific, we defer to a converter module if present.
            from .gtm_frontend import prepare_input  # optional, user-supplied

            x = prepare_input(y, sr, self.labels)
            proba = self._model.predict(x, verbose=0)[0]
            scores = {self.labels[i]: round(float(proba[i]) * 100, 2)
                      for i in range(len(self.labels))}
            top = max(range(len(proba)), key=lambda i: proba[i])
            return {
                "predicted_class": self.labels[top],
                "confidence": round(float(proba[top]) * 100, 2),
                "scores": scores,
            }
        except Exception:  # noqa: BLE001
            # Never fabricate: if the real model cannot run, report unavailable.
            return None
