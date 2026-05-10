/**
 * Chat-session catalogue (one workspace contains many chat sessions).
 *
 * "Active session" is independent of the chat WS lifecycle — it's the id
 * the URL is currently focused on, and the chat store owns the WS for
 * that id.
 */

import { defineStore } from "pinia";
import { computed, ref } from "vue";

import * as api from "../api/sessions";
import type { SessionRecord } from "../api/types";

import { useChatStore } from "./chat";
import { useUiStore } from "./ui";
import { useWorkspaceStore } from "./workspace";

export const useChatSessionStore = defineStore("chat-session", () => {
  const ui = useUiStore();
  const workspace = useWorkspaceStore();

  const sessions = ref<SessionRecord[]>([]);
  const activeId = ref<string | null>(null);

  const active = computed<SessionRecord | null>(() =>
    activeId.value ? sessions.value.find((s) => s.id === activeId.value) ?? null : null
  );

  async function refresh(wsid: string): Promise<void> {
    try {
      const data = await api.listSessions(wsid);
      sessions.value = data.sessions;
    } catch (exc) {
      ui.toastError("Failed to list sessions", exc);
    }
  }

  async function create(wsid: string, title = ""): Promise<SessionRecord> {
    const sess = await api.createSession(wsid, title);
    sessions.value = [sess, ...sessions.value];
    return sess;
  }

  async function rename(sid: string, title: string): Promise<SessionRecord> {
    const sess = await api.renameSession(sid, title);
    sessions.value = sessions.value.map((s) => (s.id === sess.id ? sess : s));
    return sess;
  }

  /**
   * Apply a title update that originated server-side (e.g. the
   * background LLM titler in chat_ws). We just patch the local cache;
   * no API call needed because the registry already has the new
   * title. If the session isn't in our cached list (different
   * workspace, never loaded, …) this is a no-op — the next refresh
   * will pick it up.
   */
  function applyTitleUpdate(sid: string, title: string): void {
    const clean = title.trim();
    if (!clean) return;
    sessions.value = sessions.value.map((s) =>
      s.id === sid ? { ...s, title: clean } : s,
    );
  }

  async function remove(sid: string): Promise<void> {
    await api.deleteSession(sid);
    // Release any parked WS bridge for this chat. Without this the
    // multi-bridge tab cache (chat store) keeps the deleted session's
    // WebSocket alive — heartbeating, auto-reconnecting, and pinning a
    // pi process on the backend until the workspace is closed.
    try {
      useChatStore().closeSession(sid);
    } catch {
      /* chat store not initialised yet — nothing parked */
    }
    sessions.value = sessions.value.filter((s) => s.id !== sid);
    if (activeId.value === sid) activeId.value = null;
  }

  function setActive(sid: string | null): void {
    activeId.value = sid;
  }

  /**
   * Web shortcut: spin up a workspace + a session inside it in one shot.
   * The desktop flow uses two steps (pick folder, then create session).
   */
  async function createWebPair(): Promise<{ workspace: { id: string }; session: SessionRecord }> {
    const ws = await workspace.create();
    const sess = await create(ws.id);
    return { workspace: ws, session: sess };
  }

  return {
    sessions,
    activeId,
    active,
    refresh,
    create,
    rename,
    applyTitleUpdate,
    remove,
    setActive,
    createWebPair,
  };
});
