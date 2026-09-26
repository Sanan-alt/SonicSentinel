"""Mirror generated evidence into the repo and write model metadata + samples.

Copies the real generated reports from ``output_root/reports`` into the repo's
``reports/`` tree (for submission), writes ``models/python/model_metadata.json``
from the trained bundle, and produces ``reports/evaluation/sample_predictions.csv``
by running the model on the sample_audio clips.

Run (after training):
    python src/generate_reports.py
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
_ROOT = Path(__file__).resolve().parents[1]

from sonic.config import load_config          # noqa: E402
from sonic.features import extract_features    # noqa: E402
from sonic.preprocessing import AudioSettings, load_audio  # noqa: E402


def _copy(src: Path, dst: Path):
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    return False


def main() -> None:
    import joblib

    cfg = load_config()
    live_reports = cfg.path("reports_dir")
    repo_reports = _ROOT / "reports"

    # 1. Mirror the key generated report files into the repo tree.
    mirrored = []
    for src_rel, dst_rel in [
        ("metrics.json", "evaluation/metrics.json"),
        ("confusion_matrix.csv", "evaluation/confusion_matrix.csv"),
        ("confusion_matrix.png", "evaluation/confusion_matrix.png"),
        ("model_comparison_report.csv", "comparison/model_comparison_report.csv"),
        ("dataset/dataset_validation.json", "dataset/dataset_validation.json"),
        ("dataset/dataset_validation.md", "dataset/dataset_validation.md"),
    ]:
        if _copy(live_reports / src_rel, repo_reports / dst_rel):
            mirrored.append(dst_rel)

    # 2. model metadata from the trained bundle.
    py_path = cfg.path("models_dir") / "sonicsentinel_model.joblib"
    if py_path.exists():
        bundle = joblib.load(py_path)
        metrics_path = live_reports / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
        meta = {
            "model_name": bundle.get("model_name"),
            "model_version": bundle.get("version"),
            "classes": bundle.get("classes"),
            "n_features": len(bundle.get("feature_names", [])),
            "feature_config": cfg["features"],
            "audio_config": cfg["audio"],
            "test_accuracy": metrics.get("python", {}).get("test_accuracy"),
            "test_macro_f1": metrics.get("python", {}).get("test_macro_f1"),
            "critical_class_recall": metrics.get("python", {}).get("critical_class_recall"),
            "models_compared": [m.get("model") for m in metrics.get("model_comparison", [])],
        }
        out = _ROOT / "models" / "python" / "model_metadata.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        mirrored.append("models/python/model_metadata.json")

        # 3. sample predictions on sample_audio.
        settings = AudioSettings.from_config(cfg)
        classes = list(bundle["classes"])
        rows = []
        for clip in sorted((_ROOT / "sample_audio").glob("*")):
            if clip.suffix.lower() not in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}:
                continue
            try:
                y = load_audio(clip, settings)
                feats = extract_features(y, settings.sample_rate, cfg)
                vec = bundle["scaler"].transform(feats.reshape(1, -1))
                model = bundle["model"]
                proba = (model.predict_proba(vec)[0] if hasattr(model, "predict_proba")
                         else None)
                if proba is not None:
                    idx = int(np.argmax(proba))
                    rows.append({"file": clip.name, "predicted": classes[idx],
                                 "confidence_pct": round(float(proba[idx]) * 100, 2)})
            except Exception as e:  # noqa: BLE001
                rows.append({"file": clip.name, "predicted": f"error: {e}", "confidence_pct": ""})
        sp = repo_reports / "evaluation" / "sample_predictions.csv"
        sp.parent.mkdir(parents=True, exist_ok=True)
        with sp.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["file", "predicted", "confidence_pct"])
            w.writeheader(); w.writerows(rows)
        mirrored.append("reports/evaluation/sample_predictions.csv")

    print("Mirrored / generated:")
    for m in mirrored:
        print(f"  {m}")
    if not mirrored:
        print("  (nothing found — run src/train.py and src/validate_dataset.py first)")


if __name__ == "__main__":
    main()
