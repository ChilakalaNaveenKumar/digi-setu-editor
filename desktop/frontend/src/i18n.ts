/**
 * vue-i18n setup.
 *
 * One locale shipped (`en`). Adding another language later is:
 *   1. cp src/locales/en.json src/locales/<lang>.json
 *   2. translate the values
 *   3. import here, register under `messages`
 *   4. expose a UI affordance (settings menu) to set i18n.global.locale
 *
 * Convention for keys: short UI fragments (buttons, labels, mode
 * names) live in en.json; long-form prose (Privacy / Terms full
 * paragraphs) stays inline in the .vue templates — those are rare
 * full-clone targets when a translation lands.
 *
 * `legacy: false` selects the Composition API mode (the modern,
 * recommended path; required for `useI18n()` in setup blocks).
 *
 * `silentTranslationWarn` + `silentFallbackWarn` are off so missing
 * keys print loudly during development. We DO want to know when a
 * component asks for a key that doesn't exist.
 */

import { createI18n } from "vue-i18n";

import en from "./locales/en.json";

export type SupportedLocale = "en";

export const SUPPORTED_LOCALES: readonly SupportedLocale[] = ["en"] as const;

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: "en" as SupportedLocale,
  fallbackLocale: "en" as SupportedLocale,
  messages: { en },
  // Numbers (token counts, prices) come pre-formatted from the
  // backend so we don't define numberFormats. If we ever start
  // formatting in-component, register them here.
});

/** Switch the active locale. Persists to localStorage so the choice
 *  survives reloads. Returns the locale that was actually applied (may
 *  fall back to "en" if the user passes something unsupported). */
export function setLocale(value: string): SupportedLocale {
  const normalised: SupportedLocale = (SUPPORTED_LOCALES as readonly string[]).includes(value)
    ? (value as SupportedLocale)
    : "en";
  i18n.global.locale.value = normalised;
  try {
    localStorage.setItem("digi-setu:locale", normalised);
  } catch {
    /* ignore storage errors (private mode, etc.) */
  }
  return normalised;
}

/** Read whatever locale we last persisted and apply it. Called once
 *  during boot before the app mounts so the UI never flashes English
 *  for a tick before switching. */
export function bootLocale(): void {
  try {
    const stored = localStorage.getItem("digi-setu:locale");
    if (stored && (SUPPORTED_LOCALES as readonly string[]).includes(stored)) {
      i18n.global.locale.value = stored as SupportedLocale;
    }
  } catch {
    /* ignore */
  }
}

// ── HMR for locale JSON ─────────────────────────────────────────────
// Vite hot-replaces `./locales/en.json` when it changes, but vue-i18n
// keeps a snapshot of the messages object from the moment it was
// constructed. Without explicit HMR plumbing, edits to en.json look
// like they didn't apply (the UI still shows raw key names like
// `chat.error.generic`) until you cold-reload the window.
//
// The accept-callback below grabs the fresh JSON and re-installs it
// via setLocaleMessage. Production builds tree-shake `import.meta.hot`
// out so this costs nothing in shipped bundles.
// `import.meta.hot` only exists in Vite dev. The Vite types don't ship
// it on the global ImportMeta interface (it's a Vite-specific augment
// that requires `vite/client` in the tsconfig), and we don't want to
// pull that whole namespace in just for one optional dev hook. Cast
// through `any` here to keep the production type-check (`vue-tsc
// --noEmit`) clean while still no-op'ing the block in builds.
const _meta = import.meta as unknown as {
  hot?: {
    accept: (
      dep: string,
      cb: (mod: { default?: Record<string, unknown> } | undefined) => void,
    ) => void;
  };
};
if (_meta.hot) {
  _meta.hot.accept("./locales/en.json", (mod) => {
    const fresh = mod?.default;
    if (fresh) {
      i18n.global.setLocaleMessage("en", fresh as never);
    }
  });
}
