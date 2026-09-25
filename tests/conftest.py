"""Shared pytest fixtures and path setup for SonicSentinel tests."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "webapp"))


@pytest.fixture(scope="session")
def cfg():
    from sonic.config import load_config
    return load_config()


@pytest.fixture
def tone():
    """A 5-second 440 Hz sine wave at 22050 Hz (a clean, non-silent signal)."""
    sr = 22050
    t = np.linspace(0, 5.0, int(sr * 5.0), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
