/**
 * Editor preferences — persisted in localStorage, shared across the app.
 *
 * Currently houses just the auto-save settings, but the shape (`prefs`
 * object + `setX(value)` mutators) is set up so additional editor knobs
 * (font size, tab size, render whitespace, etc.) drop in without
 * reshuffling consumers.
 *
 * Why localStorage and not the backend `user_prefs.py` blob?
 *   - Editor prefs are per-device per-user. Different machine ≠ same
 *     keyboard, different DPI ≠ same font size. Keeping them client-only
 *     matches every IDE on the planet (VS Code, JetBrains, Sublime).
 *   - Avoids a network round-trip to read on app boot.
 *   - Persists offline, doesn't break dev with no auth.
 *
 * If we ever want a server-synced "workspace settings" layer, that lives
 * separately (a `workspace.json` in `.digi-setu/` that overrides these).
 */

import { defineStore } from "pinia";
import { ref, watch } from "vue";

/** "off" — manual Cmd/S only (default; matches most code editors).
 *  "afterDelay" — auto-save 1s after typing stops, like VS Code default.
 *  "onBlur" — save when the editor loses focus (clicked another file /
 *   tab / outside). Closer to JetBrains' "save on focus change". */
export type AutoSaveMode = "off" | "afterDelay" | "onBlur";

const STORAGE_KEY = "digi-setu/editor-prefs/v1";

interface EditorPrefsBlob {
  autoSave: AutoSaveMode;
  /** Debounce in ms used when `autoSave === "afterDelay"`. 1000 matches
   *  the VS Code default; we expose it because some users find 1s
   *  jarring on slow networks (each save rebuilds shadow snapshots). */
  autoSaveDelayMs: number;
}

const DEFAULTS: EditorPrefsBlob = {
  autoSave: "off",
  autoSaveDelayMs: 1000,
};

function load(): EditorPrefsBlob {
  if (typeof window === "undefined") return { ...DEFAULTS };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULTS };
    const parsed = JSON.parse(raw) as Partial<EditorPrefsBlob>;
    const mode: AutoSaveMode =
      parsed.autoSave === "afterDelay" || parsed.autoSave === "onBlur"
        ? parsed.autoSave
        : "off";
    const delay =
      typeof parsed.autoSaveDelayMs === "number" && parsed.autoSaveDelayMs >= 200
        ? Math.min(parsed.autoSaveDelayMs, 30_000)
        : DEFAULTS.autoSaveDelayMs;
    return { autoSave: mode, autoSaveDelayMs: delay };
  } catch {
    return { ...DEFAULTS };
  }
}

function persist(blob: EditorPrefsBlob): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(blob));
  } catch {
    /* quota exceeded / Safari private mode — non-fatal */
  }
}

export const useEditorPrefsStore = defineStore("editor-prefs", () => {
  const initial = load();
  const autoSave = ref<AutoSaveMode>(initial.autoSave);
  const autoSaveDelayMs = ref<number>(initial.autoSaveDelayMs);

  // Auto-persist on any change so the UI doesn't have to remember to
  // call .save() — flat blob, no migrations to worry about.
  watch(
    [autoSave, autoSaveDelayMs],
    () =>
      persist({
        autoSave: autoSave.value,
        autoSaveDelayMs: autoSaveDelayMs.value,
      }),
    { deep: false },
  );

  function setAutoSave(mode: AutoSaveMode): void {
    autoSave.value = mode;
  }

  function setAutoSaveDelay(ms: number): void {
    autoSaveDelayMs.value = Math.max(200, Math.min(30_000, Math.floor(ms)));
  }

  return {
    autoSave,
    autoSaveDelayMs,
    setAutoSave,
    setAutoSaveDelay,
  };
});
