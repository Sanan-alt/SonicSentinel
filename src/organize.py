"""Organise raw audio into SRS classes and build the dataset metadata (SRS Step 1/5).

What it does:
  * Reads ESC-50 clips, maps their target -> SRS class (only mapped categories).
  * Reads the hand-collected mp3 folders (Aggression, Glass breaking).
  * De-duplicates by SHA-256 so the accidental gunshot=Aggression copy is dropped.
  * Copies unique clips into data/categorized_audio/<class>/.
  * Assigns a stable Audio ID and a stratified train/val/test split.
  * Writes data/dataset_metadata.csv with the SRS metadata fields.

Run:
    python src/organize.py
"""

from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# Allow running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sonic.config import load_config
from sonic.labels import ESC50_TO_SRS, MP3_FOLDER_TO_SRS, esc50_target_map

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def esc50_class_for(filename: str, target_map: dict[int, str]) -> str | None:
    """ESC-50 filename -> SRS class, or None if not a mapped category."""
    stem = Path(filename).stem
    try:
        target = int(stem.split("-")[-1])
    except ValueError:
        return None
    esc_category = target_map.get(target)
    if esc_category is None:
        return None
    return ESC50_TO_SRS.get(esc_category)


def collect_sources(cfg):
    """Yield (source_path, srs_class, source_name) for every candidate clip."""
    target_map = esc50_target_map(cfg.path("esc50_meta"))

    # ESC-50 (original 44.1kHz only; the 16000/44100 sub-folders are content
    # duplicates and are excluded via the folder path itself).
    esc_root = cfg.path("esc50_audio")
    for path in sorted(esc_root.glob("*.wav")):
        srs_class = esc50_class_for(path.name, target_map)
        if srs_class is not None:
            yield path, srs_class, "esc50"

    # Hand-collected class folders (one class per folder).
    for folder_key, srs_class in MP3_FOLDER_TO_SRS.items():
        folder = cfg.path("mp3_folders", folder_key)
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTS:
                yield path, srs_class, f"mp3:{folder_key}"

    # User-contributed clips: Dataset/user_uploads/<class>/*.  Each subfolder
    # name must be a valid SRS class; other names are ignored. Picked up
    # automatically by the background trainer (see webapp/services/trainer.py).
    user_root = None
    if "user_uploads" in cfg["paths"].get("mp3_folders", {}):
        user_root = cfg.path("mp3_folders", "user_uploads")
    if user_root and user_root.exists():
        valid_classes = set(cfg.classes)
        for class_dir in sorted(p for p in user_root.iterdir() if p.is_dir()):
            srs_class = class_dir.name
            if srs_class not in valid_classes:
                continue
            for path in sorted(class_dir.iterdir()):
                if path.is_file() and path.suffix.lower() in AUDIO_EXTS:
                    yield path, srs_class, f"user:{srs_class}"


def stratified_split(items_by_class, ratios, seed):
    """Assign each item a split, stratified per class. Returns {index: split}."""
    import random

    rng = random.Random(seed)
    split_of: dict[int, str] = {}
    for _, indices in items_by_class.items():
        idx = list(indices)
        rng.shuffle(idx)
        n = len(idx)
        n_train = int(round(n * ratios["train"]))
        n_val = int(round(n * ratios["val"]))
        for i, global_index in enumerate(idx):
            if i < n_train:
                split_of[global_index] = "train"
            elif i < n_train + n_val:
                split_of[global_index] = "val"
            else:
                split_of[global_index] = "test"
    return split_of


def main() -> None:
    cfg = load_config()
    out_root = cfg.path("categorized")
    # Clear any previous build so re-runs never mix stale copies into the
    # dataset (otherwise removed/relabelled clips would linger).
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # 1. Collect + de-duplicate.
    records = []          # list of dicts
    seen_hashes: set[str] = set()
    duplicates = 0
    for source, srs_class, source_name in collect_sources(cfg):
        try:
            file_hash = sha256(source)
        except OSError as error:
            print(f"skip (read error) {source}: {error}", file=sys.stderr)
            continue
        if file_hash in seen_hashes:
            duplicates += 1
            continue
        seen_hashes.add(file_hash)
        records.append(
            {
                "source_path": source,
                "srs_class": srs_class,
                "source": source_name,
                "hash": file_hash,
                "orig_filename": source.name,
                "suffix": source.suffix.lower(),
            }
        )

    if not records:
        print("No audio found. Check config paths.", file=sys.stderr)
        sys.exit(1)

    # 2. Stratified split.
    items_by_class = defaultdict(list)
    for i, rec in enumerate(records):
        items_by_class[rec["srs_class"]].append(i)
    split_of = stratified_split(items_by_class, cfg["split"], int(cfg["split"]["seed"]))

    # 3. Copy into class folders + build metadata rows.
    for cls in sorted({r["srs_class"] for r in records}):
        (out_root / cls).mkdir(parents=True, exist_ok=True)

    meta_rows = []
    for i, rec in enumerate(records):
        audio_id = f"SS{i:05d}"
        split = split_of[i]
        dest_name = f"{audio_id}_{rec['hash'][:8]}{rec['suffix']}"
        dest = out_root / rec["srs_class"] / dest_name
        shutil.copy2(rec["source_path"], dest)
        meta_rows.append(
            {
                "audio_id": audio_id,
                "filename": dest.name,
                "class_label": rec["srs_class"],
                "source": rec["source"],
                "original_filename": rec["orig_filename"],
                "sha256": rec["hash"],
                "split": split,
                "augmented": "original",
                "relative_path": str(dest.relative_to(cfg.output_root)),
            }
        )

    # 4. Write metadata CSV.
    meta_path = cfg.path("metadata_csv")
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "audio_id", "filename", "class_label", "source",
        "original_filename", "sha256", "split", "augmented", "relative_path",
    ]
    with meta_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(meta_rows)

    # 5. Report.
    per_class = defaultdict(lambda: defaultdict(int))
    for row in meta_rows:
        per_class[row["class_label"]][row["split"]] += 1

    print(f"Organised {len(meta_rows)} unique clips into {out_root}")
    print(f"Duplicates removed (incl. the gunshot=Aggression copy): {duplicates}")
    print(f"Metadata written to {meta_path}\n")
    print(f"{'class':<26}{'train':>7}{'val':>6}{'test':>6}{'total':>7}")
    print("-" * 52)
    for cls in cfg.classes:
        c = per_class.get(cls, {})
        total = sum(c.values())
        flag = "  <- NO DATA (add later)" if total == 0 else ""
        print(f"{cls:<26}{c.get('train',0):>7}{c.get('val',0):>6}{c.get('test',0):>6}{total:>7}{flag}")
    # Any class present in data but not in the mandatory list (shouldn't happen).
    extra = set(per_class) - set(cfg.classes)
    for cls in sorted(extra):
        c = per_class[cls]
        print(f"{cls:<26}{c.get('train',0):>7}{c.get('val',0):>6}{c.get('test',0):>6}{sum(c.values()):>7}  (extra)")


if __name__ == "__main__":
    main()
