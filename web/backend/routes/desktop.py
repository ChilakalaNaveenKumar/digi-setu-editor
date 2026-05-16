"""
Desktop install + heartbeat + release-channel endpoints.

These power three flows that didn't have a backend until now:

  1. **Authenticated download tracking** — Download.vue calls
     ``POST /api/desktop/track-download`` BEFORE pointing the
     browser at the static .dmg/.exe URL. We record who clicked
     which artefact at which time so the operator can answer
     "how many of our users actually got the new build out?"
     without scraping Caddy logs.

  2. **Per-install heartbeats** — every desktop sidecar boot
     POSTs ``/api/desktop/heartbeat`` with its persistent
     ``install_id`` UUID + currently-running version. Upserts the
     ``desktop_clients`` row keyed on (user_id, install_id), so a
     user with three machines shows up as three rows. Returns the
     server-side latest version + minimum-supported floor so the
     desktop's auto-updater can decide whether to nag.

  3. **Latest-version pointer** — ``GET /api/desktop/latest-version``
     is the public read-side companion to ``set_release_channel``,
     used by Download.vue to render the "v{X} · early access"
     banner and by any in-app banner that wants to surface
     "you're outdated" without going through the full updater
     manifest.

All three live in one router file because they share their data
backend (``services/desktop_telemetry``) and the same JWT
auth — splitting them across files would just add import noise.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from services import desktop_telemetry
from services.auth import require_user

router = APIRouter(tags=["desktop"])


def _client_ip(request: Request) -> Optional[str]:
    """Best-effort client IP extraction. Caddy forwards X-Forwarded-For;
    the first value is the original public IP (Caddy itself appends
    its loopback address as the trust hop). Falls back to the raw
    socket peer when the header is missing (local dev curl)."""
    fwd = request.headers.get("x-forwarded-for", "").strip()
    if fwd:
        return fwd.split(",", 1)[0].strip()
    return request.client.host if request.client else None


class TrackDownloadBody(BaseModel):
    # Same enum the SPA's Download.vue computes from the user-agent.
    # Validated as a string to keep the surface forgiving — a stale
    # SPA shipping a new platform value shouldn't 422 the user
    # before the cloud has been redeployed.
    platform: str = Field(min_length=1, max_length=64)
    # Best-effort version of the artefact the user is downloading.
    # The SPA reads this from its hard-coded APP_VERSION constant.
    version: str = Field(min_length=1, max_length=32)


class TrackDownloadResponse(BaseModel):
    ok: bool
    download_id: int
    download_url: str


@router.post("/api/desktop/track-download", response_model=TrackDownloadResponse)
async def track_download(
    body: TrackDownloadBody,
    request: Request,
    user_id: str = Depends(require_user),
) -> TrackDownloadResponse:
    """Record an authenticated user's download intent and hand back
    the static URL the SPA should point the browser at.

    Why we return the URL rather than 302'ing: a 302 from a fetch()
    call is followed by the browser, which would issue a second GET
    that the SPA can no longer attach an Authorization header to —
    Caddy serves /downloads/* anonymously anyway, but the SPA still
    wants to receive the URL string so it can trigger the download
    via a synthetic ``<a download>`` click. This also keeps the
    surface debuggable (the URL is human-readable in the response).

    We use the SPA-side platform key in the DB rather than
    server-derived parsing of the User-Agent — the SPA already
    decided which artefact the user clicked, and the UA can lie
    in ways that don't reflect the user's actual click.
    """
    download_id = desktop_telemetry.record_download(
        user_id=user_id,
        version=body.version,
        platform=body.platform,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    # The /downloads/{filename} pattern is hard-coded in Caddy. We
    # don't reconstruct the full filename here — the SPA already
    # knows it (computed from version + platform). Returning a
    # platform-relative path lets the SPA stay the source of truth
    # for "what's the right artefact for this OS" and keeps this
    # endpoint pure-tracking.
    return TrackDownloadResponse(
        ok=True,
        download_id=download_id,
        download_url=f"/downloads/{_filename_for(body.platform, body.version)}",
    )


def _filename_for(platform: str, version: str) -> str:
    """Mirror of the filename pattern in web/frontend/src/views/Download.vue.
    Kept in sync by hand because the SPA bundles the constants and
    re-implementing the platform map here would just be a second
    place to drift. If a future redesign ever moves filename
    derivation to a shared spec, this function goes away."""
    table = {
        "mac-arm":         f"Digi-Setu-{version}-arm64.dmg",
        "mac-intel":       f"Digi-Setu-{version}-x86_64.dmg",
        "linux-deb":       f"Digi-Setu-{version}-amd64.deb",
        "linux-appimage":  f"Digi-Setu-{version}-amd64.AppImage",
        "windows":         f"Digi-Setu-{version}-x64-setup.exe",
        "windows-msi":     f"Digi-Setu-{version}-x64.msi",
    }
    return table.get(platform, f"Digi-Setu-{version}-{platform}.bin")


class HeartbeatBody(BaseModel):
    # Stable per-install UUID the desktop sidecar generates on
    # first launch and stores at ``$DIGI_SETU_HOME/install_id``.
    # Limited to 64 chars to soak up uuid4 + suffix room without
    # opening the door to abuse.
    install_id: str = Field(min_length=1, max_length=64)
    # CARGO_PKG_VERSION of the running desktop binary.
    version: str = Field(min_length=1, max_length=32)
    # Kernel-style platform: ``darwin-arm64``, ``darwin-x86_64``,
    # ``linux-x86_64``, ``win32-x86_64`` …
    platform: str = Field(min_length=1, max_length=64)


class HeartbeatResponse(BaseModel):
    ok: bool
    first_seen: bool
    latest_version: str
    update_available: bool
    min_supported: Optional[str] = None
    release_notes: Optional[str] = None


@router.post("/api/desktop/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    body: HeartbeatBody,
    request: Request,
    user_id: str = Depends(require_user),
) -> HeartbeatResponse:
    """One round-trip per desktop boot: client tells us its version,
    we record it and tell the client whether there's a newer
    release. Cheap (single SQLite upsert + read) and the only
    desktop→cloud write that runs unconditionally on every launch.
    """
    result = desktop_telemetry.record_heartbeat(
        user_id=user_id,
        install_id=body.install_id,
        version=body.version,
        platform=body.platform,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    channel = desktop_telemetry.get_release_channel("current") or {}
    latest = channel.get("version") or body.version
    update_available = _semver_lt(body.version, latest)

    return HeartbeatResponse(
        ok=True,
        first_seen=bool(result.get("first_seen")),
        latest_version=latest,
        update_available=update_available,
        min_supported=channel.get("min_supported"),
        release_notes=channel.get("release_notes"),
    )


def _semver_lt(a: str, b: str) -> bool:
    """``a < b`` for plain X.Y.Z strings. Forgiving on input —
    invalid / empty versions count as "older" so a malformed
    client.version still gets surfaced an "update available"
    rather than silently passing as up-to-date.
    """
    try:
        ta = tuple(int(p) for p in a.split("-")[0].split("."))
        tb = tuple(int(p) for p in b.split("-")[0].split("."))
    except ValueError:
        return True
    # Pad to equal length so 0.1 < 0.1.1 evaluates as expected.
    n = max(len(ta), len(tb))
    ta_p = ta + (0,) * (n - len(ta))
    tb_p = tb + (0,) * (n - len(tb))
    return ta_p < tb_p


class ClientRow(BaseModel):
    install_id: str
    first_seen_ts: str
    last_seen_ts: str
    version: str
    platform: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None


class ClientsResponse(BaseModel):
    clients: list[ClientRow]
    latest_version: str


@router.get("/api/desktop/clients", response_model=ClientsResponse)
async def list_clients(user_id: str = Depends(require_user)) -> ClientsResponse:
    """Every desktop install this user has ever phoned home from,
    most-recent first. Powers the (planned) Devices section in the
    web account page — show "MacBook Pro · v0.1.0 · last seen 2h
    ago · update available".
    """
    rows = desktop_telemetry.list_clients(user_id)
    channel = desktop_telemetry.get_release_channel("current") or {}
    return ClientsResponse(
        clients=[ClientRow(**r) for r in rows],
        latest_version=channel.get("version") or "",
    )


class LatestVersionResponse(BaseModel):
    version: str
    published_at: str
    release_notes: Optional[str] = None
    min_supported: Optional[str] = None


@router.get("/api/desktop/latest-version", response_model=LatestVersionResponse)
async def latest_version() -> LatestVersionResponse:
    """Public read of the canonical release pointer. Used by:
      * Download.vue to render the "v{X}" hero badge.
      * The desktop's pre-launch update check (when offline /
        unauthenticated, the heartbeat path doesn't fire — this
        endpoint still works as a fallback).

    Anonymous on purpose — the version string isn't sensitive and
    making it public lets the marketing site embed the badge
    without an auth bounce."""
    channel = desktop_telemetry.get_release_channel("current")
    if channel is None:
        # Telemetry seeds 'current' on first DB access; a missing row
        # should be impossible. Defensive empty-shape so a damaged
        # DB doesn't take the marketing page down — the SPA falls
        # back to its hard-coded APP_VERSION constant.
        return LatestVersionResponse(version="", published_at="")
    return LatestVersionResponse(
        version=channel["version"],
        published_at=channel["published_at"],
        release_notes=channel.get("release_notes"),
        min_supported=channel.get("min_supported"),
    )
