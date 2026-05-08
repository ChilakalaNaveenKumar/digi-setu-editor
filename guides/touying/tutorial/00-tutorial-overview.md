# Touying Tutorial — Overview

Read these in order before diving into per-feature pages or themes.

| File | Covers |
| ---- | ------ |
| [`01-getting-started.md`](./01-getting-started.md) | The minimal first deck (`simple-theme`) and the more complex `university-theme` example with CeTZ / Fletcher / Theorion integrations. |
| [`02-code-styles.md`](./02-code-styles.md) | Simple-style (`= / ==` headings, `#pause`, `---`, `#pagebreak()`) vs block-style (`#slide[...]`, `#empty-slide[]`, `#focus-slide`); convention over configuration with `new-section-slide-fn`. |
| [`03-sections.md`](./03-sections.md) | Sections / subsections / `slide-level`; numbering with `numbly`; outlines via `components.adaptive-columns`; special heading labels (`<touying:hidden>`, `<touying:unnumbered>`, `<touying:handout>`, …); `#show: appendix`. |
| [`04-settings.md`](./04-settings.md) | Global styles, `config-info`, `config-common(preamble: ...)`, show-rule overrides via `touying-set-config`, local overrides via `slide(config: ...)`, deferred config, frozen counters, querying via `touying-get-config`. |
| [`05-layout.md`](./05-layout.md) | Typst's page model, headers / footers / margins via `config-page`, two- and three-column slides via `composer` / `cols`, `lazy-v` for equal-height columns, `breakable: false` / `clip` to prevent overflow. |
| [`06-multi-file.md`](./06-multi-file.md) | The recommended `globals.typ` / `main.typ` / `content.typ` split; `sections/` directory layout. |
| [`07-build-your-own-theme.md`](./07-build-your-own-theme.md) | End-to-end Bamboo theme: `bamboo-theme(...)`, `config-colors`, `config-store`, custom header / footer, custom `slide` / `title-slide` / `new-section-slide` / `focus-slide`. |
| [`dynamic/`](./dynamic/) | `#pause`, `#meanwhile`, `only`, `uncover`, `alternatives`, math equation animation, cover function, CeTZ / Fletcher animation, handout mode, named waypoints. |
| [`progress/`](./progress/) | `utils.slide-counter`, `utils.last-slide-number`, `utils.touying-progress`, `utils.display-current-heading`, `components.progressive-outline` and friends. |
| [`utilities/`](./utilities/) | `utils.fit-to-height`, `utils.fit-to-width`. |

After this you should be comfortable navigating `themes/`, `integration/`,
`external/`, and `reference/`. Each page assumes you know:

1. Slides start with `#import "@preview/touying:0.7.3": *` plus
   `#import themes.<name>: *` and `#show: <name>-theme.with(...)`.
2. **Headings drive structure.** `=` is a section, `==` is a slide title (or
   subsection — depending on `slide-level`), `===` is a subsubsection.
3. **`#slide[...]`** is the block-style alternative needed for advanced
   features (focus slides, callback animation, theme-specific extras).
4. **Animations are subslides.** `#pause` separates one slide into multiple
   subslides; `only` / `uncover` / `alternatives` query `self.subslide` —
   pass `repeat: N` when using callback style.
5. **`config-*` is the unified API.** All themes accept the same
   `config-info`, `config-colors`, `config-page`, `config-common`,
   `config-methods`, `config-store` arguments.
