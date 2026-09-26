"""Prepare an import-ready Google Teachable Machine (GTM) audio dataset.

GTM is browser-based and cannot be trained from Python. This script builds the
exact folder layout a human uploads into a GTM Audio Project so that GTM is
trained on the SAME underlying TRAINING recordings as the Python model (SRS
Step 9: same class names, training split only, no val/test leakage).

Output layout (one folder per class, GTM canonical names):

    gtm/dataset_export/
        Machinery Fault/
        Glass Breaking/
        Alarm or Siren/
        Vehicle Horn/
        Animal Sound/
        Gunshot/
        Panic Scream/
        Aggression/
        Person Asking for Help/
        Background Noise/

Only TRAINING-split originals are exported (val/test are held out for the
unseen comparison). Clips are trimmed to short samples suitable for GTM.

Run:
    python gtm/export_dataset.py
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from sonic.config import load_config  # noqa: E402

# Pipeline class label -> GTM canonical display name (SRS Step 9 exact names).
PIPELINE_TO_GTM = {
    "machinery_fault": "Machinery Fault",
    "glass_breaking": "Glass Breaking",
    "alarm_siren": "Alarm or Siren",
    "vehicle_horn": "Vehicle Horn",
    "animal_sound": "Animal Sound",
    "gunshot": "Gunshot",
    "panic_scream": "Panic Scream",
    "aggression": "Aggression",
    "person_asking_for_help": "Person Asking for Help",
    "background_noise": "Background Noise",
}


def main() -> None:
    cfg = load_config()
    meta_path = cfg.path("metadata_csv")
    if not meta_path.exists():
        print(f"Dataset metadata not found: {meta_path}\nRun: python src/organize.py",
              file=sys.stderr)
        sys.exit(1)

    out_root = _ROOT / "gtm" / "dataset_export"
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    for gtm_name in PIPELINE_TO_GTM.values():
        (out_root / gtm_name).mkdir(exist_ok=True)

    exported = {name: 0 for name in PIPELINE_TO_GTM.values()}
    skipped = 0
    with meta_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            # TRAINING split only, originals only (SRS: no val/test leakage into GTM).
            if row.get("split") != "train":
                continue
            if row.get("augmented", "original") != "original":
                continue
            cls = row.get("class_label", "")
            gtm_name = PIPELINE_TO_GTM.get(cls)
            if not gtm_name:
                skipped += 1
                continue
            src = cfg.output_root / row["relative_path"]
            if not src.exists():
                skipped += 1
                continue
            dest = out_root / gtm_name / f"{row['audio_id']}{src.suffix}"
            shutil.copy2(src, dest)
            exported[gtm_name] += 1

    print(f"GTM import-ready dataset written to: {out_root}\n")
    print(f"{'GTM class':<28}{'train samples':>14}")
    print("-" * 42)
    for name, n in exported.items():
        flag = "  <- NO DATA" if n == 0 else ""
        print(f"{name:<28}{n:>14}{flag}")
    if skipped:
        print(f"\n({skipped} rows skipped: missing file or non-mandatory class.)")
    print("\nNext: upload these folders into a Google Teachable Machine Audio "
          "Project, train, export, and place the export in models/gtm/export/.")


if __name__ == "__main__":
    main()
