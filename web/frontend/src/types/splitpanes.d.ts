/**
 * Lightweight ambient module declaration for `splitpanes`. The package
 * doesn't ship its own .d.ts; we declare just the two component shapes
 * we use so vue-tsc stays clean. Props/events are typed loosely on
 * purpose — we only consume the `@resize` event and pass numeric size
 * props, both of which we handle locally with our own type guards.
 */
declare module "splitpanes" {
  import type { DefineComponent } from "vue";
  export const Splitpanes: DefineComponent<{
    horizontal?: boolean;
    pushOtherPanes?: boolean;
    dblClickSplitter?: boolean;
    rtl?: boolean;
    firstSplitter?: boolean;
    class?: string;
  }>;
  export const Pane: DefineComponent<{
    size?: number | string;
    minSize?: number | string;
    maxSize?: number | string;
  }>;
}
