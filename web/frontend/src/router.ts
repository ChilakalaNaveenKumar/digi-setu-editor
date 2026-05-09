/**
 * Vue Router setup.
 *
 * Routes (history mode so the URL shows real paths, not `#`-hashes):
 *
 *   /                  Home — picker (flat list of recent chats).
 *   /sessions          Alias for / — Clerk's hosted sign-in redirects here
 *                      after auth (configured in the Clerk dashboard).
 *   /chat/:sid         Active chat session (the IDE shell). Tabs in the
 *                      chat sidebar switch between chats inside the
 *                      currently-open workspace.
 *   /login             Clerk <SignIn /> mount point
 *   /pricing           Public plans page (sign-in required to upgrade)
 *   /privacy           Static privacy policy (/privacy-policy is also routed
 *                      here because Clerk's "legal documents" URL field
 *                      points there).
 *   /terms             Static terms / output ownership
 *
 * `/chat/:sid` is the only persistable URL inside the app — bookmark it
 * and it'll resolve the workspace from the session id at boot via the
 * session's wsid.
 *
 * Auth guard:
 *   - In dev mode (`auth_required=false`) every route is open and the
 *     guard short-circuits.
 *   - In prod mode the guard waits for Clerk to load, then bounces
 *     unauthenticated users to /login (carrying a `next` param so we
 *     can return them to the original URL after sign-in).
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

import { useConfigStore } from "./stores/config";

// Routes that bypass the Clerk auth guard. The picker (both "/" and
// the "/sessions" alias) stays public because:
//
//   1. Clerk's hosted sign-in redirects here right after sign-in, but
//      the auth cookie hasn't necessarily been written by the time
//      the guard runs (race window during the OAuth round-trip). If
//      the guard 401-bounces in that window we end up in a redirect
//      loop: / → /login → Clerk → / → /login → ...
//   2. The picker UI itself works gracefully whether signed in or
//      not — the BrandHeader's <ClerkShow :when="'signed-out'"> /
//      <ClerkShow :when="'signed-in'"> pair handles the auth state
//      without help from the router.
//
// Anything that genuinely requires a signed-in user (chat, billing
// portal, etc.) gates itself at the API layer or via per-component
// guards, not here.
const PUBLIC_ROUTES = new Set([
  "picker",
  "login",
  "sessions",
  "privacy",
  "terms",
  "pricing",
  "feedback",
  "download",
  // Desktop sign-in bounce page: the Tauri shell pops the user's
  // default browser at https://digi-setu.com/desktop/sign-in. The
  // page mints a Clerk session for the signed-in user and redirects
  // to a digi-setu:// deep link. Must stay public — being signed in
  // is the *expected* case (we mint a handoff for the existing
  // session) but the route still needs to load before Clerk has
  // finished hydrating, which the global guard would otherwise
  // bounce away from.
  "desktop-sign-in",
]);

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "picker",
    component: () => import("./views/Picker.vue"),
  },
  {
    // Clerk's Account Portal sends users to /sessions after sign-in /
    // sign-up (see dashboard → User redirects). Alias to the picker
    // so we don't have to maintain a separate component.
    path: "/sessions",
    name: "sessions",
    component: () => import("./views/Picker.vue"),
  },
  {
    path: "/chat/:sid",
    name: "chat",
    component: () => import("./views/Workspace.vue"),
    props: true,
  },
  {
    path: "/login",
    name: "login",
    component: () => import("./views/Login.vue"),
  },
  {
    // Desktop sign-in bounce page. The Tauri shell opens this URL in
    // the user's default browser; after Clerk authenticates, the page
    // mints a fresh Clerk session via /api/auth/desktop-mint-handoff
    // and redirects to the digi-setu:// deep link the desktop client
    // supplied via `?return=…`. The desktop sidecar then exchanges
    // the session_id for a JWT via /api/auth/desktop-refresh, and
    // the frontend stashes the session_id in the OS keychain so the
    // user stays signed in across app restarts (Cursor-style SSO).
    path: "/desktop/sign-in",
    name: "desktop-sign-in",
    component: () => import("./views/DesktopSignIn.vue"),
  },
  {
    path: "/pricing",
    name: "pricing",
    component: () => import("./views/Pricing.vue"),
  },
  {
    path: "/privacy",
    name: "privacy",
    component: () => import("./views/Privacy.vue"),
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
  },
  {
    path: "/feedback",
    name: "feedback",
    component: () => import("./views/Feedback.vue"),
  },
  {
    path: "/activity",
    name: "activity",
    component: () => import("./views/Activity.vue"),
  },
  {
    // Public landing for the desktop installer download. Linked from
    // BrandHeader and the picker's empty state. Static-ish page; the
    // .dmg itself is served by Caddy directly out of /srv/pi/downloads.
    path: "/download",
    name: "download",
    component: () => import("./views/Download.vue"),
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

router.beforeEach(async (to) => {
  const cfg = useConfigStore();
  // Defensive: if main.ts somehow navigates before refresh, do it now.
  if (!cfg.ready) await cfg.refresh();

  if (!cfg.authRequired) {
    // /login is meaningless in dev mode (no Clerk to render). Bounce
    // to home so nobody trips the dead "auth disabled" notice.
    if (to.name === "login") return { path: "/" };
    return true;
  }
  if (PUBLIC_ROUTES.has(String(to.name))) return true;

  // Why not `useAuth()` here: composables rely on Vue's `inject()`
  // and only resolve inside a component setup function. Router
  // guards run outside that context, so we use the plugin-free
  // `getToken()` helper from @clerk/shared. It internally waits for
  // Clerk to finish loading and returns null iff there's no session
  // — exactly the boolean we need.
  const { getToken } = await import("@clerk/vue");
  let token: string | null = null;
  try {
    token = await getToken();
  } catch (exc) {
    console.warn("[router] getToken failed in guard", exc);
  }

  if (token) return true;
  return { name: "login", query: { next: to.fullPath } };
});
