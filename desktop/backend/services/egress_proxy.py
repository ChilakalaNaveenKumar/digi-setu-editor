"""
Egress proxy — single chokepoint for everything leaving a per-session container.

This module owns the trust boundary between the user's AI-driven shell
(running inside a `pi-session` Docker container) and the outside world.
It does three jobs:

    1. **HTTP CONNECT forward proxy** on a host:port reachable only from
       the `pi-egress` Docker network. Every container in that network
       has HTTPS_PROXY/HTTP_PROXY env baked in pointing here, AND the
       host nftables ruleset (deploy/nftables/pi-egress.nft) blocks
       ALL direct egress from the container subnet except to this
       proxy's listen address — so even if the AI tries to `unset
       HTTPS_PROXY` and curl-direct to an IP, the kernel drops the
       packet. The proxy is the ONLY way out.

    2. **Hostname allow-list enforcement.** CONNECT requests to a host
       NOT on the curated dev-friendly allow-list return HTTP 451 with
       a structured reason. The list covers ~30 hostnames spanning
       Vertex AI, npm/pypi/crates, Ubuntu/Debian apt mirrors, the
       Rust toolchain, GitHub, Hugging Face, Iconify, and common docs
       sites — enough that "user wants to install rust/go/python pkgs"
       Just Works without operator intervention. Anything not on the
       list (especially attacker-controlled exfil endpoints) gets a
       structured 451 the AI can explain to the user.

    3. **Vertex AI auth injection via TLS MITM.** For hostnames matching
       the Vertex / Anthropic-Vertex SNI pattern (`*.aiplatform.
       googleapis.com`), the proxy terminates TLS using a leaf cert
       signed on-the-fly by a backend-managed CA (whose root cert is
       bind-mounted read-only into every per-session container at
       /etc/pi/mitm-ca.crt and trusted via NODE_EXTRA_CA_CERTS), reads
       the inner HTTP request, drops any client-supplied
       Authorization / X-Goog-User-Project headers, injects a fresh
       Bearer token from the backend's own ADC + the configured GCP
       project, and forwards to the real upstream. The container
       itself never holds a Vertex token — the proxy is the sole
       holder, and it lives in the backend container which is
       already trusted with the ADC anyway.

The proxy runs in a daemon thread (ThreadingTCPServer) spawned by the
FastAPI lifespan. Threading instead of asyncio because Python's stdlib
ssl module is blocking-by-design and the bookkeeping for asyncio
TLS-MITM with `loop.start_tls()` is significantly hairier than the
~10-line synchronous `ssl.SSLContext.wrap_socket(server_side=True)`
recipe; for our load (≤ a few hundred concurrent CONNECT tunnels) the
per-tunnel thread cost is fine.

Threat model:

    * **AI exfiltrates Vertex token.** Impossible-by-construction: the
      token never enters the container. The AI's bash can `printenv
      | grep GOOGLE` all it wants — it gets project + location strings
      only. The proxy's listener is the sole auth-injection site.

    * **AI bypasses proxy with a raw socket.** Blocked at the kernel:
      nftables rejects every packet from the container subnet that
      isn't destined for the proxy's IP+port. The container has no
      route to the metadata server, the host's other interfaces, or
      the public internet directly.

    * **AI poisons the allow-list via DNS.** The proxy resolves
      hostnames itself for the upstream connection — DNS lookups
      happen INSIDE the backend container (uid 1100), which has its
      own DNS resolver pointed at the host's resolv.conf. The AI's
      bash can ship anything as the SNI / Host header, but if the
      hostname is allow-listed the proxy will resolve it freshly
      against the backend's resolver and connect. There's no AI-
      controlled DNS path between the container and upstream.

    * **AI tries to talk to the egress proxy directly to escalate.**
      The proxy only speaks HTTP CONNECT. Any non-CONNECT request
      gets 405. There's no /admin, no /healthz, no ID lookup — the
      proxy is a stateless single-purpose forwarder.

    * **Backend CA leak.** The CA private key lives at
      /srv/pi/state/proxy/mitm-ca.key, mode 0600, owned by the
      backend uid (1100). It's NEVER bind-mounted into per-session
      containers (only the public CA cert is). If a backend RCE
      leaked the CA
      key, an attacker could MITM Vertex API calls for any container
      with our CA installed (i.e. our own deployment). Mitigation:
      rotate the CA on every deploy that includes a backend code
      change. The proxy regenerates leaf certs from the current CA
      so a CA rotation just reissues each in-flight TLS session.

Operations:

    * The proxy is started by web/backend/main.py's lifespan — see
      `start_egress_proxy()` and `stop_egress_proxy()`.

    * Configuration via env (services/pi_session.py reads the same
      vars to wire the container side):
          PI_EGRESS_PROXY_HOST     (default 172.30.0.1)
          PI_EGRESS_PROXY_PORT     (default 1080)
          PI_MITM_CA_PATH          (default /srv/pi/state/proxy/mitm-ca.crt)
          PI_MITM_CA_KEY_PATH      (default /srv/pi/state/proxy/mitm-ca.key)
          PI_EGRESS_LEAF_CACHE_DIR (default /srv/pi/state/proxy/leaf-certs/)
          GOOGLE_CLOUD_PROJECT     (forwarded as X-Goog-User-Project)
          PI_EGRESS_DEBUG=1        verbose request logging to stderr

    * The CA is generated lazily on first start. `mitm-ca.crt` is
      world-readable (it's a public cert); `mitm-ca.key` is 0600
      backend-owner-only.

    * Per-host leaf certs are generated lazily on first MITM and
      cached on-disk under PI_EGRESS_LEAF_CACHE_DIR for reuse across
      backend restarts (so the cert serial / fingerprint stays
      stable, easier to spot-check).

    * Allow-list: see `_ALLOW` and `_ALLOW_SUFFIX` below. Add a
      hostname there if a legitimate dev tool routinely needs it;
      consider whether the host is trustworthy (do they ever serve
      malicious content?) before adding.
"""

