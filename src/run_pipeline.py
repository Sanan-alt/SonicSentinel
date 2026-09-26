"""One-shot pipeline: detect new data -> clean/organize -> features -> train.

Run this whenever the Dataset changes. It:
  1. Scans the raw Dataset folders and compares them against the last build.
  2. If anything changed (new/removed audio), re-organizes + re-extracts
     features (clean rebuild), otherwise reuses existing features.
  3. Trains both models and writes SRS reports.

Usage:
    python src/run_pipeline.py            # rebuild only if data changed
    python src/run_pipeline.py --force    # always rebuild everything
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sonic.config import load_config

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
PYTHON = sys.executable


def dataset_fingerprint(cfg) -> dict:
    """A lightweight signature of the raw dataset: per-source file count + names hash."""
    sig = {}
    sources = []

    esc = cfg.path("esc50_audio")
    if esc.exists():
        sources.append(("esc50", esc, "*.wav"))
    mp3 = cfg["paths"].get("mp3_folders", {})
    for key in mp3:
        p = cfg.path("mp3_folders", key)
        if p.exists():
            sources.append((key, p, "*"))

    for name, folder, pattern in sources:
        # Recurse so per-class subfolders (e.g. user_uploads/<class>/) count too.
        globber = folder.rglob if pattern == "*" else folder.glob
        files = [f for f in globber(pattern) if f.is_file() and f.suffix.lower() in AUDIO_EXTS]
        names = sorted(str(f.relative_to(folder)) for f in files)
        digest = hashlib.md5("|".join(names).encode()).hexdigest()
        sig[name] = {"count": len(files), "names_hash": digest}
    return sig


def load_previous(cfg) -> dict | None:
    fp = cfg.output_root / "dataset_fingerprint.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_fingerprint(cfg, sig) -> None:
    cfg.output_root.mkdir(parents=True, exist_ok=True)
    (cfg.output_root / "dataset_fingerprint.json").write_text(
        json.dumps(sig, indent=2), encoding="utf-8")


def run_step(script: str) -> None:
    here = Path(__file__).resolve().parent
    print(f"\n>>> Running {script} ...\n")
    result = subprocess.run([PYTHON, str(here / script)])
    if result.returncode != 0:
        print(f"[ERROR] {script} failed (exit {result.returncode}).", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    force = "--force" in sys.argv
    cfg = load_config()

    current = dataset_fingerprint(cfg)
    previous = load_previous(cfg)
    features_exist = cfg.path("features_file").exists()

    print("=" * 60)
    print(" SonicSentinel pipeline")
    print("=" * 60)
    for name, info in current.items():
        prev_count = (previous or {}).get(name, {}).get("count", "-")
        flag = ""
        if previous is not None:
            if name not in previous:
                flag = "  <- NEW source"
            elif previous[name]["names_hash"] != info["names_hash"]:
                flag = "  <- CHANGED"
        print(f"  {name:<14} {info['count']} files (was {prev_count}){flag}")

    changed = force or previous is None or previous != current or not features_exist
    models_exist = (cfg.path("models_dir") / "sonicsentinel_model.joblib").exists()

    if not changed:
        print("\nNo dataset changes detected; reusing existing features.")
    else:
        print("\nDataset changed (or --force): rebuilding dataset + features.")
        run_step("organize.py")
        run_step("extract_features.py")
        save_fingerprint(cfg, current)

    # Only (re)train when the data changed or no trained model exists yet.
    # This keeps app startup cheap: an unchanged dataset with existing models
    # skips the (slow) training step entirely.
    if changed or not models_exist:
        run_step("train.py")
    else:
        print("Models already trained and dataset unchanged; skipping training.")
    print("\n" + "=" * 60)
    print(" Pipeline complete. Launch the app with start_sonicsentinel.bat")
    print("=" * 60)


if __name__ == "__main__":
    main()
