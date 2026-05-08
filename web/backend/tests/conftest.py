"""Shared pytest config — adds the backend root to sys.path so `import services.billing`
just works when pytest is invoked from web/backend/.

This is the small price for not committing to a `src/` layout. If we ever
adopt `pyproject.toml` with `[tool.setuptools.packages.find]` we can drop
this file.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
