/**
 * Vue Router setup.
 *
 * Routes (history mode so the URL shows real paths, not `#`-hashes):
 *
 *   /                  Picker — workspace / session list. Desktop
 *                      doesn't ship a separate "marketing home"
 *                      surface; the picker IS the home page because
 *                      the user has already installed the app and
 *                      isn't being sold to. The web fork serves the
 *                      marketing landing — see web/frontend/router.ts.
 *   /sessions          Alias for / — Clerk's hosted sign-in redirects
 *                      here after auth (configured in the Clerk
 *                      dashboard).
 *   /workspaces/:wsid  Desktop landing — resolves to the most-recent
 *                      chat in the workspace (or auto-creates one), then
 *                      redirects to /chat/:sid. Kept for bookmark stability;
 *                      not part of the primary navigation flow.
 *   /chat/:sid         Active chat session (the IDE shell). Tabs in the
 *                      chat sidebar switch between chats inside the
 *                      currently-open workspace.
 *   /login             Clerk <SignIn /> mount point
 *   /pricing           Public plans page (sign-in required to upgrade)
 *   /privacy           Static privacy policy (/privacy-policy is also routed
 *                      here because Clerk's "legal documents" URL field
 *                      points there).
 *   /terms             Static terms / output ownership
 *   /acknowledgements  Open-source third-party notices (in-app render
 *                      of THIRD_PARTY_NOTICES.md). Public, no auth.
 *
 * `/chat/:sid` is the only persistable URL inside the app — bookmark it
 * and it'll resolve the workspace from the session id at boot via the
 * session's wsid.
 *
 * Route meta:
 *   - `header: 'full' | 'compact' | 'none'` — controls the global
 *     BrandHeader mounted in App.vue. The IDE shell (/chat/:sid) uses
 *     the compact variant so the chat title fits in the centre slot;
 *     the marketing routes use full; nothing currently sets 'none'
 *     but it's there for future fullscreen flows.
 *   - `footer: boolean` — render the shared <AppFooter /> below the
 *     route. The chat IDE has its own bottom bar so it sets false.
 *
 * Auth guard:
 *   - The guard does NOT block navigation based on auth state. Users
 *     can browse the picker, open folders, view workspaces, and read
 *     legal pages without signing in. The actual gate lives in the
 *     chat surface: when a user tries to send a message without a
 *     usable backend (no Clerk session AND no BYOK key), the chat
 *     panel renders an inline "sign in or add a key" prompt instead
 *     of trying to spawn the runtime and crashing the bridge.
 *   - On true first launch (`requires_setup=true` AND nothing in the
 *     URL bar — the user just opened the app), we land them on
 *     /login (the Welcome screen) as a friendly default. They can
 *     navigate away from there to / freely; we never bounce them
 *     back.
 *   - /login is auto-redirected to / once auth is satisfied so the
 *     dead "auth disabled" / "you're already signed in" stub never
 *     shows.
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

import { useConfigStore } from "./stores/config";
import { useAuthStore } from "./stores/auth";

// Routes that bypass the cold-launch /login bounce. `sessions` stays
// public because Clerk lands here right after sign-in and the auth
// cookie hasn't necessarily been written by the time the guard runs.
const PUBLIC_ROUTES = new Set([
  "login",
  "sessions",
  "privacy",
  "terms",
  "acknowledgements",
  "pricing",
  "feedback",
]);

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "picker",
    component: () => import("./views/Picker.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // Clerk's Account Portal sends users to /sessions after sign-in /
    // sign-up. Alias to the picker so we don't have to maintain a
    // separate component.
    path: "/sessions",
    name: "sessions",
    component: () => import("./views/Picker.vue"),
    meta: { header: "full", footer: true },
  },
  {
    path: "/workspaces/:wsid",
    name: "workspace",
    component: () => import("./views/PickerDesktopDrill.vue"),
    props: true,
    meta: { header: "full", footer: true },
  },
  {
    path: "/chat/:sid",
    name: "chat",
    component: () => import("./views/Workspace.vue"),
    props: true,
    meta: { header: "compact", footer: false },
  },
  {
    path: "/login",
    name: "login",
    component: () => import("./views/Login.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // /pricing — kept as a route so old in-app links and the chat
    // surface's "Upgrade" CTA don't 404, but the page itself now
    // renders an "Opening browser…" stub and immediately calls
    // openExternal({CLOUD}/pricing). Billing UX lives on the cloud
    // SPA where Stripe Checkout / Customer Portal already runs in
    // the user's signed-in browser session — we don't want a parallel
    // billing surface inside the desktop binary that could go stale,
    // mis-classify states, or leak Stripe keys.
    path: "/pricing",
    name: "pricing",
    component: () => import("./views/CloudRedirect.vue"),
    props: { target: "PRICING", title: "Pricing" },
    meta: { header: "full", footer: true },
  },
  {
    path: "/privacy",
    name: "privacy",
    component: () => import("./views/Privacy.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // Clerk's "Privacy Policy URL" field points to /privacy-policy
    // (see dashboard → Customization → Legal). Alias to the same view.
    path: "/privacy-policy",
    redirect: "/privacy",
  },
  {
    path: "/terms",
    name: "terms",
    component: () => import("./views/Terms.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // Open-source acknowledgements / third-party notices. Renders the
    // same content as THIRD_PARTY_NOTICES.md at the repo root and is
    // the legal-attribution surface required by every redistribution
    // clause we ship under (MIT, Apache 2.0, OFL, LGPL — note CeTZ
    // in particular).
    path: "/acknowledgements",
    name: "acknowledgements",
    component: () => import("./views/Acknowledgements.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // Common alternate spelling — keep both URLs alive.
    path: "/acknowledgments",
    redirect: "/acknowledgements",
  },
  {
    path: "/feedback",
    name: "feedback",
    component: () => import("./views/Feedback.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // /activity — same posture as /pricing. The cloud's CreditLedger
    // is the authoritative source of truth (every chat turn that ran
    // on the cloud relay writes a row there); a separate desktop page
    // would drift, leak the user's chat history into a local SQLite
    // (which they could delete), and force the desktop to make
    // authenticated reads against the cloud DB.
    path: "/activity",
    name: "activity",
    component: () => import("./views/CloudRedirect.vue"),
    props: { target: "ACTIVITY", title: "Activity" },
    meta: { header: "full", footer: true },
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/",
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

// True on the very first navigation of a session. Used so that on
// cold launch we can land a brand-new (no auth, no BYOK) user on the
// Welcome screen as a friendly default — but we never bounce them
// back to Welcome after that, even if they navigate away.
let firstNavigation = true;

router.beforeEach(async (to) => {
  const cfg = useConfigStore();
  const auth = useAuthStore();
  // Defensive: if main.ts somehow navigates before refresh, do it now.
  if (!cfg.ready) await cfg.refresh();
  if (!auth.ready) await auth.refresh();

  const wasFirst = firstNavigation;
  firstNavigation = false;

  // /login is the Welcome screen. If the user is already signed in
  // (or running in BYOK / dev mode), there's nothing useful for
  // /login to show — send them home. This also avoids the "you're
  // already signed in" dead-end stub.
  if (to.name === "login" && (auth.signedIn || !cfg.authRequired)) {
    return { path: "/" };
  }

  // Cold-launch friendly redirect: brand-new user (auth required, not
  // signed in, no BYOK) opening / for the first time → land them on
  // the Welcome screen. Only on the very first navigation; after that
  // they can roam freely between picker / pricing / privacy / etc.
  if (
    wasFirst &&
    to.path === "/" &&
    cfg.requiresSetup &&
    !PUBLIC_ROUTES.has(String(to.name))
  ) {
    return { name: "login" };
  }

  // Otherwise: every route is open. Chat itself prompts for sign-in
  // or BYOK at message-send time when no backend is configured;
  // navigation is never blocked.
  return true;
});
