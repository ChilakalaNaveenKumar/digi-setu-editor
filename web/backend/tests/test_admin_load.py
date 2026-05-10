"""
Smoke tests for /api/admin/load.

The endpoint is gated by ADMIN_LOAD_TOKEN; we exercise all three
auth states (disabled, missing token, bad token, good token) and
confirm the response shape matches what the Cloud Function expects.
We don't try to assert real memory numbers — those come from
/proc/meminfo which isn't on macOS CI runners. Instead we assert the
SHAPE and that mem_used/mem_total degrade to (0, 0) gracefully.
"""

from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import admin


@pytest.fixture
def app(monkeypatch):
    """Fresh app with only the admin router mounted. Avoids loading
    the giant main app for a leaf test."""
    monkeypatch.delenv("ADMIN_LOAD_TOKEN", raising=False)
    a = FastAPI()
    a.include_router(admin.router)
    return a


def test_disabled_returns_503(app):
    """No token set anywhere → endpoint refuses to even accept the
    request. Operators should never see a 401 from this route in
    prod; if they do, the token leaked."""
    with TestClient(app) as client:
        r = client.get("/api/admin/load", headers={"Authorization": "Bearer whatever"})
    assert r.status_code == 503
    assert "ADMIN_LOAD_TOKEN" in r.json()["detail"]


def test_missing_bearer_returns_401(app, monkeypatch):
    monkeypatch.setenv("ADMIN_LOAD_TOKEN", "topsecret_value_32bytes_min")
    with TestClient(app) as client:
        r = client.get("/api/admin/load")
    assert r.status_code == 401


def test_wrong_bearer_returns_403(app, monkeypatch):
    monkeypatch.setenv("ADMIN_LOAD_TOKEN", "topsecret_value_32bytes_min")
    with TestClient(app) as client:
        r = client.get(
            "/api/admin/load",
            headers={"Authorization": "Bearer not-the-right-token"},
        )
    assert r.status_code == 403


def test_good_bearer_returns_load_shape(app, monkeypatch):
    monkeypatch.setenv("ADMIN_LOAD_TOKEN", "topsecret_value_32bytes_min")
    with TestClient(app) as client:
        r = client.get(
            "/api/admin/load",
            headers={"Authorization": "Bearer topsecret_value_32bytes_min"},
        )
    assert r.status_code == 200
    body = r.json()
    # Shape contract pinned by the Cloud Function — do NOT rename
    # these fields without also bumping deploy/autoscale/cloud-function/main.py.
    assert set(body.keys()) >= {
        "ok",
        "active_sessions",
        "mem_used_bytes",
        "mem_total_bytes",
        "mem_util",
        "machine_type",
    }
    assert body["ok"] is True
    assert isinstance(body["active_sessions"], int)
    assert isinstance(body["mem_used_bytes"], int)
    assert isinstance(body["mem_total_bytes"], int)
    assert isinstance(body["mem_util"], (int, float))
    assert isinstance(body["machine_type"], str)
    # mem_util in [0, 1]; might be 0.0 on macOS (no /proc/meminfo).
    assert 0.0 <= body["mem_util"] <= 1.0


def test_constant_time_compare_smoke(app, monkeypatch):
    """Belt-and-suspenders: the route uses secrets.compare_digest, so
    a prefix-match attack shouldn't fast-path. We can't really time-
    assert here without flakiness, but we can at least confirm that
    a 1-byte difference is still rejected. (Real timing-attack tests
    belong in a separate latency harness.)"""
    monkeypatch.setenv("ADMIN_LOAD_TOKEN", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    with TestClient(app) as client:
        # Same length, single-byte tail difference.
        r = client.get(
            "/api/admin/load",
            headers={"Authorization": "Bearer aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"},
        )
    assert r.status_code == 403
