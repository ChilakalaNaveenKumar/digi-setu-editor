# `codly()` — The Configuration Function

Configures every `raw(block: true)` element that follows it in layout
order. `codly(...)` behaves like a Typst `set` rule, *not* a `show` rule:
it stores the configuration in states and applies it to all subsequent
code blocks until the next `codly(...)`, `codly-reset()`, or `local(...)`
override.

## Signature

```text
codly(
  enabled:                   bool                                       = true,
  offset:                    int                                        = 0,
  offset-from:               none | label                               = none,
  range:                     none | array                               = none,
  ranges:                    none | array                               = none,
  languages:                 dict                                       = (:),
  display-name:              bool                                       = true,
  display-icon:              bool                                       = true,
  default-color:             color | gradient | tiling                  = rgb("#283593"),
  radius:                    length                                     = 0.32em,
  inset:                     length | dictionary                        = 0.32em,
  fill:                      none | color | gradient | tiling           = none,
  zebra-fill:                none | color | gradient | tiling           = luma(240),
  stroke:                    none | stroke                              = 1pt + luma(240),
  lang-inset:                length | dictionary                        = 0.32em,
  lang-outset:               dictionary                                 = (x: 0.32em, y: 0pt),
  lang-radius:               length                                     = 0.32em,
  lang-stroke:               none | stroke | function                   = (lang) => lang.color + 0.5pt,
  lang-fill:                 none | color | gradient | tiling | function = (lang) => lang.color.lighten(80%),
  lang-format:               type(auto) | none | function               = auto,
  number-format:             function | none                            = numbering.with("1"),
  number-align:              alignment                                  = left + horizon,
  number-placement:          str                                        = "inside",
  smart-indent:              bool                                       = true,
  skip-last-empty:           bool                                       = true,
  smart-skip:                bool | dictionary                          = false,
  annotations:               array | none                               = none,
  annotation-format:         none | function                            = numbering.with("(1)"),
  highlighted-lines:         array | none                               = (),
  highlighted-default-color: color | tiling | gradient                  = orange.lighten(60%),
  highlights:                array | none                               = none,
  highlight-radius:          length                                     = 0.32em,
  highlight-fill:            function                                   = (color) => color.lighten(80%),
  highlight-stroke:          stroke | function                          = (color) => 0.5pt + color,
  highlight-inset:           length | dictionary                        = 0.32em,
  highlight-outset:          length | dictionary                        = 0em,
  highlight-clip:            bool                                       = true,
  reference-by:              str                                        = "line",
  reference-sep:             str | content                              = "-",
  reference-number-format:   function                                   = numbering.with("1"),
  header:                    content | none                             = none,
  header-repeat:             bool                                       = false,
  header-transform:          function                                   = (x) => x,
  header-cell-args:          array | dictionary | arguments             = (),
  footer:                    content | none                             = none,
  footer-repeat:             bool                                       = false,
  footer-transform:          function                                   = (x) => x,
  footer-cell-args:          array | dictionary | arguments             = (),
  breakable:                 bool                                       = true,
  skips:                     array | none                               = none,
  skip-line:                 content | none                             = align(center)[ ... ],
  skip-number:               content | none                             = [ ... ],
  aliases:                   dictionary                                 = (:),
)
```

(Argument order in the signature above mirrors the upstream manual's
"equivalent definition of the codly function" snippet exactly.)

## Set-rule semantics

> Unlike regular set-rules in native Typst, there are two considerations:
>
> - The codly function uses **states** to store the configuration, this
>   means that it is dependent on layout order for the order in which
>   settings are applied.
> - The codly function is **not local**, it sets the configuration for
>   all code blocks that follow it in layout order, unless overriden by
>   another codly call. This means that you cannot use it to set the
>   configuration for a specific code block. To perform this, use the
>   `local` function to set the configuration for a specific "section".

## Auto-reset behaviour

Each argument is independently flagged "Automatically reset: yes / no" in
the manual. As a rule of thumb:

- **Reset after each block:** `header`, `footer`, `offset`,
  `offset-from`, `range`, `ranges`, `annotations`, `highlights`,
  `highlighted-lines`, `highlight-radius`, `skips`.
- **Sticky (carry over to subsequent blocks):** all the cosmetic
  settings (`radius`, `inset`, `fill`, `zebra-fill`, `stroke`, `lang-*`,
  `number-*`, `display-*`, `smart-*`, `breakable`,
  `highlighted-default-color`, the various `highlight-*` setters apart
  from `highlight-radius`, `reference-*`, `aliases`, `languages`).

The per-argument page in this folder restates the flag verbatim.

## Pitfalls

- **`#show: codly-init` first, then `codly(...)`.** A `codly(...)` call
  without an earlier `codly-init` is a silent no-op.
- **Layout order matters.** `codly(...)` writes into states and is
  evaluated in layout order, not document order; if you call it from
  inside a `place(..)` or a function used out-of-order it can land
  later than you expect.
- **One block only?** Use `local(...)` instead of `codly(...)` —
  `local(...)` is *not* sticky and avoids the layout-order tax.
- **Reset everything to defaults:** call `codly-reset()`. Calling
  `codly()` with no arguments does *not* reset; it leaves all sticky
  settings in place.

## Example

See [`examples/01-codly/01-codly.typ`](./examples/01-codly/01-codly.typ).

## Per-argument pages

See [`00-codly-overview.md`](./00-codly-overview.md) for the full table
of arguments grouped by theme.
