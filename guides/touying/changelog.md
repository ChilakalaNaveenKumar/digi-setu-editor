# Changelog

> Source: <https://touying-typ.github.io/docs/changelog>
>
> Below is a curated changelog. Skip to the migration guides for v0.7.3 /
> v0.6.3 / v0.5.0 if you are upgrading.

## v0.7.3

### Minor breaking changes

- `#speaker-note[]` now **always** attaches to the previous slide, regardless
  of how that slide was created (explicit slide calls, heading-triggered
  section slides, normal content slides). Eliminates the "ghost empty slide"
  pitfall.
- `receive-body-for-new-section-slide-fn` (and variants) defaulted to
  `false` (was `true`).

### Migration

If you relied on content after `= Section` headings being absorbed into
the section slide body, set `receive-body-for-new-section-slide-fn: true`
in `config-common(...)` explicitly.

### Features

- `item-by-item-fn` and presets ([#347](https://github.com/touying-typ/touying/pull/347)).
- Improved `custom-progressive-outline`, new `section-relationship`
  ([#345](https://github.com/touying-typ/touying/pull/345)).
- Better `lazy-layout` for mixed layouts ([#355](https://github.com/touying-typ/touying/pull/355)).
- Add `cols` as alias for `side-by-side`; export `cols`, `lazy-xxx` to
  the public namespace ([#356](https://github.com/touying-typ/touying/pull/356)).
- `metropolis` gets `outline-slide` ([#349](https://github.com/touying-typ/touying/pull/349)).
- Warning for empty-slide content height detection.

## v0.7.1

### Features

- `breakable` and `clip` options to avoid slide overflow
  ([#336](https://github.com/touying-typ/touying/pull/336)).
- `lazy-v` (`lazy-h`) and `lazy-layout` for equalising multi-column
  block heights ([#339](https://github.com/touying-typ/touying/pull/339)).
- Additional `contact` and `extra` fields in `config-info`
  ([#342](https://github.com/touying-typ/touying/pull/342)).
- New `touying-get-config` function ([#333](https://github.com/touying-typ/touying/pull/333)).

### Fixes

- Fix `fit-to-height` and `size-to-pt`; allow text reflow.
- Fix waypoint markers ([#341](https://github.com/touying-typ/touying/pull/341)).

## v0.7.0

### Features

- **Major:** named **waypoints** ([#298](https://github.com/touying-typ/touying/pull/298)).
- Waypoint `start:` param + waypoints in `handout-subslides`
  ([#304](https://github.com/touying-typ/touying/pull/304)).
- `auto`, `"h"`-here string, and inverse function for string
  subslide-numbers and waypoints ([#301](https://github.com/touying-typ/touying/pull/301)).
- Implicitly allow fn-wrapper-based animation functions via reducer
  ([#300](https://github.com/touying-typ/touying/pull/300)).

### Notable fixes

- `cover-with-rect` no longer breaks long lines of text when partially hidden.
- Ghost-slide bug with show rules fixed; consistent handling of show rules
  and `defer:` keyword.
- `#alert` no longer delayed.
- Page margin merge / precedence corrected.
- Cover spacing issues around lists fixed.
- Negative subslide indices for `handout-subslides` parsed correctly.

## v0.6.3 — bugfix-and-features

### Features

- `#jump(n, relative: bool)` as unified animation control; `#pause` and
  `#meanwhile` redefined as sugar.
- `#handout-only` for inline content; `<touying:handout>` label for
  handout-exclusive slides ([#286](https://github.com/touying-typ/touying/pull/286)).
- `handout-subslides` to control which subslides appear in handout mode
  ([#288](https://github.com/touying-typ/touying/pull/288)).
- `#touying-raw` for animated code-block reveals
  ([#283](https://github.com/touying-typ/touying/pull/283)).
- Full-screen speaker-notes mode (`show-only-notes`)
  ([#281](https://github.com/touying-typ/touying/pull/281)).
- Arbitrary aspect ratios (e.g. `"16-10"`) across all themes and
  speaker-note second screen ([#280](https://github.com/touying-typ/touying/pull/280)).
- `#item-by-item` animation for list / enum / terms
  ([#278](https://github.com/touying-typ/touying/pull/278)).
- `subslide:` parameter on `#touying-recall`.
- `default-composer` in `config-common`.
- `cover-fn:` parameter on `uncover` for external integration (Fletcher).
- Inline mini-slides.
- Various theme polish (university, stargazer, simple, aqua).

### Theme migration guide (v0.6.3)

For theme authors:

```typst
// Before
self = utils.merge-dicts(self, config, config-page(...))
// After
self = utils.merge-dicts(self, config-page(...), config)
```

```typst
// Before
config-page(paper: "presentation-" + aspect-ratio, ...)
// After
config-page(..utils.page-args-from-aspect-ratio(aspect-ratio), ...)
```

## v0.6.2

- Allow customisation of `components.checkerboard` (#161).
- Various fixes: ratio / relative margins for full-width headers,
  `magic.bibliography-as-footnote` in Typst 0.14, theorion compatibility,
  `#meanwhile` in cetz, etc.

## v0.6.1

- Added [theorion](https://github.com/OrangeX4/typst-theorion) integration
  as the default math-theorem environment.

## v0.6.0

First Touying release for Typst 0.13.

- `auto` style for `display-current-heading` (theme creators can use
  `style: auto` for opt-in heading styling).
- `stretch: false` by default for `alternatives` (minor breaking).
- Various fixes (semi-transparent cover, type comparisons, horizontal-line
  bug in 0.13).

## v0.5.4 / v0.5.5

- New `#effect(text.with(fill: red), "2-")[Something]` for inline
  per-subslide effects.
- `align` argument added to university theme.
- Numerous bug fixes.

## v0.5.3

- `new-section-slide-fn` may receive `body` (controlled by
  `receive-body-for-new-section-slide-fn`).

## v0.5.0 — major refactor

This was the largest breaking change in Touying's history. Highlights:

- **No more closures and OOP-style `s = ...` setup.**
  - `#let slide(self: none, ..args) = { ... }` → `#let slide(..args) =
    touying-slide-wrapper(self => { ... })`. `self` is auto-injected.
  - All configuration via `config-xxx` syntax.
- **Touying-slide no longer has `section`, `subsection`, `title`
  parameters.** These become invisible level-1/2/3 headings via
  `self.headings`, controlled by `slide-level`.
- **Special heading labels** added: `<touying:hidden>`,
  `<touying:unnumbered>`, `<touying:unoutlined>`, `<touying:no-bookmark>`.
- `touying-recall()` to replay a specific slide.
- `nontight-list-enum-and-terms` (default `true`).
- `align-list-marker-with-baseline` (default `false`).
- `scale-list-items` to scale items by a factor.
- Direct use of `pause` / `meanwhile` in math (`$x + pause y$`).
- `#pause` / `#meanwhile` now work in `grid` and `table`.
- `#show: appendix` shorthand.
- `components.adaptive-columns()` for adaptive multi-column outlines.
- `magic.bibliography-as-footnote` for citation-style footnotes.
- `custom-progressive-outline`, `mini-slides` components.
- `touying-outline()` removed — use `outline()` directly.
- New stargazer theme.

### Theme migration guide (v0.5.0)

- Add `show: touying-slides.with(..)` configuration.
- Replace `self.methods.colors` with `config-colors(primary: rgb(...))`.
- Replace `self.page-args` with `config-page()`.
- Replace `self.methods.slide = slide` with `config-methods(slide: slide)`.
- Replace private theme variables (`self.xxx-footer`) with
  `config-store(footer: [..])` (read via `self.store.footer`).
- Move header / footer config inside the `slide` function (not the theme
  function).
- For `states.current-section-with-numbering`, use
  `utils.display-current-heading(level: 1)`.

## v0.4.x

- v0.4.2: theme(metropolis) decoupled text color with `neutral-dark`.
  Mark-style `uncover`, `only`, `alternatives` added.
- v0.4.1: Built-in outline + bookmark support; speaker-note for
  dual-screen; `touying-mitex` function; gallery wiki.
- v0.4.0: `#footnote[]` for all themes; subslide-aware footers / headers;
  numbered theorem environments via [ctheorems](https://typst.app/universe/package/ctheorems);
  numbering for sections / subsections.

## v0.3.x

- v0.3.3: Aqua template moved to `touying-aqua` package; theme
  `set`/`show` rule support without `setting`; simpler `composer`;
  `empty-slide` function.
- v0.3.2: Aqua theme; `s` no longer auto-exported (Breaking).
- v0.3.0: Better `show-slides` mode; `align` and `pad` support.

## v0.2.x

- v0.2.1: `touying-reducer` for cetz / fletcher; university theme;
  multiple bug fixes.
- v0.2.0: Callback-style `uncover` / `only` / `alternatives`;
  `fit-to-width` and `fit-to-height`; built-in section support
  (`states.current-section-title`, `states.touying-outline`,
  `states.touying-final-sections`, …).
