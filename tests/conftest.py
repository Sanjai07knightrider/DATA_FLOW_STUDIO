# pytest conftest.py — shared fixtures and path setup for all test modules
import sys
from pathlib import Path

# Ensure project root and src/ are on the import path for all tests
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
