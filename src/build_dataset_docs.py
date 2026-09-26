"""Build committable dataset deliverables from the real metadata (SRS section 3).

Reads the dataset metadata produced by ``organize.py`` (under output_root) plus
the categorized audio, and writes lightweight, submittable evidence into the
repo's ``data/`` folder:

  data/metadata/metadata.csv            copy of the SRS metadata
  data/metadata/dataset_dictionary.md   field definitions
  data/metadata/class_distribution.csv  per-class / per-split counts
  data/metadata/dataset_statistics.json totals, durations, sample rates, quality
  data/splits/train.csv | validation.csv | test.csv

All numbers are REAL (measured from the built dataset). Nothing is fabricated.

Run (after `python src/organize.py`):
    python src/build_dataset_docs.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sonic.config import load_config

ROOT = Path(__file__).resolve().parents[1]

DICTIONARY = """# Dataset Data Dictionary (SRS section 3)

| Field | Description |
|---|---|
| audio_id | Stable unique ID for the recording (e.g. `SS00042`), kept across all derived artefacts. |
| filename | Stored filename inside the categorized dataset. |
| class_label | One of the 10 mandatory SRS classes. |
| source | Origin of the clip (`esc50`, `mp3:<folder>`, `user_uploads`, `synthetic`). |
| original_filename | Filename as delivered by the source. |
| sha256 | SHA-256 content hash (exact-duplicate detection). |
| split | `train`, `val`, or `test` (stratified 70/15/15). |
| augmented | `original` for real recordings; augmentation name for derived train clips. |
| relative_path | Path of the stored clip relative to `output_root`. |

## Notes
- Validation and test rows are **originals only** (no augmentation leakage).
- Environment / device / source-distance are not known for public-source clips
  and are recorded as `unknown`; they are populated for any self-recorded audio.
- Synthetic placeholder clips (currently `gunshot`, `panic_scream`) are tagged in
  `source`/`augmented` and are **not** counted as unique real recordings.
"""


def main() -> None:
    cfg = load_config()
    meta_path = cfg.path("metadata_csv")
    if not meta_path.exists():
        print(f"Metadata not found: {meta_path}\nRun: python src/organize.py", file=sys.stderr)
        sys.exit(1)

    with meta_path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fieldnames = rows[0].keys() if rows else []

    meta_dir = ROOT / "data" / "metadata"
    splits_dir = ROOT / "data" / "splits"
    meta_dir.mkdir(parents=True, exist_ok=True)
    splits_dir.mkdir(parents=True, exist_ok=True)

    # 1. metadata.csv (copy).
    with (meta_dir / "metadata.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fieldnames))
        w.writeheader()
        w.writerows(rows)

    # 2. dictionary.
    (meta_dir / "dataset_dictionary.md").write_text(DICTIONARY, encoding="utf-8")

    # 3. splits csvs.
    for split, fname in [("train", "train.csv"), ("val", "validation.csv"), ("test", "test.csv")]:
        subset = [r for r in rows if r.get("split") == split]
        with (splits_dir / fname).open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(fieldnames))
            w.writeheader()
            w.writerows(subset)

    # 4. class_distribution.csv (originals only for SRS targets).
    originals = [r for r in rows if r.get("augmented", "original") == "original"]
    per_cs = defaultdict(Counter)
    for r in originals:
        per_cs[r["class_label"]][r["split"]] += 1
    with (meta_dir / "class_distribution.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["class_label", "train", "val", "test", "total", "target", "meets_target"])
        for cls in cfg.classes:
            c = per_cs.get(cls, Counter())
            total = sum(c.values())
            w.writerow([cls, c.get("train", 0), c.get("val", 0), c.get("test", 0),
                        total, 300, "yes" if total >= 300 else "no"])

    # 5. dataset_statistics.json (measure durations/sample rates from real audio).
    import librosa

    durations, srs = [], Counter()
    scanned = 0
    for r in originals:
        p = cfg.output_root / r["relative_path"]
        if not p.exists():
            continue
        try:
            d = librosa.get_duration(path=str(p))
            durations.append(round(float(d), 3))
            info = librosa.get_samplerate(str(p))
            srs[str(info)] += 1
            scanned += 1
        except Exception:
            continue

    stats = {
        "total_rows": len(rows),
        "unique_originals": len(originals),
        "augmented_rows": len(rows) - len(originals),
        "target_total": 3000,
        "meets_total_target": len(originals) >= 3000,
        "per_class_total": {cls: sum(per_cs.get(cls, Counter()).values()) for cls in cfg.classes},
        "split_totals": dict(Counter(r["split"] for r in originals)),
        "audio_scanned_for_stats": scanned,
        "duration_seconds": {
            "min": min(durations) if durations else None,
            "max": max(durations) if durations else None,
            "mean": round(sum(durations) / len(durations), 3) if durations else None,
        },
        "sample_rate_distribution": dict(srs),
    }
    (meta_dir / "dataset_statistics.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print("Dataset docs written to data/metadata/ and data/splits/")
    print(f"  unique originals: {len(originals)} / 3000")
    print(f"  splits: {stats['split_totals']}")
    print(f"  audio scanned for duration/sr stats: {scanned}")


if __name__ == "__main__":
    main()
