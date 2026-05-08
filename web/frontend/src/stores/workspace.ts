/**
 * Workspaces catalogue + active workspace tracking.
 *
 * The active wsid is the one the chat WebSocket is currently bound to.
 * It's set by the router (URL → activeId) when a session is opened, and
 * cleared on disconnect.
 */

import { defineStore } from "pinia";
import { computed, ref } from "vue";

import * as api from "../api/workspaces";
import { rawFileUrl as buildRawUrl } from "../api/files";
import type { WorkspaceRecord } from "../api/types";

import { useUiStore } from "./ui";

export const useWorkspaceStore = defineStore("workspace", () => {
  const ui = useUiStore();

  const workspaces = ref<WorkspaceRecord[]>([]);
  const activeId = ref<string | null>(null);

  const active = computed<WorkspaceRecord | null>(() =>
    activeId.value ? workspaces.value.find((w) => w.id === activeId.value) ?? null : null
  );

  async function refresh(): Promise<void> {
    try {
      const data = await api.listWorkspaces();
      workspaces.value = data.workspaces;
    } catch (exc) {
      ui.toastError("Failed to list workspaces", exc);
    }
  }

  async function create(opts: { name?: string; path?: string } = {}): Promise<WorkspaceRecord> {
    const ws = await api.createWorkspace(opts);
    workspaces.value = [ws, ...workspaces.value.filter((w) => w.id !== ws.id)];
    return ws;
  }

  async function rename(wsid: string, name: string): Promise<WorkspaceRecord> {
    const ws = await api.renameWorkspace(wsid, name);
    workspaces.value = workspaces.value.map((w) => (w.id === ws.id ? ws : w));
    return ws;
  }

  async function remove(wsid: string): Promise<void> {
    await api.deleteWorkspace(wsid);
    workspaces.value = workspaces.value.filter((w) => w.id !== wsid);
    if (activeId.value === wsid) activeId.value = null;
  }

  function setActive(wsid: string | null): void {
    activeId.value = wsid;
  }

  /**
   * Build a URL the <img>/<video>/<embed> tags can hit directly. Throws
   * if no workspace is active — every caller path is gated behind the
   * Workspace view, which only renders when active is set.
   */
  function rawFileUrl(path: string): string {
    if (!activeId.value) throw new Error("no active workspace");
    return buildRawUrl(activeId.value, path);
  }

  return {
    workspaces,
    activeId,
    active,
    refresh,
    create,
    rename,
    remove,
    setActive,
    rawFileUrl,
  };
});
