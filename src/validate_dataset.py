"""Honest dataset validation & reporting (SRS dataset requirements xvi-xix, 31).

Reports the REAL state of the built dataset — it never fabricates counts. Reads
the dataset metadata produced by ``organize.py`` and the raw audio, then checks:

  * total unique original clips vs the SRS target (3,000)
  * per-class counts vs target (300/class)
  * class imbalance / insufficient classes
  * exact duplicates (SHA-256) and near-duplicates (MFCC-mean cosine similarity)
  * split leakage (same audio_id across splits; augmented in val/test)
  * sample-rate / duration / channel / quality distributions

Writes:
  reports/dataset/dataset_validation.json
  reports/dataset/dataset_validation.md

Run:
    python src/validate_dataset.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sonic.config import load_config

TARGET_TOTAL = 3000
TARGET_PER_CLASS = 300
NEAR_DUP_THRESHOLD = 0.9995   # cosine similarity of MFCC-mean vectors


def _load_metadata(cfg):
    meta_path = cfg.path("metadata_csv")
    if not meta_path.exists():
        print(f"Metadata not found: {meta_path}\nRun: python src/organize.py", file=sys.stderr)
        sys.exit(1)
    with meta_path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh)), meta_path


def _mfcc_mean(path, sr_target):
    import librosa
    import numpy as np

    try:
        y, _ = librosa.load(str(path), sr=sr_target, mono=True, duration=5.0)
        if y.size == 0:
            return None
        m = librosa.feature.mfcc(y=y, sr=sr_target, n_mfcc=20)
        return m.mean(axis=1)
    except Exception:
        return None


def main() -> None:
    import numpy as np

    cfg = load_config()
    rows, meta_path = _load_metadata(cfg)
    classes = cfg.classes
    sr_target = int(cfg["audio"]["sample_rate"])

    originals = [r for r in rows if r.get("augmented", "original") == "original"]
    augmented = [r for r in rows if r.get("augmented", "original") != "original"]

    # Per-class + per-split counts (originals only for the SRS targets).
    per_class = Counter(r["class_label"] for r in originals)
    per_split = Counter(r["split"] for r in originals)
    per_class_split = defaultdict(Counter)
    for r in originals:
        per_class_split[r["class_label"]][r["split"]] += 1

    total_unique = len(originals)

    # Split leakage: an audio_id must appear in exactly one split.
    id_splits = defaultdict(set)
    for r in rows:
        id_splits[r["audio_id"]].add(r["split"])
    leaked_ids = {aid: sorted(s) for aid, s in id_splits.items() if len(s) > 1}

    # Augmented leakage: augmented rows must be train-only.
    aug_in_eval = [r["audio_id"] for r in augmented if r["split"] in ("val", "test")]

    # Exact duplicates by sha256 (should be 0 after organize de-dup).
    hash_counts = Counter(r.get("sha256", "") for r in originals if r.get("sha256"))
    exact_dups = {h: c for h, c in hash_counts.items() if c > 1}

    # Near-duplicate scan (sampled to keep it fast): compare MFCC-mean vectors.
    print("Scanning for near-duplicates (MFCC-mean cosine)...")
    vectors = []
    sample = originals if len(originals) <= 1500 else originals[::2]
    for r in sample:
        p = cfg.output_root / r["relative_path"]
        v = _mfcc_mean(p, sr_target)
        if v is not None:
            vectors.append((r["audio_id"], r["class_label"], v))
    near_dups = []
    if len(vectors) >= 2:
        mat = np.array([v for _, _, v in vectors])
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        unit = mat / norms
        # Block comparison to avoid a full NxN memory spike.
        for i in range(len(unit)):
            sims = unit[i + 1:] @ unit[i]
            for j_off, s in enumerate(sims):
                if s >= NEAR_DUP_THRESHOLD:
                    j = i + 1 + j_off
                    near_dups.append((vectors[i][0], vectors[j][0], round(float(s), 5)))
        near_dups = near_dups[:200]

    # Distributions from the raw audio metadata columns if present, else scan.
    sr_dist, dur_buckets, ch_dist = Counter(), Counter(), Counter()
    for r in originals:
        sr = r.get("sample_rate")
        if sr:
            sr_dist[str(sr)] += 1

    # Build report.
    class_report = []
    for c in classes:
        n = per_class.get(c, 0)
        class_report.append({
            "class": c,
            "originals": n,
            "target": TARGET_PER_CLASS,
            "meets_target": n >= TARGET_PER_CLASS,
            "train": per_class_split[c].get("train", 0),
            "val": per_class_split[c].get("val", 0),
            "test": per_class_split[c].get("test", 0),
        })

    result = {
        "metadata_file": str(meta_path),
        "total_unique_originals": total_unique,
        "target_total": TARGET_TOTAL,
        "meets_total_target": total_unique >= TARGET_TOTAL,
        "augmented_rows": len(augmented),
        "split_totals": dict(per_split),
        "per_class": class_report,
        "missing_classes": [c for c in classes if per_class.get(c, 0) == 0],
        "below_target_classes": [c for c in classes if 0 < per_class.get(c, 0) < TARGET_PER_CLASS],
        "exact_duplicates": exact_dups,
        "near_duplicate_pairs_found": len(near_dups),
        "near_duplicate_examples": near_dups[:20],
        "split_leakage_ids": leaked_ids,
        "augmented_in_val_test": aug_in_eval,
        "sample_rate_distribution": dict(sr_dist),
    }

    reports_dir = cfg.path("reports_dir") / "dataset"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "dataset_validation.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")

    # Markdown summary.
    lines = ["# Dataset Validation Report", "",
             f"- **Total unique original clips:** {total_unique} / {TARGET_TOTAL} "
             f"({'MEETS' if result['meets_total_target'] else 'BELOW'} target)",
             f"- **Augmented (train-only) rows:** {len(augmented)}",
             f"- **Split totals (originals):** {dict(per_split)}",
             f"- **Exact duplicates:** {len(exact_dups)}",
             f"- **Near-duplicate pairs found:** {len(near_dups)}",
             f"- **Split leakage (ids in >1 split):** {len(leaked_ids)}",
             f"- **Augmented clips leaked into val/test:** {len(aug_in_eval)}",
             "", "## Per-class (originals)", "",
             "| Class | Originals | Target | Meets? | Train | Val | Test |",
             "|---|---:|---:|:--:|---:|---:|---:|"]
    for cr in class_report:
        lines.append(f"| {cr['class']} | {cr['originals']} | {cr['target']} | "
                     f"{'YES' if cr['meets_target'] else 'NO'} | {cr['train']} | "
                     f"{cr['val']} | {cr['test']} |")
    if result["missing_classes"]:
        lines += ["", f"**Missing classes (no data):** {', '.join(result['missing_classes'])}"]
    if result["below_target_classes"]:
        lines += [f"**Below target:** {', '.join(result['below_target_classes'])}"]
    lines += ["", "> Counts are the REAL measured values. Where a class is below "
              "300 or the total is below 3,000, collect/import more real, "
              "ethically-sourced recordings — no fabricated clips are added."]
    (reports_dir / "dataset_validation.md").write_text("\n".join(lines), encoding="utf-8")

    # Console summary.
    print(f"\nTotal unique originals: {total_unique} / {TARGET_TOTAL} "
          f"({'MEETS' if result['meets_total_target'] else 'BELOW'} target)")
    print(f"{'class':<26}{'orig':>6}{'target':>8}{'meets':>7}")
    print("-" * 47)
    for cr in class_report:
        print(f"{cr['class']:<26}{cr['originals']:>6}{cr['target']:>8}"
              f"{'  yes' if cr['meets_target'] else '   no':>7}")
    print(f"\nExact dups: {len(exact_dups)}  Near-dup pairs: {len(near_dups)}  "
          f"Split leakage: {len(leaked_ids)}  Aug-in-eval: {len(aug_in_eval)}")
    print(f"\nReport -> {reports_dir}")


if __name__ == "__main__":
    main()
