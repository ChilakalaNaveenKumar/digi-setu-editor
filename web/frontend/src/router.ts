/**
 * Vue Router setup.
 *
 * Routes (history mode so the URL shows real paths, not `#`-hashes):
 *
 *   /                  Home — public marketing landing.
 *   /sessions          Picker — flat list of recent chats. First
 *                      authenticated surface; Clerk's hosted sign-in
 *                      also redirects here post-auth.
 *   /chat/:sid         Active chat session (the IDE shell).
 *   /login             Clerk <SignIn /> handoff page.
 *   /pricing           Public plans page (sign-in required to upgrade)
 *   /privacy           Static privacy policy (/privacy-policy is also
 *                      routed here because Clerk's "legal documents"
 *                      URL field points there).
 *   /terms             Static terms / output ownership
 *   /acknowledgements  Open-source third-party notices (in-app render
 *                      of THIRD_PARTY_NOTICES.md). Public, no auth.
 *
 * `/chat/:sid` is the only persistable URL inside the app — bookmark
 * it and it'll resolve the workspace from the session id at boot.
 *
 * Route meta:
 *   - `header: 'full' | 'compact' | 'none'` — controls the global
 *     BrandHeader mounted in App.vue. The IDE shell (/chat/:sid) uses
 *     the compact variant so the chat title fits in the centre slot;
 *     marketing routes use full.
 *   - `footer: boolean` — render the shared <AppFooter /> below the
 *     route. The chat IDE has its own bottom bar so it sets false.
 *
 * Auth guard:
 *   - In dev mode (`auth_required=false`) every route is open and the
 *     guard short-circuits. /login is meaningless without Clerk so we
 *     bounce it to /.
 *   - In prod mode the guard waits for Clerk to load. PUBLIC_ROUTES
 *     stay open; everything else bounces unauthenticated users to
 *     /login (carrying a `next` param so we can return them to the
 *     original URL after sign-in). The Home page (/) is public so a
 *     brand-new visitor lands on the marketing surface, not a Clerk
 *     redirect — they sign in by clicking the hero CTA.
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

import { useConfigStore } from "./stores/config";

// Routes that bypass the Clerk auth guard. Home / Picker / Start stay
// public because:
//
//   1. Clerk's hosted sign-in redirects to /start (or /sessions) right
//      after sign-in, but the auth cookie hasn't necessarily been
//      written by the time the guard runs (race window during the
//      OAuth round-trip). If the guard 401-bounces in that window we
//      end up in a redirect loop: /start → /login → Clerk → /start →
//      /login → … Letting the destination view itself read auth state
//      avoids the loop entirely; the underlying API calls /start makes
//      will 401 if the cookie is genuinely missing, surfacing a clean
//      error rather than ping-ponging the user.
//   2. The Home page itself is the marketing landing — it MUST be
//      reachable without auth or new visitors hit a sign-in wall
//      with no context.
//   3. The picker UI works gracefully whether signed in or not —
//      the BrandHeader's <ClerkShow :when="'signed-out'"> /
//      <ClerkShow :when="'signed-in'"> pair handles the auth state
//      without help from the router.
//
// Anything that genuinely requires a signed-in user (chat, billing
// portal, etc.) gates itself at the API layer or via per-component
// guards, not here.
const PUBLIC_ROUTES = new Set([
  "home",
  "login",
  "sessions",
  "start",
  "privacy",
  "terms",
  "acknowledgements",
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
    name: "home",
    component: () => import("./views/Home.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // Picker — the workspace/chat list. Reachable manually from the
    // header link or as the post-sign-in surface for users who don't
    // want auto-resolution.
    path: "/sessions",
    name: "sessions",
    component: () => import("./views/Picker.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // Auto-router: opens the user's most recent chat (or mints one
    // for brand-new accounts) and replaces itself with /chat/<sid>.
    // This is the post-sign-in landing page so users skip the picker
    // step entirely on the common path. See views/Start.vue for the
    // resolution rules and fallback behaviour.
    path: "/start",
    name: "start",
    component: () => import("./views/Start.vue"),
    meta: { header: "compact", footer: false },
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
    // Desktop sign-in bounce page. The Tauri shell opens this URL in
    // the user's default browser; after Clerk authenticates, the page
    // mints a fresh Clerk session via /api/auth/desktop-mint-handoff
    // and redirects to the digi-setu:// deep link the desktop client
    // supplied via `?return=…`.
    path: "/desktop/sign-in",
    name: "desktop-sign-in",
    component: () => import("./views/DesktopSignIn.vue"),
    meta: { header: "full", footer: false },
  },
  {
    path: "/pricing",
    name: "pricing",
    component: () => import("./views/Pricing.vue"),
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
    // clause we ship under (MIT, Apache 2.0, OFL, LGPL).
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
    path: "/activity",
    name: "activity",
    component: () => import("./views/Activity.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // Public landing for the desktop installer download. Linked from
    // BrandHeader and the picker's empty state. Static-ish page; the
    // .dmg itself is served by Caddy directly out of /srv/pi/downloads.
    path: "/download",
    name: "download",
    component: () => import("./views/Download.vue"),
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