from __future__ import annotations

import datetime as _dt
import logging
import os
import socket
import socketserver
import ssl
import sys
import threading
from pathlib import Path
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

logger = logging.getLogger(__name__)

# ── Configuration (env-driven) ───────────────────────────────────────
# Default paths live under /srv/pi/state/proxy/ — a sub-directory of
# /srv/pi/state that's owned by the backend uid (1100) and mode 0700.
# The parent /srv/pi/state stays root:root mode 0700 so its other
# secrets (JWT keys, auth.db) remain root-only. pi-prepare.service
# creates the proxy/ subdir on every boot.
_HOST = os.environ.get("PI_EGRESS_PROXY_HOST", "172.30.16.1")
_PORT = int(os.environ.get("PI_EGRESS_PROXY_PORT", "1080"))
_CA_CERT_PATH = Path(os.environ.get("PI_MITM_CA_PATH", "/srv/pi/state/proxy/mitm-ca.crt"))
_CA_KEY_PATH = Path(os.environ.get("PI_MITM_CA_KEY_PATH", "/srv/pi/state/proxy/mitm-ca.key"))
_LEAF_CACHE_DIR = Path(os.environ.get("PI_EGRESS_LEAF_CACHE_DIR", "/srv/pi/state/proxy/leaf-certs"))
_DEBUG = os.environ.get("PI_EGRESS_DEBUG", "").strip() == "1"

# Per-tunnel I/O timeouts. Vertex API calls can be slow (Sonnet 4.6
# completions ~30-60s for long contexts) so we set generous defaults.
_CONNECT_TIMEOUT = 30.0       # establishing the upstream socket
_HANDSHAKE_TIMEOUT = 30.0     # client→proxy CONNECT handshake
_TUNNEL_IDLE_TIMEOUT = 600.0  # idle on either side before we tear down


# ── Allow-list ───────────────────────────────────────────────────────
#
# Exact-match hostnames that are unconditionally allowed. CONNECT
# host:port pairs match here only if `host.lower()` is in the set.
_ALLOW: frozenset[str] = frozenset({
    # Typst ecosystem.
    "typst.app",
    "packages.typst.org",

    # Iconify (already in Caddy CSP — same set).
    "api.iconify.design",
    "api.unisvg.com",
    "api.simplesvg.com",

    # Rust ecosystem.
    "crates.io",
    "static.crates.io",
    "static.rust-lang.org",
    "dl.rust-lang.org",
    "doc.rust-lang.org",

    # Python docs (apt-installable docs are best-effort).
    "docs.python.org",
})


# Domain-suffix match. Each entry matches a host that EITHER equals
# the entry exactly OR ends with `.<entry>`. This dot-boundary
# semantics prevents `evilgithub.com` from matching `github.com`,
# while still allowing `api.github.com` to match.
_ALLOW_DOMAIN: tuple[str, ...] = (
    # Google APIs (Vertex, AI Studio, GCS, etc.) — owned by Google.
    "googleapis.com",
    "google.com",
    "gstatic.com",

    # GitHub + raw content + LFS.
    "github.com",
    "githubusercontent.com",

    # Hugging Face.
    "huggingface.co",
    "hf.co",

    # npm + pip ecosystems.
    "npmjs.org",
    "npmjs.com",
    "pypi.org",
    "pythonhosted.org",
    "python.org",

    # Debian / Ubuntu apt mirrors. Different distributions resolve to
    # archive.ubuntu.com vs. deb.debian.org vs. ports.ubuntu.com.
    "ubuntu.com",
    "debian.org",
    "launchpad.net",

    # Anthropic direct (in case someone configures a non-Vertex
    # Anthropic key for testing).
    "anthropic.com",

    # Rust ecosystem suffixes (also need exact rust-lang.org).
    "rust-lang.org",
    "crates.io",
)


