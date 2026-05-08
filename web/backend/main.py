"""
Backend entry point.

Local dev:
    uvicorn main:app --host 127.0.0.1 --port 8000 --reload

Cloud Run / container:
    The Dockerfile sets PORT (Cloud Run injects this) and runs
    `python -m main`, which delegates to uvicorn with the right port +
    no reload + a single worker. Cloud Run requires :$PORT and sane
    SIGTERM handling; uvicorn does both out of the box.
"""

from __future__ import annotations

import os

from app import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
        workers=1,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
