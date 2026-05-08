# `configs` — Configuration Functions

> Source: [src/configs.typ](https://github.com/touying-typ/touying/blob/main/src/configs.typ)

Touying configuration is split across several `config-*` helpers, each
producing a sub-dict that is merged into `self`. Themes accept these
helpers as positional / named arguments to `<name>-theme.with(...)`.

## `config-page(...)`

Page-level settings (margin, header, footer, fill, …). Mirrors Typst's
`set page(...)` but goes into `self.page` instead of being a state
mutation.

Common keys:

- `paper` — `"presentation-16-9"`, `"presentation-4-3"`, etc.
- `width` / `height` / `margin` — explicit dimensions.
- `header` / `footer` — content or `self => content` callback.
- `header-ascent` / `footer-descent` — gap from outer margin edge.
- `fill` — background color.
- `numbering` — page numbering format.

Example:

```typst
config-page(
  margin: (x: 4em, y: 2em),
  header: align(top)[Header],
  footer: align(bottom)[Footer],
  fill: blue.lighten(80%),
)
```

## `config-common(...)`

Cross-cutting behaviour. Common keys:

- `slide-fn`, `new-section-slide-fn`, `default-composer` — function
  hooks installed by themes.
- `slide-level` *(int, default `2`)* — heading level that creates a slide.
- `handout` *(bool, default `false`)* — handout mode (collapse subslides).
- `handout-subslides` *(int / array / str)* — which subslides to keep.
- `appendix` *(bool, default `false`)* — disable slide counter.
- `breakable` *(bool, default `true`)* — allow overflow to next page.
- `clip` *(bool, default `false`)* — visually clip overflow.
- `detect-overflow` *(bool, default `true`)* — panic on overflow.
- `preamble` *(content / fn)* — code to run before every slide.
- `subslide-preamble` *(dict)* — preamble per subslide index.
- `frozen-counters` *(tuple of counters)* — counters that don't advance.
- `frozen-states` *(tuple of states)* — states that don't change.
- `enable-pdfpc` *(bool, default `true`)* — generate `<pdfpc-file>` label.
- `show-notes-on-second-screen` — `right` / `left` / `top` / `bottom`.
- `horizontal-line-to-pagebreak` *(bool, default `true`)* — `---` ⇒
  `pagebreak()`.
- `nontight-list-enum-and-terms` *(bool, default `true`)* — force
  `tight: false` on lists.
- `align-list-marker-with-baseline` *(bool, default `false`)*.
- `scale-list-items` *(float / `auto`)* — list-item scale factor.
- `receive-body-for-new-section-slide-fn` *(bool, default `false` since
  v0.7.3)* — pass body content to the section-slide function.

## `config-info(...)`

Presentation metadata. Keys:

- `title`, `subtitle`, `author`, `date`, `institution`, `contact`,
  `logo`, `short-title` *(default `auto`)*.
- `extra` — dict of arbitrary extra fields.

Read via `self.info.<field>` (or `self.info.extra.<custom>`).

## `config-colors(...)`

Color palette. Two dimensions:

| Hue        | Brightness |
| ---------- | ---------- |
| `neutral`  | `default`, `light`, `lighter`, `lightest`, `dark`, `darker`, `darkest` |
| `primary`  | (same brightness scale) |
| `secondary`| (same) |
| `tertiary` | (same) |

Combine: `primary-light`, `neutral-darkest`, `secondary-dark`, etc.

```typst
config-colors(
  primary:           rgb("#5E8B65"),
  neutral-lightest:  rgb("#ffffff"),
  neutral-darkest:   rgb("#000000"),
)
```

Read via `self.colors.primary`, etc.

## `config-methods(...)`

Method bindings — install / replace `slide`, `init`, `cover`, `alert`,
etc.

```typst
config-methods(
  init: (self: none, body) => { set text(...); body },
  slide: my-slide,
  alert: utils.alert-with-primary-color,
  cover: utils.semi-transparent-cover,
)
```

## `config-store(...)`

Theme-private storage — anything you want to keep around but don't want
to clutter the global namespace. Read via `self.store.<key>`.

```typst
config-store(
  title: none,
  footer: footer,
  custom-thing: ...,
)
```

## `touying-set-config(config, defer: false, body)`

Override config for the current slide and all subsequent slides:

```typst
#show: touying-set-config.with(config-page(fill: blue.lighten(80%)))
```

With `defer: true`, applied at the start of the next slide (this is how
`#show: appendix` works internally).

## `touying-get-config(key: none, default: type, ...)`

Query the live config (evaluated at `context` time):

```typst
#touying-get-config()                  // whole dict
#touying-get-config().info.author      // dictionary access
#touying-get-config("info.author")     // dot-key lookup
#touying-get-config("nope", default: "fallback")
```

> **Warning.** For *custom* keys set via `touying-set-config(..)`, use
> the **string-key** form. Chained dictionary access on custom keys
> tries to access `.value` on a content element and fails.

## See also

- [`../../tutorial/04-settings.md`](../../tutorial/04-settings.md) — full settings tutorial.
- [`02-core.md`](./02-core.md) — for `touying-set-config` / `touying-get-config` internals.
