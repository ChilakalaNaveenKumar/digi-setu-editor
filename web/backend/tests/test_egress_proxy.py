"""
Unit tests for services/egress_proxy.py.

Covered:
  - Hostname allow-list (exact + suffix match)
  - MITM suffix detection (Vertex hosts)
  - CA generation: idempotent on second call when key+cert are present
  - Leaf cert generation: cached after first request, signed by CA

NOT covered (manual smoke via deploy/scripts/smoke-session.sh):
  - Actual TCP socket binding
  - TLS handshake against real Vertex endpoints
  - End-to-end MITM with a live container

Run with:
    pytest web/backend/tests/test_egress_proxy.py -v
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_state_dir(monkeypatch):
    """Override the CA paths to a tempdir so we don't touch /srv/pi/state."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        monkeypatch.setenv("PI_MITM_CA_PATH", str(td_path / "mitm-ca.crt"))
        monkeypatch.setenv("PI_MITM_CA_KEY_PATH", str(td_path / "mitm-ca.key"))
        monkeypatch.setenv("PI_EGRESS_LEAF_CACHE_DIR", str(td_path / "leaf-certs"))
        # Force-reload the module so the new env vars take effect.
        import importlib
        import services.egress_proxy as _ep
        importlib.reload(_ep)
        yield td_path


def test_allowlist_exact_match(temp_state_dir):
    from services.egress_proxy import _is_allowed
    assert _is_allowed("crates.io")
    assert _is_allowed("static.rust-lang.org")
    assert _is_allowed("typst.app")


def test_allowlist_suffix_match(temp_state_dir):
    from services.egress_proxy import _is_allowed
    # *.googleapis.com → us-central1-aiplatform.googleapis.com matches
    assert _is_allowed("us-central1-aiplatform.googleapis.com")
    assert _is_allowed("storage.googleapis.com")
    assert _is_allowed("api.github.com")
    assert _is_allowed("raw.githubusercontent.com")
    assert _is_allowed("registry.npmjs.org")
    assert _is_allowed("files.pythonhosted.org")
    assert _is_allowed("archive.ubuntu.com")
    assert _is_allowed("huggingface.co")


def test_allowlist_does_not_substring_match(temp_state_dir):
    """`evilgithub.com` must NOT match `.github.com`."""
    from services.egress_proxy import _is_allowed
    assert not _is_allowed("evilgithub.com")
    assert not _is_allowed("typst.app.attacker.com")
    assert not _is_allowed("ngithub.com")
    assert not _is_allowed("attacker.com")
    assert not _is_allowed("169.254.169.254")  # raw IP literal
    assert not _is_allowed("metadata.google.internal")


def test_allowlist_case_insensitive(temp_state_dir):
    from services.egress_proxy import _is_allowed
    assert _is_allowed("API.GITHUB.COM")
    assert _is_allowed("Crates.IO")


def test_mitm_suffix_only_for_vertex(temp_state_dir):
    from services.egress_proxy import _should_mitm
    assert _should_mitm("us-central1-aiplatform.googleapis.com")
    assert _should_mitm("us-east4-aiplatform.googleapis.com")
    # GCS / Iconify / npm are allow-listed but NOT MITM'd
    assert not _should_mitm("storage.googleapis.com")
    assert not _should_mitm("api.github.com")
    assert not _should_mitm("registry.npmjs.org")
    assert not _should_mitm("typst.app")


def test_ca_generated_on_first_call(temp_state_dir):
    from services.egress_proxy import _CA_CERT_PATH, _CA_KEY_PATH, _load_or_create_ca
    assert not _CA_CERT_PATH.exists()
    cert, key = _load_or_create_ca()
    assert _CA_CERT_PATH.exists()
    assert _CA_KEY_PATH.exists()
    # Mode 0600 on the private key.
    assert oct(_CA_KEY_PATH.stat().st_mode & 0o777) == "0o600"


def test_ca_reused_on_second_call(temp_state_dir):
    from services.egress_proxy import _load_or_create_ca
    cert1, key1 = _load_or_create_ca()
    cert2, key2 = _load_or_create_ca()
    # Same serial number — proves we loaded from disk, didn't regenerate.
    assert cert1.serial_number == cert2.serial_number


def test_leaf_cert_signed_by_ca(temp_state_dir):
    from services.egress_proxy import _get_leaf_cert, _load_or_create_ca

    ca_cert, ca_key = _load_or_create_ca()
    cert_path, key_path = _get_leaf_cert(
        "us-central1-aiplatform.googleapis.com", ca_cert, ca_key
    )
    assert cert_path.exists()
    assert key_path.exists()

    # Re-read and verify issuer matches CA subject.
    from cryptography import x509
    leaf = x509.load_pem_x509_certificate(cert_path.read_bytes())
    assert leaf.issuer == ca_cert.subject

    # SAN includes the requested hostname.
    san = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    dns_names = san.value.get_values_for_type(x509.DNSName)
    assert "us-central1-aiplatform.googleapis.com" in dns_names


def test_leaf_cert_cached_in_memory(temp_state_dir):
    from services.egress_proxy import _LEAF_CACHE, _get_leaf_cert, _load_or_create_ca

    _LEAF_CACHE.clear()
    ca_cert, ca_key = _load_or_create_ca()
    p1 = _get_leaf_cert("us-central1-aiplatform.googleapis.com", ca_cert, ca_key)
    p2 = _get_leaf_cert("us-central1-aiplatform.googleapis.com", ca_cert, ca_key)
    # Same paths returned — proves it came from cache, not regenerated.
    assert p1 == p2
    assert "us-central1-aiplatform.googleapis.com" in _LEAF_CACHE
