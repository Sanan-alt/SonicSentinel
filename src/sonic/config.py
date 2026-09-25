"""Central configuration loader for SonicSentinel AI.

Loads ``config/config.yaml`` and resolves every path against the project
root so scripts can be run from anywhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Project root = two levels up from this file (src/sonic/config.py -> root).
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "config.yaml"


class Config:
    """Thin wrapper around the parsed YAML config with path helpers."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    # Generated-output keys are resolved under paths.output_root (may be on a
    # different drive). All other path keys resolve under the project ROOT.
    _OUTPUT_KEYS = {"categorized", "metadata_csv", "features_file", "models_dir", "reports_dir"}

    # -- path helpers -----------------------------------------------------
    def path(self, *keys: str) -> Path:
        """Resolve a nested ``paths`` entry to an absolute Path.

        Example: ``cfg.path("categorized")`` or ``cfg.path("mp3_folders", "aggression")``.

        Generated-output keys are placed under ``paths.output_root``; input
        keys are placed under the project root.
        """
        node: Any = self._data["paths"]
        for key in keys:
            node = node[key]

        if keys and keys[0] in self._OUTPUT_KEYS:
            out_root = Path(self._data["paths"]["output_root"])
            if not out_root.is_absolute():
                out_root = ROOT / out_root
            return (out_root / node).resolve()
        return (ROOT / node).resolve()

    @property
    def output_root(self) -> Path:
        out_root = Path(self._data["paths"]["output_root"])
        if not out_root.is_absolute():
            out_root = ROOT / out_root
        return out_root.resolve()

    @property
    def classes(self) -> list[str]:
        return list(self._data["classes"])

    @property
    def critical_classes(self) -> list[str]:
        return list(self._data["critical_classes"])


def load_config(path: Path | str = CONFIG_PATH) -> Config:
    with open(path, "r", encoding="utf-8") as stream:
        return Config(yaml.safe_load(stream))
