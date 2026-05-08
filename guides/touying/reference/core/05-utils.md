# `utils` — Utility Functions

> Source: [src/utils.typ](https://github.com/touying-typ/touying/blob/main/src/utils.typ)

The `utils` module is the workhorse — counters, layout helpers, theme
helpers, and small functional helpers.

## Counters and progress

### `utils.slide-counter`

Typst counter that increments on every slide.

```typst
#context utils.slide-counter.display()
```

### `utils.last-slide-number`

Number of the last slide before the appendix (content value).

```typst
#context utils.slide-counter.display() + " / " + utils.last-slide-number
```

### `utils.touying-progress(callback)`

Runs `callback(ratio)` where `ratio: float` ∈ `[0.0, 1.0]` is the
current progress through the deck.

```typst
#utils.touying-progress(ratio => {
  box(width: ratio * 100%, height: 4pt, fill: blue)
})
```

## Heading helpers

### `utils.display-current-heading(level: 1, style: auto, setting: ...)`

Displays the most recent level-N heading. `style: auto` lets users style
via `show heading: set text(...)`.

### `utils.display-current-short-heading(level: 1)`

Like above but strips numbering.

### `utils.current-heading()`

Returns the current heading element (for use inside `outline.entry`
show rules).

### `utils.short-heading(it)`

Helper for `<short-heading-label>` patterns — extracts the short label
from a heading.

### `utils.display-info-date(self)`

Formats `self.info.date` according to `config-common(datetime-format)`.

## Layout helpers

### `utils.fit-to-height(width: none, prescale-width: none, grow: true, shrink: true, height, body)`

Scale `body` to fill `height`. `width:` constrains post-scale width.
`prescale-width:` controls reflow assumption. See
[`../../tutorial/utilities/01-fit-to.md`](../../tutorial/utilities/01-fit-to.md).

### `utils.fit-to-width(grow: true, shrink: true, width, body)`

Scale `body` to fill `width`.

### `utils.page-args-from-aspect-ratio(aspect-ratio)`

Compute page dimensions from `"16-9"` / `"4-3"` / `"16-10"` strings.
Used in custom themes:

```typst
config-page(..utils.page-args-from-aspect-ratio(aspect-ratio), ...)
```

## Cover helpers

### `utils.semi-transparent-cover(self: none, constructor: rgb, alpha: 85%, body)`

Default semi-transparent cover. Wraps `body` in a `cover-with-rect`
using the page-fill color at reduced alpha.

### `utils.cover-with-rect(fill: ..., body)`

Lower-level cover primitive — wraps `body` with a colored rectangle.

### `utils.update-alpha(constructor: rgb, color, alpha)`

Returns `color` with `alpha` applied via `constructor`.

## Theme helpers

### `utils.methods(self) -> (uncover, only, alternatives)`

Returns animation primitives bound to the current `self` (so they read
`self.subslide` correctly):

```typst
#slide(repeat: 3, self => {
  let (uncover, only, alternatives) = utils.methods(self)
  // ...
})
```

### `utils.alert-with-primary-color(self: none, it)`

`text(fill: self.colors.primary, it)` — shorthand for `#alert[...]` in
custom themes.

### `utils.merge-dicts(..dicts)`

Right-biased merge of dicts (last value wins). Used to apply
`config-page(...)` overrides inside slide functions:

```typst
self = utils.merge-dicts(self, config-page(header: ..., footer: ...))
```

### `utils.call-or-display(self, value)`

If `value` is callable, call it with `self`; otherwise display it
directly. Used for header / footer values that may be either content
or `(self) => content`:

```typst
utils.call-or-display(self, self.store.footer)
```

### `utils.section-relationship(entry) -> int`

Returns -2 / -1 / 0 / 1 / 2 indicating where `entry` is relative to the
current heading:

| Value | Meaning |
| ----- | ------- |
| `-2`  | Earlier section, different top-level. |
| `-1`  | Earlier sibling in the same top-level. |
| `0`   | Current heading or its children. |
| `1`   | Future sibling in the same top-level. |
| `2`   | Later section, different top-level. |

Use it to roll your own outline styling. See
[`../../tutorial/progress/02-sections.md`](../../tutorial/progress/02-sections.md).

## Compatibility helpers

### `utils.empty-page(self)` *(deprecated)*

Used in pre-v0.5 themes; replaced by
`config-common(freeze-slide-counter: true) + config-page(margin: 0em)`.

### `utils.size-to-pt(size, container-dimension)`

Convert a `length`/`ratio`/`relative` to `pt` given the container
dimension. Used by `fit-to-height` / `fit-to-width` internally.

## See also

- [`01-configs.md`](./01-configs.md) — `config-*` helpers.
- [`03-components.md`](./03-components.md) — layout components.
- [`../../tutorial/progress/`](../../tutorial/progress/) — counters /
  progress in context.
