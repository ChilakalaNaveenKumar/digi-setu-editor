"""Shared pytest config — adds the backend root to sys.path so `import services.billing`
just works when pytest is invoked from web/backend/.

This is the small price for not committing to a `src/` layout. If we ever
adopt `pyproject.toml` with `[tool.setuptools.packages.find]` we can drop
this file.
"""

import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

# Point any module that resolves a SQLite path at import time at a
# scratch directory. Without this the test process would touch the
# operator's real ``billing.db`` / ``gemini_cache.db`` etc. Resolved
# BEFORE any service module is imported (pytest evaluates conftest
# before collecting test files), so module-level globals like
# ``services.gemini_cache_db._DB_PATH`` pick up the tmp path.
_TMP_DATA_ROOT = tempfile.mkdtemp(prefix="pi-test-data-")
os.environ.setdefault("PI_DATA_ROOT", _TMP_DATA_ROOT)
os.environ.setdefault(
    "GEMINI_CACHE_DB_PATH", os.path.join(_TMP_DATA_ROOT, "gemini_cache.db"),
)
os.environ.setdefault(
    "DESKTOP_TELEMETRY_DB_PATH",
    os.path.join(_TMP_DATA_ROOT, "desktop_telemetry.db"),
)
