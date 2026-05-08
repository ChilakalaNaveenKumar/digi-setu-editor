# Visualize – Overview

The **Visualize** module is Typst's drawing toolkit: shapes (`circle`, `rect`,
`square`, `ellipse`, `polygon`, `polygon.regular`), parametric drawings
(`curve`, `line`), raster/vector graphics (`image`), and the appearance
primitives shared by all of them (`color`, `gradient`, `tiling`, `stroke`).

For richer figures (CAD-style drawings, plots, charts) reach for the
[CeTZ](https://typst.app/universe/package/cetz) and
[Plotly-style](https://typst.app/universe) packages from Typst Universe — they
build on top of the primitives documented here.

## What lives in this module

| Group        | Functions / types                                                        |
| ------------ | ------------------------------------------------------------------------ |
| Boxed shapes | `rect`, `square`, `circle`, `ellipse`                                    |
| Free shapes  | `curve`, `polygon`, `polygon.regular`, `line`                            |
| Graphics     | `image`                                                                  |
| Paint        | `color`, `gradient` (linear/radial/conic), `tiling`                      |
| Stroke       | `stroke` (thickness, cap, join, dash, miter limit)                       |
| Deprecated   | `path` (use `curve`), `image.decode` / `*.decode` (pass `bytes` instead) |

All boxed shapes (`rect`, `square`, `circle`, `ellipse`) accept the same
appearance parameters: `fill`, `stroke`, `inset`, `outset`, `radius` (where
applicable), and an optional positional `body`. They differ only in geometry.

## Accessibility

Every shape and path Typst draws is **automatically marked as a PDF artifact**.
Assistive technology (screen readers) skips them by default; only the textual
content inside the shape (e.g. a label inside a `rect[...]`) is read.

If you assemble shapes into something with semantic meaning (a diagram, a
flowchart, a logo with text), wrap it in a `figure(...)` and supply the
`alt:` parameter so AT users get an equivalent description:

```typst
#figure(
  rect(width: 30pt, height: 30pt, fill: red, stroke: 1pt + black),
  alt: "Red square outlined in black, used as the warning sign in the diagram.",
)
```

For [`image`](./06-image.md) the alt text goes on the image directly (or on
the figure when the image plus surrounding labels form a single unit).

## Coordinates and positions

`curve.move`, `curve.line`, `curve.cubic`, `polygon`, `path`, and `line`
accept arrays of two values (`(x, y)`). Each value can be:

- A length (`30pt`, `1cm`)
- A ratio (`50%`) — relative to the parent container
- A `relative` (`50% + 5pt`) — combination

`(0pt, 0pt)` is the top-left of the local coordinate system. `y` grows
downward.

For `curve` segments you can also pass `relative: true` to express each
position relative to the previous pen position.

## Painting and stroking

Anywhere a `fill:` is accepted you can pass `none`, a `color`, a
`gradient`, or a `tiling`. Anywhere a `stroke:` is accepted you can pass
`none`, `auto`, a thickness (`2pt`), a color, a `color + thickness`
combination (`2pt + red`), a full `stroke(...)` object, a
`gradient`/`tiling`, or a per-side dictionary (`(top: 2pt, rest: 0.5pt)`).

```typst
#rect(fill: blue, stroke: 2pt + red)
#rect(stroke: (top: 2pt + red, rest: 0.5pt + black))
#rect(fill: gradient.linear(red, blue, angle: 45deg))
```

When you set a `fill` on a shape, the **default stroke disappears**. Set
both explicitly if you want both.

## Deprecation watch (Typst 0.14+)

| Deprecated                | Use instead                           |
| ------------------------- | ------------------------------------- |
| `path(...)`               | `curve(...)`                          |
| `image.decode(bytes)`     | `image(bytes)` (pass bytes directly)  |
| `cbor.decode` / `csv.decode` / `json.decode` / `toml.decode` / `xml.decode` / `yaml.decode` | Pass `bytes` directly to the loader (`json(bytes)`, etc.) |
| `pattern(...)`            | `tiling(...)` (pattern is an alias)   |

Stick to the new APIs in new code; the old ones still work but emit
warnings and will be removed in 0.15.
