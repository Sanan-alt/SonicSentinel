"""Classify an audio clip with the trained Python model (SRS Step 8 / xxv-xxvi).

Loads the saved model bundle, preprocesses the clip, extracts features, and
prints the predicted class plus a confidence score for every trained class.

Run:
    python src/predict.py path/to/clip.wav
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sonic.config import load_config
from sonic.features import extract_features
from sonic.preprocessing import AudioSettings, load_audio


def predict(clip_path: Path):
    import joblib

    cfg = load_config()
    bundle_path = cfg.path("models_dir") / "sonicsentinel_model.joblib"
    if not bundle_path.exists():
        print("Model not found. Run: python src/train.py", file=sys.stderr)
        sys.exit(1)

    bundle = joblib.load(bundle_path)
    settings = AudioSettings.from_config(cfg)

    y = load_audio(clip_path, settings)
    vec = extract_features(y, settings.sample_rate, cfg).reshape(1, -1)
    vec = bundle["scaler"].transform(vec)

    model = bundle["model"]
    classes = bundle["classes"]
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(vec)[0]
    else:  # fall back to a one-hot style score
        pred_idx = int(model.predict(vec)[0])
        proba = np.zeros(len(classes))
        proba[pred_idx] = 1.0

    order = np.argsort(proba)[::-1]
    return classes, proba, order, bundle["model_name"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify an audio clip.")
    parser.add_argument("clip", type=str, help="path to an audio file")
    parser.add_argument("--top", type=int, default=3, help="show top-N predictions")
    args = parser.parse_args()

    clip_path = Path(args.clip).resolve()
    if not clip_path.exists():
        print(f"File not found: {clip_path}", file=sys.stderr)
        sys.exit(1)

    classes, proba, order, model_name = predict(clip_path)

    print(f"\nModel: {model_name}")
    print(f"Clip : {clip_path.name}")
    print(f"Predicted: {classes[order[0]]}  ({proba[order[0]] * 100:.1f}%)\n")
    print(f"Top {args.top} predictions:")
    for idx in order[: args.top]:
        print(f"  {classes[idx]:<26}{proba[idx] * 100:6.2f}%")
    print("\nAll class confidences:")
    for i, cls in enumerate(classes):
        print(f"  {cls:<26}{proba[i] * 100:6.2f}%")


if __name__ == "__main__":
    main()
