"""Extract acoustic features for every organised clip (SRS Step 6 / requirement xx).

Reads data/dataset_metadata.csv, preprocesses each clip, extracts a fixed
feature vector, and saves everything to a single .npz for fast training.

Run:
    python src/extract_features.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sonic.config import load_config
from sonic.features import extract_features, feature_names
from sonic.preprocessing import AudioSettings, load_audio


def main() -> None:
    cfg = load_config()
    settings = AudioSettings.from_config(cfg)
    meta_path = cfg.path("metadata_csv")
    if not meta_path.exists():
        print("Metadata not found. Run: python src/organize.py", file=sys.stderr)
        sys.exit(1)

    meta = pd.read_csv(meta_path)
    out_root = cfg.output_root
    total = len(meta)
    print(f"Extracting features for {total} clips (sr={settings.sample_rate}, "
          f"dur={settings.duration}s)...")

    vectors: list[np.ndarray] = []
    labels: list[str] = []
    audio_ids: list[str] = []
    splits: list[str] = []
    sources: list[str] = []
    failures = 0
    start = time.time()

    for i, row in meta.iterrows():
        clip_path = out_root / row["relative_path"]
        try:
            y = load_audio(clip_path, settings)
            vec = extract_features(y, settings.sample_rate, cfg)
        except Exception as error:  # noqa: BLE001 - log and skip bad clips
            failures += 1
            print(f"  skip {row['audio_id']} ({clip_path.name}): {error}", file=sys.stderr)
            continue
        vectors.append(vec)
        labels.append(row["class_label"])
        audio_ids.append(row["audio_id"])
        splits.append(row["split"])
        sources.append(row["source"])

        done = i + 1
        if done % 200 == 0 or done == total:
            elapsed = time.time() - start
            print(f"  {done}/{total} processed ({elapsed:.0f}s)")

    if not vectors:
        print("No features extracted.", file=sys.stderr)
        sys.exit(1)

    X = np.vstack(vectors).astype(np.float32)
    features_path = cfg.path("features_file")
    features_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        features_path,
        X=X,
        y=np.array(labels),
        audio_id=np.array(audio_ids),
        split=np.array(splits),
        source=np.array(sources),
        feature_names=np.array(feature_names(cfg)),
    )

    print(f"\nSaved {X.shape[0]} feature vectors of dim {X.shape[1]} -> {features_path}")
    print(f"Failed/skipped clips: {failures}")


if __name__ == "__main__":
    main()
