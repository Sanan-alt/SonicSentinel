"""Extract acoustic features for every organised clip (SRS Step 6 / requirement xx).

Reads the dataset metadata, preprocesses each clip, extracts a fixed feature
vector, and saves everything to a single .npz for fast training.

Training-split clips are additionally augmented (SRS requirement xix): each
train clip yields ``augmentation.per_clip`` extra augmented feature vectors,
tagged augmented=True and kept in the SAME split as the parent. Validation and
test clips are never augmented.

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

from sonic.augmentation import augment
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

    aug_cfg = cfg.get("augmentation", {}) or {}
    aug_enabled = bool(aug_cfg.get("enabled", False))
    aug_per_clip = int(aug_cfg.get("per_clip", 0))
    aug_methods = list(aug_cfg.get("methods", []))
    rng = np.random.default_rng(int(cfg["split"]["seed"]))

    print(f"Extracting features for {total} clips (sr={settings.sample_rate}, "
          f"dur={settings.duration}s). Augmentation="
          f"{'on' if aug_enabled else 'off'} (x{aug_per_clip} on train).")

    vectors: list[np.ndarray] = []
    labels: list[str] = []
    audio_ids: list[str] = []
    splits: list[str] = []
    sources: list[str] = []
    augmented: list[bool] = []
    failures = 0
    aug_count = 0
    start = time.time()

    import gc

    def _features_with_retry(signal):
        """Extract features; on a transient MemoryError, gc and retry once."""
        try:
            return extract_features(signal, settings.sample_rate, cfg)
        except MemoryError:
            gc.collect()
            return extract_features(signal, settings.sample_rate, cfg)

    for i, row in meta.iterrows():
        clip_path = out_root / row["relative_path"]
        try:
            y = load_audio(clip_path, settings)
            vec = _features_with_retry(y)
        except Exception as error:  # noqa: BLE001 - log and skip bad clips
            failures += 1
            print(f"  skip {row['audio_id']} ({clip_path.name}): {error}", file=sys.stderr)
            gc.collect()
            continue

        # Original clip.
        vectors.append(vec)
        labels.append(row["class_label"])
        audio_ids.append(row["audio_id"])
        splits.append(row["split"])
        sources.append(row["source"])
        augmented.append(False)

        # Augmented copies (train split only).
        if aug_enabled and aug_per_clip > 0 and row["split"] == "train" and aug_methods:
            for _ in range(aug_per_clip):
                method = str(rng.choice(aug_methods))
                try:
                    y_aug = augment(y, settings.sample_rate, method, rng)
                    vec_aug = _features_with_retry(y_aug)
                    del y_aug
                except Exception:  # noqa: BLE001
                    continue
                vectors.append(vec_aug)
                labels.append(row["class_label"])
                audio_ids.append(row["audio_id"])   # same Audio ID as parent
                splits.append("train")
                sources.append(f"aug:{method}")
                augmented.append(True)
                aug_count += 1

        del y
        done = i + 1
        if done % 200 == 0 or done == total:
            gc.collect()
            elapsed = time.time() - start
            print(f"  {done}/{total} originals processed, {aug_count} augmented ({elapsed:.0f}s)")

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
        augmented=np.array(augmented),
        feature_names=np.array(feature_names(cfg)),
    )

    n_orig = int(np.sum(~np.array(augmented)))
    print(f"\nSaved {X.shape[0]} feature vectors of dim {X.shape[1]} -> {features_path}")
    print(f"  originals: {n_orig}   augmented: {aug_count}")
    print(f"Failed/skipped clips: {failures}")


if __name__ == "__main__":
    main()
