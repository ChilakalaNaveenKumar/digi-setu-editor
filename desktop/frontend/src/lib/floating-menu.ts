/**
 * Tiny floating-menu helper for popovers / dropdown menus that anchor
 * to a trigger button.
 *
 * What it does
 * ------------
 * Given a trigger element ref + the menu's natural width/height, it
 * returns a reactive style object that:
 *
 *   - Positions the menu *fixed* on the viewport so it can escape any
 *     ancestor with overflow:hidden (chat pane, file tree, tool card,
 *     editor pane, etc — all of which clip absolutely-positioned
 *     children).
 *   - Right-aligns the menu under the trigger, then horizontally
 *     clamps it inside the viewport with an 8 px gutter on each side.
 *   - Vertically flips up when there's not enough room below AND
 *     there's more room above. This is what stops "Copy command /
 *     Re-run / Open in Terminal" from disappearing off the bottom of
 *     the screen when a tool card is rendered near the bottom of the
 *     chat scroll. Exact same flip rule the existing
 *     ChatSettingsMenu / ModelPicker / PermissionModePicker pickers
 *     use, kept in sync so the whole UI feels consistent.
 *   - Caps `maxHeight` so a tall menu turns into a scrollable one
 *     instead of overflowing the viewport. Combined with the menu
 *     element's own `overflow-y-auto`, this guarantees every item is
 *     reachable on tiny windows.
 *
 * What it does NOT do
 * -------------------
 * - It does NOT teleport. The caller wraps the menu in
 *   `<Teleport to="body">` themselves — that keeps Teleport visible
 *   in the SFC where it lives so reviewers don't have to chase the
 *   render target through a composable.
 * - It does NOT manage open state. The caller owns the boolean ref
 *   that controls visibility, plus its click-outside / Escape
 *   handlers. We only compute geometry.
 * - It does NOT pre-render the menu to measure it. We accept a
 *   "desired" height/width up front and clamp around that. This is
 *   precise enough in practice (every dropdown in the app has a
 *   stable item count) and avoids the FOUC of a one-frame measurement
 *   pass.
 *
 * Usage
 * -----
 * ```vue
 * <script setup>
 * import { useFloatingMenu } from "../lib/floating-menu";
 * const open = ref(false);
 * const triggerRef = ref(null);
 * const { menuStyle, reposition } = useFloatingMenu(triggerRef, {
 *   width: 192,
 *   height: 160,
 * });
 * watch(open, async (v) => {
 *   if (v) { await nextTick(); reposition(); }
 * });
 * </script>
 * <template>
 *   <button ref="triggerRef" @click="open = !open">⋯</button>
 *   <Teleport to="body">
 *     <div v-if="open" :style="menuStyle"
 *          class="fixed z-50 max-h-[calc(100vh-16px)] overflow-y-auto …">
 *       …
 *     </div>
 *   </Teleport>
 * </template>
 * ```
 */

import { onMounted, onUnmounted, ref, type Ref } from "vue";

export interface FloatingMenuOptions {
  /** Natural width of the menu, in pixels. Used for horizontal
   *  clamping. */
  width: number;
  /** Natural height of the menu (estimate is fine). Used for the
   *  flip-up decision and as a maxHeight cap. */
  height: number;
  /** Viewport gutter — minimum gap from the menu edge to the screen
   *  edge. 8 px matches the rest of the app and the Tailwind 2-step. */
  margin?: number;
  /** Pixels of breathing room between the trigger and the menu when
   *  it opens below or above. */
  gap?: number;
  /** "right" (default): align the menu's right edge with the trigger's
   *  right edge — natural for "⋯" buttons and gear icons.
   *  "left": align left edges — natural for Open / Save dropdowns
   *  whose trigger sits on the left of a toolbar. */
  align?: "left" | "right";
}

export interface FloatingMenuHandle {
  /** Style object to bind to the popover element. Reactive. */
  menuStyle: Ref<Record<string, string>>;
  /** Call after toggling visibility, on resize, on scroll, etc. */
  reposition: () => void;
}

export function useFloatingMenu(
  triggerRef: Ref<HTMLElement | null>,
  opts: FloatingMenuOptions,
): FloatingMenuHandle {
  const margin = opts.margin ?? 8;
  const gap = opts.gap ?? 4;
  const align = opts.align ?? "right";

  const menuStyle = ref<Record<string, string>>({
    // Start hidden off-screen so the first paint after `open=true`
    // doesn't flash at (0,0) before our reposition() runs.
    position: "fixed",
    top: "-9999px",
    left: "-9999px",
    width: `${opts.width}px`,
  });

  function reposition(): void {
    const t = triggerRef.value;
    if (!t) return;
    const rect = t.getBoundingClientRect();
    const width = Math.min(opts.width, window.innerWidth - margin * 2);

    let left: number;
    if (align === "right") {
      left = rect.right - width;
    } else {
      left = rect.left;
    }
    if (left < margin) left = margin;
    if (left + width > window.innerWidth - margin) {
      left = window.innerWidth - margin - width;
    }

    const spaceBelow = window.innerHeight - rect.bottom - margin - gap;
    const spaceAbove = rect.top - margin - gap;
    // Flip rule: only flip up if (a) below doesn't fit AND (b) above
    // genuinely has more room. Avoids ping-ponging when both sides
    // are tight.
    const flipUp = spaceBelow < opts.height && spaceAbove > spaceBelow;
    if (flipUp) {
      menuStyle.value = {
        position: "fixed",
        top: "auto",
        bottom: `${window.innerHeight - rect.top + gap}px`,
        left: `${left}px`,
        width: `${width}px`,
        maxHeight: `${Math.max(96, Math.min(opts.height, spaceAbove))}px`,
      };
      return;
    }
    menuStyle.value = {
      position: "fixed",
      top: `${rect.bottom + gap}px`,
      left: `${left}px`,
      width: `${width}px`,
      maxHeight: `${Math.max(96, Math.min(opts.height, spaceBelow))}px`,
    };
  }

  // Same capture-phase scroll/resize listeners the existing pickers
  // (ChatSettingsMenu, ModelPicker, PermissionModePicker) use, so an
  // open menu re-anchors when ANY ancestor (chat pane, modal body,
  // page) scrolls — not just the document.
  function onResize(): void {
    reposition();
  }
  function onScroll(): void {
    reposition();
  }

  onMounted(() => {
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onScroll, true);
  });
  onUnmounted(() => {
    window.removeEventListener("resize", onResize);
    window.removeEventListener("scroll", onScroll, true);
  });

  return { menuStyle, reposition };
}
