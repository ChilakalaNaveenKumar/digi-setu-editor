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
 * (`pi-typst-test://...`), which the OS hands back to the running
 * Tauri app. We then forward it to the FastAPI sidecar's
 * `/api/auth/desktop-exchange` endpoint, which stamps the session
 * cookie locally so subsequent api/client calls authenticate.
 *
 * URL contract
 * ────────────
 *   pi-typst-test://auth/callback?token=<one-time-clerk-ticket>&state=<csrf>
 *   pi-typst-test://billing/return?session=<stripe-session-id>&billing=success
 *   pi-typst-test://billing/return?billing=cancel
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
 *     deep-link schemes; just pass `pi-typst-test://billing/return`.
 *
 *   - Clerk dashboard:
 *       Authorized origins:        https://digi-setu.com
 *       Authorized redirect URIs:  pi-typst-test://auth/callback
 *                                  digi-setu://auth/callback
 *       Allowed redirect schemes:  pi-typst-test, digi-setu
 */

import { isDesktop, onDeepLink, openExternal } from "./native-bridge";
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
 * Kick off browser-based sign-in. Returns the CSRF state token so the
 * caller can show a "waiting for browser…" status and time it out.
 *
 * The web URL (where Clerk renders) is computed from
 * `getApiBase()` in dev (we point at the local sidecar's host so the
 * dev loop doesn't depend on the prod web app being up) and from
 * `import.meta.env.VITE_DESKTOP_AUTH_URL` in production builds (set
 * to `https://digi-setu.com` typically).
 */
export async function startDesktopSignIn(): Promise<string> {
  if (!isDesktop()) {
    throw new Error("startDesktopSignIn called outside desktop mode");
  }

  const state = _newState();
  sessionStorage.setItem(STATE_STORAGE_KEY, state);

  const returnUrl = "pi-typst-test://auth/callback";
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
      const token = params.get("token");
      const state = params.get("state");
      const expectedState = sessionStorage.getItem(STATE_STORAGE_KEY);

      if (!token) {
        opts.onAuthFailure?.("missing token in callback");
        return;
      }
      if (!state || !expectedState || state !== expectedState) {
        opts.onAuthFailure?.("CSRF state mismatch");
        return;
      }
      sessionStorage.removeItem(STATE_STORAGE_KEY);

      try {
        await apiPost<{ ok: true }>("/api/auth/desktop-exchange", { token });
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

function _resolveWebAuthBase(): string {
  // In a packaged build, VITE_DESKTOP_AUTH_URL is baked in (e.g.
  // https://digi-setu.com). In dev, point at the same origin as the
  // sidecar so we don't need an internet round-trip to test the
  // bounce flow against a /desktop/sign-in stub the developer can
  // wire up locally.
  const env = (import.meta as { env?: Record<string, string> }).env;
  const fromEnv = env?.VITE_DESKTOP_AUTH_URL;
  if (fromEnv) return fromEnv.replace(/\/+$/, "");
  const apiBase = getApiBase();
  if (apiBase) return apiBase;
  return window.location.origin;
}
