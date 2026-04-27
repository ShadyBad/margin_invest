"""Shared fixtures for audit tests."""
from __future__ import annotations

import random

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def deterministic_random() -> None:
    """Pin the RNG seed for every audit test. Determinism is a correctness invariant."""
    random.seed(42)
    np.random.seed(42)
