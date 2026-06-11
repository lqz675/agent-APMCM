"""pytest conftest: put scripts/ on sys.path so unit tests can import directly."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
