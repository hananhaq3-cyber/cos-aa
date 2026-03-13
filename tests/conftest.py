"""
Root conftest — makes fixtures available to all test directories.

Note: fixtures defined in tests/fixtures/conftest.py are auto-discovered
by pytest (no pytest_plugins directive needed — that causes double-registration).
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