# MITM suffix. Vertex AI hosts have the regional prefix pattern
# `<region>-aiplatform.googleapis.com` (e.g.
# `us-central1-aiplatform.googleapis.com`) — there's no dot
# before `aiplatform`, so we use plain substring-suffix match
# here. Safe because `*.googleapis.com` is fully Google-owned.
_MITM_HOST_SUFFIX: tuple[str, ...] = (
    "aiplatform.googleapis.com",
)


def _matches_domain(host: str, entry: str) -> bool:
    """host equals entry, OR host ends with `.entry`."""
    return host == entry or host.endswith("." + entry)


def _is_allowed(host: str) -> bool:
    if not host:
        return False
    host = host.lower().strip()
    if host in _ALLOW:
        return True
    return any(_matches_domain(host, d) for d in _ALLOW_DOMAIN)


def _should_mitm(host: str) -> bool:
    if not host:
        return False
    host = host.lower().strip()
    return any(host.endswith(s) for s in _MITM_HOST_SUFFIX)


# ── CA + leaf cert management ────────────────────────────────────────
def _load_or_create_ca() -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """
    Return the backend's MITM CA, generating it on first use.

    The CA cert lives at PI_MITM_CA_PATH (world-readable PEM, mode
    0644), the private key at PI_MITM_CA_KEY_PATH (mode 0600,
    backend-owner-only). We INSIST on these paths being inside
    /srv/pi/state/ — that volume is mounted read-write only into the
    backend container (the per-session containers see ONLY the public
    cert via a separate read-only bind mount).

    Validity: 10 years for the CA (we rotate manually on operator-
    initiated key rotations; the cert is not exposed to the public
    internet so the long lifetime isn't a CA-store-poisoning risk).
    """
    if _CA_CERT_PATH.exists() and _CA_KEY_PATH.exists():
        try:
            cert = x509.load_pem_x509_certificate(_CA_CERT_PATH.read_bytes())
            key = serialization.load_pem_private_key(
                _CA_KEY_PATH.read_bytes(), password=None
            )
            if not isinstance(key, rsa.RSAPrivateKey):
                raise TypeError(f"unexpected CA key type: {type(key)}")
            return cert, key
        except Exception as exc:
            logger.error(
                "egress-proxy: existing CA at %s/%s unreadable (%s); regenerating",
                _CA_CERT_PATH, _CA_KEY_PATH, exc,
            )

    logger.info("egress-proxy: generating new MITM CA at %s", _CA_CERT_PATH)
    _CA_CERT_PATH.parent.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Pi Session MITM CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "digi-setu"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "egress-proxy"),
    ])
    now = _dt.datetime.now(_dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(minutes=5))
        .not_valid_after(now + _dt.timedelta(days=365 * 10))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    _CA_CERT_PATH.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(_CA_CERT_PATH, 0o644)
    _CA_KEY_PATH.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(_CA_KEY_PATH, 0o600)

    return cert, key


_LEAF_LOCK = threading.Lock()
_LEAF_CACHE: dict[str, tuple[Path, Path]] = {}


