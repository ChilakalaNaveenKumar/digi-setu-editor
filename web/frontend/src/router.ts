/**
 * Vue Router setup.
 *
 * Routes (history mode so the URL shows real paths, not `#`-hashes):
 *
 *   /                  Home — picker (web flat list, or desktop workspace list)
 *   /sessions          Alias for / — Clerk's hosted sign-in redirects here
 *                      after auth (configured in the Clerk dashboard).
 *   /workspaces/:wsid  Desktop drilled into one workspace's chat list
 *   /chat/:sid         Active chat session (the IDE shell)
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

// Routes that bypass the Clerk auth guard. `sessions` stays public
// because Clerk lands here right after sign-in and the auth cookie
// hasn't necessarily been written by the time the guard runs (race
// window during the OAuth round trip). The picker itself works
// gracefully whether the user is signed in or not.
const PUBLIC_ROUTES = new Set([
  "login",
  "sessions",
  "privacy",
  "terms",
  "pricing",
  "feedback",
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
    path: "/workspaces/:wsid",
    name: "workspace",
    component: () => import("./views/PickerDesktopDrill.vue"),
    props: true,
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
