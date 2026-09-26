"""Continuous background training service.

While the web app runs, this keeps the models up to date with ALL data in the
Dataset folders AND any user-contributed clips, WITHOUT blocking the web server:

  * On startup it runs one training cycle (only rebuilds if the dataset changed,
    reusing the pipeline's fingerprint check - so a normal restart is cheap).
  * A daemon thread then re-checks periodically; if new audio has appeared
    (e.g. a reviewer labelled a clip, or files were dropped into any Dataset
    folder) it retrains and hot-reloads the live InferenceService.

Training itself is delegated to ``src/run_pipeline.py`` so there is a single
source of truth for the organise -> features -> train steps. The pipeline's
own dataset-fingerprint means "no change -> no rebuild", so this loop is safe
to run forever.

User-contributed training data:
  Call ``add_labelled_clip(src_path, pipeline_class)`` to copy an uploaded clip
  into ``Dataset/user_uploads/<class>/``. That folder is registered as a normal
  dataset source (see config.yaml paths.mp3_folders.user_uploads), so it is
  automatically picked up on the next cycle.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from sonic.config import load_config  # noqa: E402
from sonic.labels import MP3_FOLDER_TO_SRS  # noqa: E402

_PYTHON = sys.executable
_PIPELINE = _ROOT / "src" / "run_pipeline.py"

# Dataset class -> the folder key used for user-contributed clips.
_CLASS_TO_FOLDER = {v: k for k, v in MP3_FOLDER_TO_SRS.items()}


class BackgroundTrainer:
    """Runs the training pipeline off the request path and hot-reloads models."""

    def __init__(self, cfg=None, reload_callback=None, interval_sec: int = 900):
        self.cfg = cfg or load_config()
        self.reload_callback = reload_callback      # called after a successful retrain
        self.interval_sec = interval_sec            # how often to re-check for new data
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self.status = {
            "state": "idle", "last_run": None, "last_result": None,
            "rebuilt": False, "message": "not started",
        }

    # -- public control ---------------------------------------------------
    def start(self) -> None:
        """Launch the background loop once (idempotent)."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="sonic-trainer", daemon=True)
        self._thread.start()

    def trigger_now(self) -> None:
        """Ask the loop to run a training cycle as soon as possible."""
        t = threading.Thread(target=self._run_cycle, args=(False,), daemon=True)
        t.start()

    # -- user-data intake -------------------------------------------------
    def add_labelled_clip(self, src_path: str | Path, pipeline_class: str) -> Path | None:
        """Copy a user clip into the training set under its labelled class.

        The clip lands in ``Dataset/user_uploads/<class>/`` (a registered
        source) and is trained on during the next cycle. Returns the new path.
        """
        src = Path(src_path)
        if not src.exists():
            return None
        base = _ROOT / "Dataset" / "user_uploads" / pipeline_class
        base.mkdir(parents=True, exist_ok=True)
        dest = base / src.name
        try:
            shutil.copy2(src, dest)
        except OSError:
            return None
        return dest

    # -- internals --------------------------------------------------------
    def _loop(self) -> None:
        # First cycle on startup (cheap if nothing changed).
        self._run_cycle(startup=True)
        while True:
            time.sleep(self.interval_sec)
            self._run_cycle(startup=False)

    def _run_cycle(self, startup: bool) -> None:
        # Only one training run at a time.
        if not self._lock.acquire(blocking=False):
            return
        self._running = True
        self.status.update(state="running",
                           message="startup cycle" if startup else "scheduled cycle")
        try:
            result = subprocess.run(
                [_PYTHON, str(_PIPELINE)],           # no --force: rebuild only if changed
                cwd=str(_ROOT), capture_output=True, text=True,
            )
            out = (result.stdout or "") + (result.stderr or "")
            rebuilt = "rebuilding dataset" in out.lower()
            ok = result.returncode == 0
            self.status.update(
                state="idle",
                last_run=time.strftime("%Y-%m-%d %H:%M:%S"),
                last_result="ok" if ok else f"exit {result.returncode}",
                rebuilt=rebuilt,
                message=out.strip().splitlines()[-1] if out.strip() else "done",
            )
            # Hot-reload the live model only if we actually retrained.
            if ok and rebuilt and self.reload_callback:
                try:
                    self.reload_callback()
                except Exception as error:  # noqa: BLE001
                    self.status["message"] = f"reload failed: {error}"
        except Exception as error:  # noqa: BLE001
            self.status.update(state="error", last_result=str(error),
                               message=f"cycle failed: {error}")
        finally:
            self._running = False
            self._lock.release()