def _get_leaf_cert(
    hostname: str,
    ca_cert: x509.Certificate,
    ca_key: rsa.RSAPrivateKey,
) -> tuple[Path, Path]:
    """
    Return on-disk paths to a (cert, key) pair signing for `hostname`,
    issued by the backend CA. Cached in memory after first generation;
    regenerated only after backend restart.

    The leaf cert is valid for 30 days and has SAN=DNS:hostname. We
    cache to disk too (under PI_EGRESS_LEAF_CACHE_DIR) so a CA rotation
    can be detected (different issuer fingerprint → cache invalidated)
    and so `ssl.SSLContext.load_cert_chain` can read PEM files instead
    of in-memory bytes (saves a temp-file dance per handshake).
    """
    with _LEAF_LOCK:
        if hostname in _LEAF_CACHE:
            return _LEAF_CACHE[hostname]

        leaf_dir = _LEAF_CACHE_DIR / hostname.replace("/", "_").replace("..", "")
        leaf_dir.mkdir(parents=True, exist_ok=True)
        cert_path = leaf_dir / "cert.pem"
        key_path = leaf_dir / "key.pem"

        # Reuse on-disk if present and signed by the current CA.
        if cert_path.exists() and key_path.exists():
            try:
                disk_cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
                if disk_cert.issuer == ca_cert.subject:
                    now = _dt.datetime.now(_dt.timezone.utc)
                    if disk_cert.not_valid_after_utc > now + _dt.timedelta(days=1):
                        _LEAF_CACHE[hostname] = (cert_path, key_path)
                        return cert_path, key_path
            except Exception:
                pass  # fall through to regenerate

        leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = _dt.datetime.now(_dt.timezone.utc)
        leaf_cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ]))
            .issuer_name(ca_cert.subject)
            .public_key(leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - _dt.timedelta(minutes=5))
            .not_valid_after(now + _dt.timedelta(days=30))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(hostname)]),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(ca_key, hashes.SHA256())
        )

        cert_path.write_bytes(leaf_cert.public_bytes(serialization.Encoding.PEM))
        os.chmod(cert_path, 0o644)
        key_path.write_bytes(
            leaf_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        os.chmod(key_path, 0o600)

        _LEAF_CACHE[hostname] = (cert_path, key_path)
        return cert_path, key_path


# ── Vertex token broker ──────────────────────────────────────────────
#
# We use Application Default Credentials. On the GCE VM that resolves
# to the metadata server's workload-identity token; on the operator's
# laptop it's whatever `gcloud auth application-default login` wrote
# to ~/.config/gcloud/application_default_credentials.json.
#
# google-auth caches the token internally and refreshes when within 5
# minutes of expiry. We just ask for `creds.token` after refreshing
# if needed — thread-safe via a single lock around the refresh call
# (google.auth.credentials.Credentials is NOT thread-safe by default).
_CREDS_LOCK = threading.Lock()
_CREDS = None  # type: ignore[var-annotated]


def _init_credentials() -> None:
    """Load ADC once at proxy start. Failure logs but doesn't crash."""
    global _CREDS
    try:
        import google.auth
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        _CREDS = creds
        logger.info("egress-proxy: ADC loaded (type=%s)", type(creds).__name__)
    except Exception as exc:
        logger.warning(
            "egress-proxy: ADC unavailable — Vertex MITM will return 503 "
            "until the host has Application Default Credentials configured "
            "(running on GCE? `gcloud auth application-default login` on "
            "the operator's laptop?): %s",
            exc,
        )
        _CREDS = None


def _get_vertex_token() -> Optional[str]:
    """Return a fresh Vertex bearer token, or None if ADC is unavailable."""
    if _CREDS is None:
        return None
    with _CREDS_LOCK:
        try:
            from google.auth.transport.requests import Request
            if not _CREDS.valid:
                _CREDS.refresh(Request())
            return _CREDS.token
        except Exception as exc:
            logger.error("egress-proxy: token refresh failed: %s", exc)
            return None


# ── Connection handler ───────────────────────────────────────────────
class _ConnectHandler(socketserver.BaseRequestHandler):
    """
    Per-connection TCP handler. Reads the HTTP CONNECT preamble,
    decides allow / deny / MITM, and either splices bytes (relay) or
    terminates TLS + injects auth (MITM) before forwarding upstream.
    """

    # Populated by EgressProxy._make_handler before SocketServer
    # constructs the handler instance.
    _ca_cert: x509.Certificate = None  # type: ignore[assignment]
    _ca_key: rsa.RSAPrivateKey = None  # type: ignore[assignment]

    def handle(self) -> None:
        sock: socket.socket = self.request
        sock.settimeout(_HANDSHAKE_TIMEOUT)
        peer = "{}:{}".format(*self.client_address[:2])
        try:
            request_line = self._read_request_line(sock)
            if request_line is None:
                return

            parts = request_line.split()
            if len(parts) < 2:
                self._respond(sock, 400, "Bad Request",
                              extra_headers={"X-Egress-Reason": "malformed request line"})
                return

            method = parts[0].upper()

            # Special-case: HTTP GET to metadata.google.internal. The
            # Node `google-auth-library` that pi-ai uses does its own
            # token bootstrap by calling the GCE metadata server BEFORE
            # any actual Vertex API call — and it routes that bootstrap
            # through HTTP_PROXY since pi-ai's HTTP client honours it.
            # The metadata server is NOT on our allow-list (we don't
            # want containers fetching real tokens), but the bootstrap
            # NEEDS to succeed or the SDK gives up before issuing the
            # Vertex call where we actually inject the auth header.
            #
            # Solution: intercept the metadata-server request inside
            # the proxy and synthesise a fake token response. The token
            # value doesn't matter — the proxy strips and replaces the
            # Authorization header on every Vertex request anyway. As
            # long as the SDK gets a 200 with a parseable JSON token,
            # it proceeds to the real Vertex call.
            if method == "GET" and self._is_metadata_request(parts[1]):
                # Drain the request headers (we don't care about
                # them — the path is enough to dispatch). Caller
                # of _serve_fake_metadata is responsible for the
                # drain because the TLS-MITM path uses a different
                # drain primitive on the wrapped socket.
                self._drain_remaining_headers(sock)
                self._serve_fake_metadata(sock, parts[1])
                return

            if method != "CONNECT":
                self._respond(sock, 405, "Method Not Allowed",
                              extra_headers={"X-Egress-Reason": "only CONNECT supported"})
                return

            target = parts[1]
            if ":" not in target:
                self._respond(sock, 400, "Bad Request",
                              extra_headers={"X-Egress-Reason": "missing port in CONNECT target"})
                return
            host, _, port_s = target.rpartition(":")
            host = host.strip("[]").lower()
            try:
                port = int(port_s)
            except ValueError:
                self._respond(sock, 400, "Bad Request",
                              extra_headers={"X-Egress-Reason": "non-numeric port"})
                return

            self._drain_remaining_headers(sock)

            # Metadata server CONNECT. The Node `gcp-metadata` lib in
            # pi-ai routes its bootstrap fetch through HTTPS_PROXY,
            # which means it issues `CONNECT metadata.google.internal:80
            # HTTP/1.1` (note: port 80, plain HTTP — not 443). After
            # we ack with 200 the client sends plain HTTP request
            # bytes inside the tunnel, NOT a TLS handshake. So we must
            # branch on port:
            #
            #   port 80   → cleartext tunnel; read the HTTP request
            #               line directly off the raw socket and reply
            #               with the synthetic metadata response.
            #
            #   port 443  → MITM with our CA-signed leaf cert; same
            #               synthetic response over the inner TLS.
            #
            # The previous unconditional MITM attempt blew up with
            # `[SSL: HTTP_REQUEST]` because we tried to TLS-accept a
            # cleartext HTTP request that came over a port-80 tunnel.
            if host in ("metadata.google.internal", "metadata.goog", "169.254.169.254"):
                self._respond(sock, 200, "Connection established")
                if port == 443:
                    self._mitm_metadata(sock, host)
                else:
                    self._serve_metadata_over_plain(sock)
                return

            if not _is_allowed(host):
                logger.info("egress-proxy: %s DENY %s:%d (not on allow-list)", peer, host, port)
                self._respond(
                    sock, 451, "Unavailable For Legal Reasons",
                    extra_headers={"X-Egress-Reason": f"host '{host}' not on allow-list"},
                    body=(
                        f"Egress to host '{host}' is not allowed.\n"
                        "If this is a legitimate package source, ask the operator to "
                        "add it to the allow-list in services/egress_proxy.py.\n"
                    ).encode("utf-8"),
                )
                return

            self._respond(sock, 200, "Connection established")

            if _should_mitm(host):
                if _DEBUG:
                    logger.info("egress-proxy: %s MITM %s:%d", peer, host, port)
                self._mitm_tunnel(sock, host, port)
            else:
                if _DEBUG:
                    logger.info("egress-proxy: %s RELAY %s:%d", peer, host, port)
                self._relay_tunnel(sock, host, port)

        except (socket.timeout, OSError) as exc:
            logger.debug("egress-proxy: %s connection error: %s", peer, exc)
        except Exception:
            logger.exception("egress-proxy: %s handler crash", peer)
        finally:
            try:
                sock.close()
            except Exception:
                pass

    # ── helpers ──────────────────────────────────────────────────────
    def _is_metadata_request(self, target: str) -> bool:
        """
        True if the request line target points at the GCE metadata
        server. Forward-proxy GETs use absolute-form URLs, e.g.:
            GET http://metadata.google.internal/computeMetadata/v1/...
        """
        t = target.lower()
        return (
            "metadata.google.internal" in t
            or "169.254.169.254" in t
            or "metadata.goog" in t  # alt host name some libs try
        )

    def _serve_fake_metadata(self, sock, target: str) -> None:
        """
        Respond with a synthetic GCE-metadata-server response so the
        Node google-auth-library's token bootstrap succeeds without
        ever reaching the real metadata server. We honour the two
        endpoints pi-ai exercises during startup:

          /computeMetadata/v1/instance/service-accounts/default/token
              → fake JSON token (overridden by proxy on real Vertex
                requests anyway)

          /computeMetadata/v1/project/project-id (and "numeric-project-id")
              → the GCP project the backend itself runs against, so
                the SDK's project resolution matches ours

          everything else
              → 200 with empty body, prevents the lib from giving up

        IMPORTANT: This function does NOT drain the request headers —
        the caller is responsible because the right drain primitive
        depends on whether `sock` is a raw socket or a TLS-wrapped
        one (`SSLSocket` doesn't deliver bytes via raw `recv()` and
        a non-TLS drain on a TLS-wrapped socket hangs forever).
        """
        path = ""
        if "://" in target:
            _, _, after = target.partition("://")
            _, _, path_part = after.partition("/")
            path = "/" + path_part if path_part else "/"
        else:
            path = target

        path_l = path.lower()
        peer = "{}:{}".format(*self.client_address[:2])
        logger.info("egress-proxy: %s METADATA-FAKE %s", peer, path)

        if "/token" in path_l:
            # Fake bearer that satisfies the SDK's parsing. The proxy
            # injects the real one on the upstream Vertex request.
            body = (
                b'{"access_token":"fake-egress-bootstrap-token",'
                b'"expires_in":3600,"token_type":"Bearer"}'
            )
            ctype = "application/json; charset=utf-8"
        elif "project-id" in path_l or "numeric-project-id" in path_l:
            project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip().encode("utf-8")
            body = project or b"unknown-project"
            ctype = "text/plain; charset=utf-8"
        elif "/scopes" in path_l:
            body = (
                b"https://www.googleapis.com/auth/cloud-platform\n"
                b"https://www.googleapis.com/auth/userinfo.email\n"
            )
            ctype = "text/plain; charset=utf-8"
        else:
            body = b""
            ctype = "text/plain; charset=utf-8"

        resp = (
            f"HTTP/1.1 200 OK\r\n"
            f"Metadata-Flavor: Google\r\n"
            f"Content-Type: {ctype}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("ascii")
        try:
            sock.sendall(resp)
            if body:
                sock.sendall(body)
        except OSError:
            pass

    def _read_request_line(self, sock: socket.socket) -> Optional[str]:
        """Read up to the first CRLF, return as ASCII string (or None on EOF)."""
        buf = bytearray()
        while True:
            chunk = sock.recv(1)
            if not chunk:
                return None
            buf.extend(chunk)
            if buf.endswith(b"\r\n"):
                return buf[:-2].decode("ascii", errors="replace")
            if len(buf) > 8192:
                return None  # oversized request line

    def _drain_remaining_headers(self, sock: socket.socket) -> None:
        """Read until empty line (end of headers). Discard them — we
        only care about the request line for CONNECT."""
        buf = bytearray()
        while True:
            chunk = sock.recv(1)
            if not chunk:
                return
            buf.extend(chunk)
            if buf.endswith(b"\r\n\r\n"):
                return
            if len(buf) > 16384:
                return  # cap

    def _respond(
        self,
        sock: socket.socket,
        status: int,
        reason: str,
        *,
        extra_headers: Optional[dict[str, str]] = None,
        body: bytes = b"",
    ) -> None:
        lines = [f"HTTP/1.1 {status} {reason}"]
        lines.append("Connection: close")
        if extra_headers:
            for k, v in extra_headers.items():
                lines.append(f"{k}: {v}")
        if body:
            lines.append(f"Content-Length: {len(body)}")
            lines.append("Content-Type: text/plain; charset=utf-8")
        lines.append("")
        lines.append("")
        try:
            sock.sendall("\r\n".join(lines).encode("ascii", errors="replace"))
            if body:
                sock.sendall(body)
        except OSError:
            pass

    # ── relay (no TLS termination) ───────────────────────────────────
    def _relay_tunnel(self, client: socket.socket, host: str, port: int) -> None:
        try:
            upstream = socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT)
        except (OSError, socket.gaierror) as exc:
            logger.warning("egress-proxy: relay upstream connect %s:%d failed: %s", host, port, exc)
            return

        client.settimeout(_TUNNEL_IDLE_TIMEOUT)
        upstream.settimeout(_TUNNEL_IDLE_TIMEOUT)
        try:
            self._splice(client, upstream)
        finally:
            try:
                upstream.close()
            except OSError:
                pass

    # ── Cleartext metadata over CONNECT-port-80 tunnel ───────────────
    def _serve_metadata_over_plain(self, sock: socket.socket) -> None:
        """
        After the CONNECT 200 ack, the client (Node gcp-metadata)
        writes a plain HTTP request directly into the tunnel. We
        read the request line, drain headers, and reply with the
        same synthetic payload as the HTTP_PROXY and TLS-MITM paths.
        """
        request_line = self._read_request_line(sock)
        if not request_line:
            return
        self._drain_remaining_headers(sock)
        parts = request_line.split()
        target = parts[1] if len(parts) >= 2 else "/"
        self._serve_fake_metadata(sock, target)

    # ── MITM metadata server (synthetic token response) ──────────────
    def _mitm_metadata(self, raw_client: socket.socket, host: str) -> None:
        """Terminate TLS to the metadata host and serve a synthetic
        token response — same payloads as the HTTP_PROXY path."""
        cert_path, key_path = _get_leaf_cert(host, self._ca_cert, self._ca_key)
        server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        server_ctx.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
        try:
            tls_client = server_ctx.wrap_socket(raw_client, server_side=True)
        except (ssl.SSLError, OSError) as exc:
            logger.warning("egress-proxy: %s metadata MITM TLS failed: %s", host, exc)
            return
        try:
            request_line = self._read_request_line_tls(tls_client)
            if not request_line:
                return
            self._drain_remaining_headers_tls(tls_client)
            parts = request_line.split()
            target = parts[1] if len(parts) >= 2 else "/"
            self._serve_fake_metadata(tls_client, target)
        finally:
            try:
                tls_client.close()
            except OSError:
                pass

    def _read_request_line_tls(self, sock) -> Optional[str]:
        buf = bytearray()
        while True:
            try:
                chunk = sock.recv(1)
            except (ssl.SSLError, OSError):
                return None
            if not chunk:
                return None
            buf.extend(chunk)
            if buf.endswith(b"\r\n"):
                return buf[:-2].decode("ascii", errors="replace")
            if len(buf) > 8192:
                return None

    def _drain_remaining_headers_tls(self, sock) -> None:
        buf = bytearray()
        while True:
            try:
                chunk = sock.recv(1)
            except (ssl.SSLError, OSError):
                return
            if not chunk:
                return
            buf.extend(chunk)
            if buf.endswith(b"\r\n\r\n"):
                return
            if len(buf) > 16384:
                return

    # ── MITM (terminate TLS, inject auth header) ─────────────────────
    def _mitm_tunnel(self, raw_client: socket.socket, host: str, port: int) -> None:
        cert_path, key_path = _get_leaf_cert(host, self._ca_cert, self._ca_key)
        server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        server_ctx.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

        try:
            tls_client = server_ctx.wrap_socket(raw_client, server_side=True)
        except (ssl.SSLError, OSError) as exc:
            logger.warning("egress-proxy: %s MITM TLS handshake failed: %s", host, exc)
            return

        try:
            self._mitm_proxy_one_request(tls_client, host, port)
        finally:
            try:
                tls_client.close()
            except OSError:
                pass

    def _mitm_proxy_one_request(
        self,
        tls_client: ssl.SSLSocket,
        host: str,
        port: int,
    ) -> None:
        # Read the full HTTP request from the client. We read until
        # \r\n\r\n for headers, parse Content-Length, then read body.
        # Streaming bodies (chunked / no Content-Length) are forwarded
        # untouched after the headers — we don't try to interpret
        # them, just splice.
        tls_client.settimeout(_TUNNEL_IDLE_TIMEOUT)

        try:
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = tls_client.recv(8192)
                if not chunk:
                    return
                head += chunk
                if len(head) > 64 * 1024:
                    logger.warning("egress-proxy: %s oversized request headers", host)
                    return

            head_blob, _, body_so_far = head.partition(b"\r\n\r\n")
            request_line, _, header_blob = head_blob.partition(b"\r\n")

            # Parse headers (case-insensitive).
            parsed_headers: list[tuple[bytes, bytes]] = []
            for raw_line in header_blob.split(b"\r\n"):
                if not raw_line:
                    continue
                k, _, v = raw_line.partition(b":")
                parsed_headers.append((k.strip(), v.strip()))

            # Drop client-supplied Authorization / X-Goog-User-Project /
            # Proxy-Authorization. We're injecting our own.
            stripped = [
                (k, v)
                for k, v in parsed_headers
                if k.lower() not in (
                    b"authorization",
                    b"proxy-authorization",
                    b"x-goog-user-project",
                )
            ]

            token = _get_vertex_token()
            if not token:
                # ADC unavailable. Reply with a synthetic 503 inside
                # the wrapped TLS so the AI's SDK gets a clear error
                # instead of a hung connection.
                resp = (
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Length: 0\r\n"
                    b"X-Egress-Reason: Vertex ADC unavailable on backend\r\n"
                    b"Connection: close\r\n\r\n"
                )
                try:
                    tls_client.sendall(resp)
                except OSError:
                    pass
                return

            project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
            stripped.append((b"Authorization", f"Bearer {token}".encode("ascii")))
            if project:
                stripped.append((b"X-Goog-User-Project", project.encode("ascii")))

            new_head = request_line + b"\r\n"
            for k, v in stripped:
                new_head += k + b": " + v + b"\r\n"
            new_head += b"\r\n"

            content_length = 0
            for k, v in stripped:
                if k.lower() == b"content-length":
                    try:
                        content_length = int(v)
                    except ValueError:
                        content_length = 0
                    break

            # Open TLS to upstream.
            try:
                upstream_raw = socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT)
            except (OSError, socket.gaierror) as exc:
                logger.warning("egress-proxy: %s upstream connect failed: %s", host, exc)
                return
            upstream_ctx = ssl.create_default_context()
            try:
                upstream_tls = upstream_ctx.wrap_socket(
                    upstream_raw, server_hostname=host
                )
            except (ssl.SSLError, OSError) as exc:
                logger.warning("egress-proxy: %s upstream TLS failed: %s", host, exc)
                try:
                    upstream_raw.close()
                except OSError:
                    pass
                return
            upstream_tls.settimeout(_TUNNEL_IDLE_TIMEOUT)

            try:
                upstream_tls.sendall(new_head)
                if body_so_far:
                    upstream_tls.sendall(body_so_far)
                # Read remaining body from client and forward.
                remaining = content_length - len(body_so_far)
                while remaining > 0:
                    chunk = tls_client.recv(min(remaining, 65536))
                    if not chunk:
                        break
                    upstream_tls.sendall(chunk)
                    remaining -= len(chunk)

                # Now splice both directions until either side closes.
                self._splice(tls_client, upstream_tls)
            finally:
                try:
                    upstream_tls.close()
                except OSError:
                    pass

        except (ssl.SSLError, OSError) as exc:
            logger.debug("egress-proxy: %s MITM IO error: %s", host, exc)

    # ── byte splicer ─────────────────────────────────────────────────
    def _splice(self, a, b) -> None:
        """
        Bidirectional copy a<->b. Returns when either side closes.

        Two threads, each forwarding one direction. Each thread closes
        the OPPOSITE side's write half on EOF so the peer learns the
        flow ended (half-close) without immediately killing the
        return path.
        """
        def pump(src, dst, label: str) -> None:
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except (OSError, ssl.SSLError) as exc:
                logger.debug("egress-proxy: pump %s eof: %s", label, exc)
            finally:
                try:
                    if isinstance(dst, ssl.SSLSocket):
                        # SSLSocket.shutdown() takes flags but SSLSocket
                        # disallows half-close cleanly. Best-effort.
                        dst.unwrap()
                    else:
                        dst.shutdown(socket.SHUT_WR)
                except (OSError, ssl.SSLError):
                    pass

        t1 = threading.Thread(target=pump, args=(a, b, "→"), daemon=True)
        t2 = threading.Thread(target=pump, args=(b, a, "←"), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()


# ── Server bootstrap ─────────────────────────────────────────────────
class _ThreadingProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True
    # Bigger backlog than default 5 — bursty container restart on a
    # backend redeploy can momentarily queue dozens of CONNECTs.
    request_queue_size = 64


_SERVER: Optional[_ThreadingProxyServer] = None
_SERVER_THREAD: Optional[threading.Thread] = None


def start_egress_proxy() -> None:
    """
    Start the proxy in a daemon thread. Idempotent — calling twice
    is a no-op (lifespan startup might fire twice during reload).

    Failure modes:
      * CA cert unwritable (e.g. /srv/pi/state not bind-mounted in
        dev): logs a warning and SKIPS starting the proxy. The
        backend continues to run; per-session containers will fail
        to talk to anything until the operator fixes the path.
      * Listen address already in use: logs an error, propagates.
        Usually means a previous backend instance left the socket
        bound (systemd should have killed it; if not, `lsof -i :1080`
        will show the offender).
    """
    global _SERVER, _SERVER_THREAD

    if _SERVER is not None:
        logger.debug("egress-proxy: already started, skipping")
        return

    try:
        ca_cert, ca_key = _load_or_create_ca()
    except OSError as exc:
        logger.warning(
            "egress-proxy: cannot create CA at %s (%s); proxy will NOT start. "
            "Per-session containers will fail to reach Vertex/etc until this "
            "is resolved (run as a user with write access to /srv/pi/state).",
            _CA_CERT_PATH, exc,
        )
        return

    _init_credentials()

    handler = _ConnectHandler
    handler._ca_cert = ca_cert
    handler._ca_key = ca_key

    bind_host = _HOST
    # Allow listening on 0.0.0.0 if explicitly configured for
    # compose dev (where the bridge gateway IP isn't reachable from
    # the backend container side).
    if os.environ.get("PI_EGRESS_PROXY_BIND_ALL", "").strip() == "1":
        bind_host = "0.0.0.0"

    try:
        _SERVER = _ThreadingProxyServer((bind_host, _PORT), handler)
    except OSError as exc:
        logger.error(
            "egress-proxy: failed to bind %s:%d (%s). Per-session containers "
            "will not be able to make any outbound connection.",
            bind_host, _PORT, exc,
        )
        _SERVER = None
        return

    _SERVER_THREAD = threading.Thread(
        target=_SERVER.serve_forever,
        name="egress-proxy",
        daemon=True,
    )
    _SERVER_THREAD.start()

    logger.info(
        "egress-proxy: listening on %s:%d (CA=%s, allow=%d hosts + %d domains)",
        bind_host, _PORT, _CA_CERT_PATH, len(_ALLOW), len(_ALLOW_DOMAIN),
    )


def stop_egress_proxy() -> None:
    """Shut down the proxy (idempotent)."""
    global _SERVER, _SERVER_THREAD

    if _SERVER is not None:
        try:
            _SERVER.shutdown()
            _SERVER.server_close()
        except Exception as exc:
            logger.warning("egress-proxy: shutdown error: %s", exc)
        finally:
            _SERVER = None
    if _SERVER_THREAD is not None:
        _SERVER_THREAD.join(timeout=2.0)
        _SERVER_THREAD = None


if __name__ == "__main__":
    # `python -m services.egress_proxy` — useful for ad-hoc smoke
    # tests on the operator's laptop. Just starts the proxy and
    # blocks forever.
    logging.basicConfig(
        level=logging.DEBUG if _DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    start_egress_proxy()
    if _SERVER is None:
        sys.exit(1)
    try:
        if _SERVER_THREAD is not None:
            _SERVER_THREAD.join()
    except KeyboardInterrupt:
        stop_egress_proxy()
