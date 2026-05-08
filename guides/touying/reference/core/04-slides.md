# `slides` — Slide Engine

> Source: [src/slides.typ](https://github.com/touying-typ/touying/blob/main/src/slides.typ)

The `slides` module owns the high-level slide rendering pipeline. Theme
slide functions wrap this engine with theme-specific styling.

## The `slide(...)` function

Every theme exports its own `slide(...)` (with possibly different
default args), but they all share the same base shape:

```typst
#let slide(
  config:   (:),         // local config overrides
  repeat:   auto,        // number of subslides; auto = inferred
  setting:  body => body,// per-slide show / set rule
  composer: cols,        // column composer for `body, body, ...`
  // theme-specific
  title:    auto,
  align:    horizon,
  footer:   auto,
  ..args,
)[
  ...content...
]
```

Common parameters:

- **`config:`** *(dict)* — shorthand for `touying-set-config`
  inside this slide only.
- **`repeat:`** *(int / auto)* — number of subslides. `auto` only works
  when subslide count is inferable from `#pause` markers; explicit when
  using `utils.methods(self)` bindings.
- **`setting:`** *(fn)* — wraps the body with extra `set` / `show` rules.
- **`composer:`** *(fn)* — how to combine multiple bodies passed as
  positional args. Default is `cols`. Use `(1fr, 1fr)` for equal halves,
  `(2fr, 1fr)` for asymmetric, `auto` for natural width.
- **`title:`** *(content / auto / none)* — per-slide title override.
- **`footer:`** *(content / fn / auto / none)* — per-slide footer override.

## Callback-style `slide`

Pass a `(self) => content` callback instead of a content block to
access `self.subslide`:

```typst
#slide(repeat: 3, self => {
  let (only, uncover, alternatives) = utils.methods(self)
  [Subslide #self.subslide:]
  uncover("2-")[Reveal from 2.]
})
```

The callback receives the *fully merged* `self` — all `config-*`
overrides, theme defaults, and `slide(config: ...)` overrides applied.

## Multi-body slides via `composer`

Pass multiple positional bodies; `composer` lays them out side-by-side:

```typst
#slide[
  Left column.
][
  Right column.
]

// Custom composer
#slide(composer: (1fr, 2fr))[
  Narrow left.
][
  Wide right.
]
```

The default `composer: cols` accepts the same params as `components.cols`.

## Special slide functions (per-theme)

Each theme also exports:

- `title-slide(...)` — opens the deck.
- `focus-slide[...]` — full-bleed primary-color slide for emphasis.
- `centered-slide[...]` — content centered on the page (simple theme).
- `outline-slide(...)` — TOC slide (aqua, dewdrop, stargazer).
- `matrix-slide(...)` — grid layout (university theme).
- `new-section-slide(short-title: ..., title)` — new section heading
  slide (auto-fired from `=` headings if registered via
  `config-common(new-section-slide-fn: ...)`).
- `empty-slide[...]` — bare slide with no header / footer.

## See also

- [`02-core.md`](./02-core.md) — `touying-slide`, `touying-slide-wrapper`.
- [`../../themes/`](../../themes/) — per-theme slide function families.
- [`../../tutorial/02-code-styles.md`](../../tutorial/02-code-styles.md)
  — when to use block-style `#slide[...]`.
