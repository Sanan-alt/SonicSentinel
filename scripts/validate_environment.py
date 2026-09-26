"""Check the runtime environment: Python version, packages, ffmpeg, folders.

Run:
    python scripts/validate_environment.py
"""

from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = ["librosa", "soundfile", "numpy", "sklearn", "xgboost",
            "flask", "matplotlib", "yaml", "joblib"]


def main() -> None:
    ok = True

    if sys.version_info < (3, 10):
        print(f"[FAIL] Python {sys.version.split()[0]} < 3.10")
        ok = False
    else:
        print(f"[OK]   Python {sys.version.split()[0]}")

    for mod in REQUIRED:
        try:
            importlib.import_module(mod)
            print(f"[OK]   import {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] import {mod}: {e}")
            ok = False

    ff = shutil.which("ffmpeg")
    print(f"[{'OK' if ff else 'WARN'}] ffmpeg: {ff or 'not on PATH (mp3/m4a decode may need it)'}")

    for rel in ["config/config.yaml", "alert_rules/alert_rules.json",
                "src/train.py", "webapp/app.py"]:
        p = ROOT / rel
        print(f"[{'OK' if p.exists() else 'FAIL'}] {rel}")
        ok = ok and p.exists()

    print("\nEnvironment OK" if ok else "\nEnvironment has problems")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
