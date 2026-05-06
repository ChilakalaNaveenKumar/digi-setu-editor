/**
 * Ambient type shim for `vue-virtual-scroller` v2 (Vue 3 beta).
 *
 * The package ships only ESM JS — no .d.ts. We declare the small subset
 * of the API we actually use (DynamicScroller / DynamicScrollerItem and
 * the CSS side-effect import) so consumer files type-check cleanly.
 */
declare module "vue-virtual-scroller" {
  import type { DefineComponent } from "vue";
  export const DynamicScroller: DefineComponent<Record<string, unknown>>;
  export const DynamicScrollerItem: DefineComponent<Record<string, unknown>>;
  export const RecycleScroller: DefineComponent<Record<string, unknown>>;
  const _default: { install: (app: unknown) => void };
  export default _default;
}

declare module "vue-virtual-scroller/dist/vue-virtual-scroller.css";
