#!/usr/bin/env python3
"""Public wrapper for release validation."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("validate_anonymous_release.py")), run_name="__main__")
