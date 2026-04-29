"""Pytest config: ensure the project root is on sys.path so `memory_tool` imports cleanly."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
