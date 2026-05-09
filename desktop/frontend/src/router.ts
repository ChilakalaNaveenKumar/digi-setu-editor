/**
 * Vue Router setup.
 *
 * Routes (history mode so the URL shows real paths, not `#`-hashes):
 *
 *   /                  Home — public marketing landing
 *   /sessions          Picker — recent chats (web) or workspaces (desktop).
 *                      This is the first authenticated surface; Clerk's
 *                      hosted sign-in also redirects here post-auth.
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
 *     can browse the home page, picker, open folders, view workspaces,
 *     and read legal pages without signing in. The actual gate lives
 *     in the chat surface: when a user tries to send a message without
 *     a usable backend (no Clerk session AND no BYOK key), the chat
 *     panel renders an inline "sign in or add a key" prompt instead
 *     of trying to spawn the runtime and crashing the bridge.
 *   - On true first launch (`requires_setup=true`) we land the user on
 *     the public Home page (/), which carries its own primary CTA into
 *     /login. We do NOT bounce / → /login any more — the user always
 *     sees the marketing surface first so they know what they're
 *     signing in to.
 *   - /login is auto-redirected to /sessions once auth is satisfied so
 *     the dead "auth disabled" / "you're already signed in" stub never
 *     shows.
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

import { useConfigStore } from "./stores/config";
import { useAuthStore } from "./stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("./views/Home.vue"),
    meta: { header: "full", footer: true },
  },
  {
    // Picker is the first authenticated surface. Clerk's Account
    // Portal sends users to /sessions after sign-in / sign-up (see
    // dashboard → User redirects), so the route name is fixed.
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
    // authenticated reads against the cloud DB. Sending users to
    // {CLOUD}/activity keeps the data path: browser → Caddy → cloud
    // FastAPI → SQLite-on-VM. The desktop never reaches that DB.
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

router.beforeEach(async (to) => {
  const cfg = useConfigStore();
  const auth = useAuthStore();
  // Defensive: if main.ts somehow navigates before refresh, do it now.
  if (!cfg.ready) await cfg.refresh();
  if (!auth.ready) await auth.refresh();

  // /login is the Welcome screen. If the user is already signed in
  // (or running in BYOK / dev mode), there's nothing useful for
  // /login to show — send them straight to the picker. This also
  // avoids the "you're already signed in" dead-end stub.
  if (to.name === "login" && (auth.signedIn || !cfg.authRequired)) {
    return { name: "sessions" };
  }

  // Otherwise: every route is open. Cold-launch first-time users
  // land on / (the public Home page) and choose to sign in from
  // the hero CTA — we no longer punt them to /login behind their
  // back. Chat itself prompts for sign-in or BYOK at message-send
  // time when no backend is configured.
  return true;
});
