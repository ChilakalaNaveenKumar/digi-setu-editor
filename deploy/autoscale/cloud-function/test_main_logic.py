"""
Pure-function tests for the tier picker. Run with:

    cd deploy/autoscale/cloud-function
    pip install -r requirements.txt
    pip install pytest
    GCP_PROJECT_ID=x GCP_ZONE=x GCP_INSTANCE=x BACKEND_URL=x \\
      pytest test_main_logic.py -v

The picker is the only piece that's worth unit-testing — everything
else (Secret Manager fetch, compute API calls) is GCP-side and the
deploy-time DRY_RUN dry-run is the real integration test for those.
"""

from __future__ import annotations

import os
import sys


def _import_main():
    """Import main.py after pinning the required env vars so the
    module-level `os.environ[...]` reads don't KeyError."""
    os.environ.setdefault("GCP_PROJECT_ID", "test-project")
    os.environ.setdefault("GCP_ZONE", "us-central1-a")
    os.environ.setdefault("GCP_INSTANCE", "test-instance")
    os.environ.setdefault("BACKEND_URL", "https://example.com")
    sys.path.insert(0, os.path.dirname(__file__))
    import main  # noqa: WPS433 — late import is the whole point

    return main


def test_hold_when_low_load():
    m = _import_main()
    target, _reason = m._pick_tier(sessions=1, mem_util=0.30, current_idx=0)
    assert target == 0


def test_scale_up_when_mem_high():
    m = _import_main()
    target, reason = m._pick_tier(sessions=1, mem_util=0.85, current_idx=0)
    assert target == 1
    assert "0.85" in reason or "85" in reason


def test_scale_up_when_session_count_exceeds_mem():
    m = _import_main()
    # tier 0 = e2-small with 2 GiB. 3 sessions > 2 GiB → scale up.
    target, _ = m._pick_tier(sessions=3, mem_util=0.40, current_idx=0)
    assert target == 1


def test_scale_down_when_comfortable_at_smaller():
    m = _import_main()
    # On tier 2 (8 GiB) but only using ~1 GiB. tier 1 (4 GiB) is
    # plenty (1 GiB << 4 * 0.7 * 0.7 ≈ 1.96 GiB). Should scale down.
    target, _ = m._pick_tier(
        sessions=1, mem_util=1.0 / 8.0, current_idx=2,
    )
    assert target == 1


def test_no_scale_down_at_min_tier():
    m = _import_main()
    target, _ = m._pick_tier(sessions=0, mem_util=0.01, current_idx=0)
    assert target == 0


def test_no_scale_up_past_max_tier():
    m = _import_main()
    # Force MAX_TIER=4 (the default). At tier 4 with full pressure we
    # MUST hold — the autoscaler can't conjure a bigger box.
    target, _ = m._pick_tier(sessions=40, mem_util=0.99, current_idx=4)
    assert target == 4


def test_hysteresis_keeps_us_at_borderline():
    """Sitting at a tier where we're at ~60% mem util and sessions ==
    tier capacity — the scale-down branch should NOT fire because the
    smaller tier is too tight. The scale-up branch should also NOT
    fire because mem_util < 70%. Net: hold."""
    m = _import_main()
    target, _ = m._pick_tier(sessions=4, mem_util=0.50, current_idx=2)  # 8 GiB
    assert target == 2
