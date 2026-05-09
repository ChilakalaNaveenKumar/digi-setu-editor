/**
 * Desktop OAuth + billing deep-link orchestration.
 *
 * The Tauri webview can't run Clerk's SignIn component directly because:
 *   1. Clerk's anti-phishing posture refuses non-default-browser UAs
 *      for some flows (passkeys, WebAuthn).
 *   2. Stripe Checkout's 3DS step opens in a new tab — webviews don't
 *      have tabs.
 *   3. Users expect their existing browser autofill / SSO / Apple
 *      Pay / etc. to "just work" during sign-in.
 *
 * So the desktop flow bounces login + checkout out to the system
 * browser. After Clerk / Stripe is done it redirects to a deep link
 * (`digi-setu://...`), which the OS hands back to the running
 * Tauri app. We then forward it to the FastAPI sidecar's
 * `/api/auth/desktop-exchange` endpoint, which stamps the session
 * cookie locally so subsequent api/client calls authenticate.
 *
 * URL contract
 * ────────────
 *   digi-setu://auth/callback?session_id=<clerk-sess-id>&state=<csrf>
 *   digi-setu://billing/return?session=<stripe-session-id>&billing=success
 *   digi-setu://billing/return?billing=cancel
 *
 * Note: the older `?token=…` form is still accepted by the deep-link
 * handler for backward-compat, but the production web bounce page
 * (`/desktop/sign-in`) now mints a Clerk session via
 * `clerk.sessions.create()` and forwards the resulting `session_id`
 * directly. The desktop sidecar then mints a fresh JWT from it on
 * demand via `/api/auth/desktop-refresh`, and the SPA stashes the
 * `session_id` in the OS keychain so the user stays signed in
 * across app restarts.
 *
 * The CSRF `state` is a 24-byte random hex generated at sign-in start
 * time and stored in `sessionStorage`; the deep-link handler
 * cross-checks it before exchanging the token, which prevents a
 * malicious app from fabricating a deep-link in our scheme to log
 * the user into someone else's account.
 *
 * What needs to be wired up on the web (`digi-setu.com`) side
 * ─────────────────────────────────────────────────────────────
 *   - A `/desktop/sign-in?state=<csrf>&return=<deeplink>` page that:
 *       1. Renders Clerk's SignIn component.
 *       2. After sign-in succeeds, calls Clerk's `createTicket` API
 *          (server-side) to mint a single-use auth ticket.
 *       3. window.location = `${return}?token=${ticket}&state=${csrf}`
 *
 *   - Stripe Checkout success_url + cancel_url already accept
 *     deep-link schemes; just pass `digi-setu://billing/return`.
 *
 *   - Clerk dashboard:
 *       Authorized origins:        https://digi-setu.com
 *       Authorized redirect URIs:  digi-setu://auth/callback
 *       Allowed redirect schemes:  digi-setu
 */

import { isDesktop, onDeepLink, openExternal } from "./native-bridge";
import {
  deleteSessionId,
  loadSessionId,
  storeSessionId,
} from "./secure-storage";
import { apiPost, getApiBase } from "../api/client";

const STATE_STORAGE_KEY = "digi-setu:desktop-auth:state";

