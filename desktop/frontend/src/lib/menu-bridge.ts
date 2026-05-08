/**
 * Bridge between the native menu bar (built in src-tauri/src/menu.rs)
 * and the Vue SPA. The Rust side fires Tauri events with stable
 * `menu:*` ids; this module subscribes once at boot and translates
 * them into router pushes / Pinia store calls.
 *
 * Adding a new menu item:
 *   1. Pick a stable id in src-tauri/src/menu.rs::ids and emit it from
 *      lib.rs::handle_menu_event via `emit_to_active("menu:<id>")`.
 *   2. Wire it here in `routeMenuEvent`. Keep the matchers small —
 *      the bridge is glue, not business logic.
 *   3. Frontend stays SSR-safe: the dynamic import means web builds
 *      never load `@tauri-apps/api/event` and never see the listener.
 *
 * Web mode: `installMenuBridge()` is a no-op so importing this file
 * unconditionally from main.ts is fine.
 */

import type { Router } from "vue-router";
import { isDesktop } from "./native-bridge";
import { useChatSessionStore } from "../stores/chat-session";
import { useWorkspaceStore } from "../stores/workspace";
import { useUiStore } from "../stores/ui";

type Unlisten = () => void;

/** All menu events we emit from Rust. Keep in sync with menu::ids. */
const MENU_EVENTS = [
  "menu:open_folder",
  "menu:close_folder",
  "menu:new_chat",
  "menu:find_in_chat",
  "menu:focus_chat",
  "menu:zoom_in",
  "menu:zoom_out",
  "menu:zoom_reset",
] as const;
type MenuEventName = (typeof MENU_EVENTS)[number];

// ── Zoom ────────────────────────────────────────────────────────────
// Minimum / maximum kept conservative — going below 70 % makes the chat
// composer touch-target unusable; above 200 % the message bubbles wrap
// awkwardly on a 13" screen. These match VS Code's zoom clamps.
const ZOOM_MIN = 0.7;
const ZOOM_MAX = 2.0;
const ZOOM_STEP = 0.1;

function getZoom(): number {
  // We persist zoom on `documentElement.style.zoom` — non-standard but
  // honoured by both WKWebView (macOS) and WebView2 (Windows). Falls
  // back to 1.0 when unset.
  const raw = document.documentElement.style.zoom;
  const parsed = raw ? Number(raw) : 1.0;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1.0;
}

function setZoom(next: number): void {
  const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, next));
  // Round to 2 decimals so 1.0 + 0.1 + 0.1 + 0.1 doesn't drift to
  // 1.3000000000000003 in the inspector.
  document.documentElement.style.zoom = String(Math.round(clamped * 100) / 100);
}

// ── Frontend custom events ──────────────────────────────────────────
// Components (Composer, MessageList, …) listen for these instead of
// importing this module — keeps the menu wiring decoupled from the
// chat UI. Emitted as window CustomEvents so Vue components can attach
// either via `@finder` template syntax or addEventListener in onMounted.
function dispatch(name: "menu-find-in-chat" | "menu-focus-chat"): void {
  window.dispatchEvent(new CustomEvent(name));
}

// ── Event router ────────────────────────────────────────────────────
async function routeMenuEvent(name: MenuEventName, router: Router): Promise<void> {
  switch (name) {
    case "menu:open_folder": {
      // Defer the actual folder-pick to the Picker view. Routing there
      // first means the user always sees the picker UI light up — even
      // if they were deep inside a chat — instead of a hidden file
      // dialog popping over their workspace.
      await router.push({ name: "picker" });
      // Use a microtask to let the route render before triggering the
      // picker's openDesktopFolder handler. The Picker view exposes
      // it as a window-level event so we don't have to plumb refs.
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent("menu-open-folder"));
      }, 0);
      return;
    }
    case "menu:close_folder": {
      const ws = useWorkspaceStore();
      ws.setActive(null);
      await router.push({ name: "picker" });
      return;
    }
    case "menu:new_chat": {
      const ws = useWorkspaceStore();
      const wsid = ws.activeId;
      if (!wsid) {
        useUiStore().toast({
          message: "Open a folder first to start a new chat",
          kind: "info",
        });
        return;
      }
      try {
        const chatStore = useChatSessionStore();
        const fresh = await chatStore.create(wsid);
        await router.push({
          name: "chat",
          params: { sid: fresh.id },
          query: { wsid },
        });
      } catch (exc) {
        useUiStore().toastError("Could not create chat", exc);
      }
      return;
    }
    case "menu:find_in_chat":
      dispatch("menu-find-in-chat");
      return;
    case "menu:focus_chat":
      dispatch("menu-focus-chat");
      return;
    case "menu:zoom_in":
      setZoom(getZoom() + ZOOM_STEP);
      return;
    case "menu:zoom_out":
      setZoom(getZoom() - ZOOM_STEP);
      return;
    case "menu:zoom_reset":
      setZoom(1.0);
      return;
    default: {
      // Exhaustiveness — if a new event id slips into MENU_EVENTS
      // without a matcher this won't compile.
      const _exhaustive: never = name;
      void _exhaustive;
    }
  }
}

/**
 * Subscribe to every `menu:*` event the Rust side emits. Returns a
 * teardown callback (mostly useful in tests; in prod the listener
 * lives for the app lifetime).
 *
 * In web mode this resolves to a no-op immediately so calling it
 * unconditionally is safe.
 */
export async function installMenuBridge(router: Router): Promise<Unlisten> {
  if (!isDesktop()) return () => {};

  const { listen } = await import("@tauri-apps/api/event");
  const unlisteners: Unlisten[] = [];

  for (const name of MENU_EVENTS) {
    const off = await listen(name, () => {
      void routeMenuEvent(name, router).catch((exc) => {
        console.error(`[menu-bridge] handler ${name} threw:`, exc);
      });
    });
    unlisteners.push(off);
  }

  return () => {
    for (const off of unlisteners) off();
  };
}
