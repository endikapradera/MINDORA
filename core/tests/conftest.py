"""Pytest configuration and shared fixtures for MINDORA tests."""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Ensure the core package is importable from this test directory
CORE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE_DIR))

# Set required env defaults so modules can import without crashing
os.environ.setdefault("IA_OFFLINE_LLM_PATH", "/dev/null")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