/** Hex-encoded CSRF token; generated once per sign-in attempt. */
function _newState(): string {
  const buf = new Uint8Array(24);
  crypto.getRandomValues(buf);
  return Array.from(buf)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Kick off browser-based sign-in.
 *
 * Returns the CSRF state token so the caller can show a "waiting
 * for browser…" status and time it out.
 *
 * Architecture (the long version):
 *
 *   1. We generate a CSRF state token and pre-register it with the
 *      sidecar via /api/auth/desktop-prepare-state. The sidecar
 *      remembers it for ~10 minutes; the matching callback below
 *      will only be honoured if its `state` matches one we registered.
 *
 *   2. We open the user's default browser at
 *      `<web_base>/desktop/sign-in?state=…&return=<localhost_callback>`.
 *      The web bounce page renders Clerk's SignIn component inline.
 *
 *   3. After Clerk authenticates, the bounce page hits
 *      `POST /api/auth/desktop-mint-handoff` (on the WEB backend) to
 *      mint a fresh Clerk session, then top-level navigates to
 *      `<localhost_callback>?session_id=…&state=…`.
 *
 *   4. The user's browser issues that GET to our local sidecar.
 *      The sidecar validates the state, mints a JWT from the session
 *      id, and renders a "You're signed in! You can close this tab"
 *      HTML page.
 *
 *   5. The user clicks back to the desktop window. App.vue's window-
 *      focus listener fires `auth.refresh()` which calls
 *      `/api/auth/whoami` and sees `signed_in=true`. The router
 *      gate flips and the user lands on the picker.
 *
 * Why localhost and not `digi-setu://` deep-links:
 *   On macOS in `tauri dev` the binary runs without an .app bundle
 *   so LaunchServices has no `digi-setu://` handler registered.
 *   Even with a synthesised .app wrapper, single-instance + Apple
 *   Event delivery to the running PID is a known Tauri-2 dev
 *   footgun. Localhost callbacks work uniformly across dev / prod
 *   on every platform — the same pattern gh CLI / gcloud CLI use.
 *
 * The web URL (where Clerk renders) is resolved by
 * `_resolveWebAuthBase()`: `VITE_DESKTOP_AUTH_URL` in dev (typically
 * `http://localhost:5174` pointing at a locally-running web stack)
 * and `https://digi-setu.com` in packaged production builds.
 */
export async function startDesktopSignIn(): Promise<string> {
  if (!isDesktop()) {
    throw new Error("startDesktopSignIn called outside desktop mode");
  }

  const state = _newState();
  sessionStorage.setItem(STATE_STORAGE_KEY, state);

  // Pre-register the state token with the sidecar so the localhost
  // callback knows to accept it. If this fails the user can't sign
  // in at all, so surface the error rather than letting it silently
  // produce a "Sign-in link expired" page later.
  await apiPost<{ ok: true }>("/api/auth/desktop-prepare-state", { state });

  // Localhost callback URL. The sidecar's port is randomized and
  // bound only to 127.0.0.1, so this URL is only meaningful from
  // within the user's machine — exactly what we want.
  const apiBase = getApiBase().replace(/\/+$/, "");
  const returnUrl = `${apiBase}/api/auth/desktop-callback`;
  const webBase = _resolveWebAuthBase();
  const url = `${webBase}/desktop/sign-in?state=${encodeURIComponent(
    state,
  )}&return=${encodeURIComponent(returnUrl)}`;

  await openExternal(url);
  return state;
}

/**
 * Open Stripe Checkout (or Customer Portal) in the system browser
 * with deep-link return URLs. The backend's billing routes already
 * accept a `return_url` override — we just pass our scheme.
 */
export async function openStripeUrl(stripeUrl: string): Promise<void> {
  if (!isDesktop()) {
    window.location.href = stripeUrl;
    return;
  }
  await openExternal(stripeUrl);
}

/**
 * Wire deep-link callbacks into the SPA's auth + billing stores.
 * Call exactly once at boot. The handler cross-checks the CSRF
 * state, exchanges the one-time token for a session via the local
 * sidecar, and emits internal events the stores can listen for.
 *
 * Returns the unsubscribe function — keep it around if you ever
 * need to tear the bridge down (HMR cleanup mainly).
 */
export async function installDeepLinkBridge(opts: {
  onAuthSuccess?: () => void | Promise<void>;
  onAuthFailure?: (reason: string) => void;
  onBillingSuccess?: (stripeSessionId: string) => void | Promise<void>;
  onBillingCancel?: () => void;
} = {}): Promise<() => void> {
  if (!isDesktop()) return () => {};

  return onDeepLink(async ({ url }) => {
    let parsed: URL;
    try {
      parsed = new URL(url);
    } catch {
      console.warn("[desktop-auth] malformed deep-link URL:", url);
      return;
    }

    const path = parsed.host + parsed.pathname; // tauri://localhost-style URLs put the path after host
    const params = parsed.searchParams;

    // ── auth/callback ─────────────────────────────────────────
    if (path.endsWith("auth/callback") || parsed.pathname.endsWith("/auth/callback")) {
      // Two flavours of this URL exist:
      //   - new (preferred): ?session_id=<sess_…>&state=<csrf>
      //     The web bounce page minted a Clerk session via
      //     /api/auth/desktop-mint-handoff and forwarded the id.
      //     We POST it to /desktop-refresh which mints a fresh JWT
      //     and caches it sidecar-side.
      //   - legacy: ?token=<one-time-clerk-ticket>&state=<csrf>
      //     Older bounce-page contract. Still accepted via
      //     /desktop-exchange so dev environments and any in-flight
      //     OAuth bounces from a previous version don't break.
      const sessionId = params.get("session_id");
      const token = params.get("token");
      const state = params.get("state");
      const expectedState = sessionStorage.getItem(STATE_STORAGE_KEY);

      if (!sessionId && !token) {
        opts.onAuthFailure?.("missing session_id/token in callback");
        return;
      }
      if (!state || !expectedState || state !== expectedState) {
        opts.onAuthFailure?.("CSRF state mismatch");
        return;
      }
      sessionStorage.removeItem(STATE_STORAGE_KEY);

      try {
        let resolvedSessionId: string | null = null;
        if (sessionId) {
          // Preferred path: the web bounce already created a Clerk
          // session; we just refresh against it.
          const result = await apiPost<{
            ok: true;
            user_id: string;
            mode: string;
          }>("/api/auth/desktop-refresh", { session_id: sessionId });
          if (result.ok) resolvedSessionId = sessionId;
        } else if (token) {
          const result = await apiPost<{
            ok: true;
            user_id: string;
            session_id: string;
            mode: string;
          }>("/api/auth/desktop-exchange", { token });
          resolvedSessionId = result.session_id || null;
        }

        // Persist the Clerk session id in the OS keychain so future
        // launches can silently re-mint a JWT without bouncing
        // through the browser. We deliberately store the long-lived
        // session id (not the JWT itself) — Cursor's pattern for
        // "stay signed in for weeks".
        if (resolvedSessionId) {
          await storeSessionId(resolvedSessionId);
        }
        await opts.onAuthSuccess?.();
      } catch (err) {
        opts.onAuthFailure?.(
          err instanceof Error ? err.message : "exchange failed",
        );
      }
      return;
    }

    // ── billing/return ────────────────────────────────────────
    if (path.endsWith("billing/return") || parsed.pathname.endsWith("/billing/return")) {
      const status = params.get("billing");
      const session = params.get("session");
      if (status === "success" && session) {
        await opts.onBillingSuccess?.(session);
      } else {
        opts.onBillingCancel?.();
      }
      return;
    }

    console.warn("[desktop-auth] unrecognised deep-link path:", parsed.pathname);
  });
}

/**
 * Boot-time silent SSO restore. Pulls the Clerk session id from the
 * OS keychain (if any) and POSTs it to /api/auth/desktop-refresh.
 *
 * Returns:
 *   - true   → session was restored; SPA proceeds as signed-in.
 *   - false  → no cached session, refresh failed, or web mode. The
 *              SPA falls through to its normal auth-required path
 *              (Welcome screen).
 *
 * Idempotent and side-effect-safe: a refresh failure clears the
 * stale keychain entry so the user isn't trapped in a 401 loop.
 */
export async function restoreDesktopSession(): Promise<boolean> {
  if (!isDesktop()) return false;
  const sessionId = await loadSessionId();
  if (!sessionId) return false;

  try {
    const result = await apiPost<{ ok: true; user_id: string; mode: string }>(
      "/api/auth/desktop-refresh",
      { session_id: sessionId },
    );
    return !!result?.ok;
  } catch (err) {
    // 401 here means "session no longer valid on Clerk's side"
    // (revoked, expired, dashboard force-logout). Clear the stale
    // keychain entry so we don't keep retrying every launch.
    console.warn("[desktop-auth] silent refresh failed", err);
    await deleteSessionId();
    return false;
  }
}

/**
 * Sign out completely: tell the backend to drop its in-memory cache
 * AND wipe the OS-keychain entry so the next launch lands on the
 * Welcome screen as if it were a first-time user.
 */
export async function signOutDesktop(): Promise<void> {
  try {
    await apiPost<{ ok: true }>("/api/auth/desktop-sign-out", {});
  } catch (err) {
    // Backend may already be gone (sign-out during sidecar restart);
    // ignore. We still want to clear the keychain locally.
    console.warn("[desktop-auth] sign-out POST failed", err);
  }
  await deleteSessionId();
}

function _resolveWebAuthBase(): string {
  // Resolution order:
  //   1. `VITE_DESKTOP_AUTH_URL` env (set per build / per `npm run dev`).
  //      Use this in dev to point at a locally-running web stack
  //      (e.g. http://localhost:5174) so you can walk the full
  //      sign-in flow without deploying production.
  //   2. Hardcoded production default `https://digi-setu.com`. Once
  //      we ship signed installers this is what end users hit.
  // We deliberately do NOT fall back to the sidecar's loopback URL
  // any more — the sidecar doesn't host the Clerk SignIn UI, only the
  // web stack does, and silently falling back there made the
  // "browser opens but page is blank" failure mode hard to debug.
  const env = (import.meta as { env?: Record<string, string> }).env;
  const fromEnv = env?.VITE_DESKTOP_AUTH_URL;
  if (fromEnv) return fromEnv.replace(/\/+$/, "");
  return "https://digi-setu.com";
}
