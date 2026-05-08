#!/bin/bash
# Per-session container entrypoint.
#
# Runs as PID 1 (under tini) inside each pi-session container. Three jobs:
#
#   1. Set umask 002 so files written by the AI to /workspace inherit
#      group-write — the host parent dir (mode 2770, gid 1000) has
#      SGID set, and the backend (uid 1100, secondary group 1000)
#      needs write access for GCS sync / registry updates.
#
#   2. If the backend bind-mounted a Vertex credentials JSON at
#      /etc/pi/vertex.json (or a path passed via
#      GOOGLE_APPLICATION_CREDENTIALS), make sure the sandbox user
#      can read it. The bind mount lands as root:root mode 0644 by
#      default — that's already world-readable, so this is just a
#      sanity check, but if the operator sets stricter perms on the
#      host side (mode 0640 root:1000) we chown/chmod as needed here.
#      DEFERRED to Phase 5 — for now the file may not exist yet.
#
#   3. Drop from root → uid 1000 (sandbox) and exec the supplied
#      command. setpriv handles the uid/gid/group switch with the
#      same flags pattern used by the backend's old in-process
#      sandbox drop (see web/backend/services/pi_session.py git
#      history for the rationale). We do NOT pass --no-new-privs
#      because sudo's setuid bit needs to work for the
#      "user installs whatever" workflow that's the whole point of
#      this image.
#
# Failure modes:
#
#   * No CMD passed → exec "" exits with a clear error. We refuse to
#     default to `bash` because that would let an operator typo
#     ("docker run pi-session" with no args) silently start an
#     interactive shell with no agent attached.
#
#   * setpriv missing → the image's util-linux package is broken;
#     bail loudly so the operator notices on first deploy rather
#     than getting a confusing "permission denied".
#
#   * /workspace not bind-mounted → the AI starts with cwd=/workspace
#     pointing at an EMPTY ephemeral overlay layer (no user files).
#     We log a warning but don't refuse; some smoke tests run
#     without a workspace.

set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "entrypoint-session: no CMD supplied — refusing to default to bash" >&2
    echo "(this image is meant to be invoked by the backend with explicit pi --mode rpc args)" >&2
    exit 64
fi

if ! command -v setpriv >/dev/null 2>&1; then
    echo "entrypoint-session: setpriv not found in container — broken image" >&2
    exit 70
fi

# umask 002 = 0664 for new files / 0775 for new dirs. SGID inheritance
# on /workspace's host parent (mode 2770) does the gid part; we just
# need to make sure the group bits are writable.
umask 002

# Sanity check on /workspace. If the bind mount is missing, log it but
# continue — `pi --mode rpc` can still start, it just won't have any
# user data to operate on. This is exercised by `docker run pi-session
# pi --version` smoke tests where no volume is mounted.
if [ ! -d /workspace ]; then
    echo "entrypoint-session: WARN /workspace does not exist — agent will run in an empty cwd" >&2
fi

# ── MITM CA cert install ────────────────────────────────────────────
#
# The backend's egress proxy (web/backend/services/egress_proxy.py)
# generates a CA cert at /srv/pi/state/mitm-ca.crt on first boot and
# bind-mounts it READ-ONLY into every per-session container at
# /etc/pi/mitm-ca.crt. The proxy uses this CA to sign leaf certs on
# the fly for *.aiplatform.googleapis.com so it can MITM the TLS
# connection from pi-ai → Vertex and inject the Authorization header
# from the backend's own ADC token. Without trust of this CA, every
# pi-ai HTTPS call to Vertex would fail with a cert verification error.
#
# We install the CA into THREE places to cover every TLS client a user
# might invoke inside the container:
#
#   1. /usr/local/share/ca-certificates/pi-mitm.crt + update-ca-certificates
#      → openssl/curl/wget/python-requests/most C-based clients
#
#   2. NODE_EXTRA_CA_CERTS env → Node.js fetch / undici / pi-ai (the
#      one client we ABSOLUTELY need to trust the proxy)
#
#   3. SSL_CERT_FILE / CURL_CA_BUNDLE / REQUESTS_CA_BUNDLE → catches
#      Python's ssl module (used by pip), curl when invoked
#      explicitly, and python-requests in the user's installed
#      packages.
#
# If the bind mount is missing (laptop dev with no proxy) we skip
# silently — pi-ai will then try to talk to Vertex directly using the
# operator's ADC, same as the legacy subprocess runtime.
MITM_CA="/etc/pi/mitm-ca.crt"
if [ -f "${MITM_CA}" ]; then
    install -d -m 0755 /usr/local/share/ca-certificates
    install -m 0644 "${MITM_CA}" /usr/local/share/ca-certificates/pi-mitm.crt
    # update-ca-certificates rebuilds /etc/ssl/certs/ca-certificates.crt
    # and the c_rehash symlinks. Output goes to stderr so it doesn't
    # mix with the RPC stdout. ~500ms on first boot, faster on
    # subsequent runs (most certs are unchanged).
    update-ca-certificates 2>&1 | tail -3 >&2 || true

    export NODE_EXTRA_CA_CERTS="${MITM_CA}"
    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
    export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
    export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
else
    echo "entrypoint-session: WARN /etc/pi/mitm-ca.crt missing — Vertex auth will fall back to the container's own ADC (which doesn't exist), expect HTTPS errors" >&2
fi

# Ensure /workspace is at least readable by the sandbox uid before we
# drop privileges. Bind mounts inherit host ownership, so this should
# already be 1000:1000 from the host's pi-prepare.service stamp; we
# just double-check and log if something is off.
if [ -d /workspace ]; then
    ws_uid="$(stat -c '%u' /workspace 2>/dev/null || echo unknown)"
    ws_gid="$(stat -c '%g' /workspace 2>/dev/null || echo unknown)"
    if [ "$ws_uid" != "1000" ] && [ "$ws_gid" != "1000" ]; then
        echo "entrypoint-session: WARN /workspace ownership ${ws_uid}:${ws_gid} (expected 1000:1000)" >&2
    fi
fi

# Drop to the sandbox user. --clear-groups drops any inherited
# supplementary groups (none should be present, but defense in depth).
# We deliberately do NOT pass --no-new-privs because sudo's setuid
# bit is the documented escalation path for "user installs apt
# packages" — see Dockerfile.session header rationale.
exec setpriv \
    --reuid 1000 \
    --regid 1000 \
    --clear-groups \
    --inh-caps=-all \
    -- "$@"
