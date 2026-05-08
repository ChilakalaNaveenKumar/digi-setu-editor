# `tiling()` — Repeating Pattern Fills

A `tiling` is a paint value that repeats a small piece of content in a
grid to fill an entire shape, text run, or background. Anywhere a
`color` is accepted, you can also pass a `tiling`.

> The constructor used to be called `pattern`. The old name still works
> (alias) but is deprecated since Typst 0.13. Prefer `tiling`.

## Constructor

```text
tiling(
  size:     auto | array = auto,        // (width, height) of one tile
  spacing:  array = (0pt, 0pt),         // gap between tiles
  relative: auto | "self" | "parent" = auto,
  body:     content                      // what one tile draws
) -> tiling
```

`spacing < size` ⇒ tiles overlap. `spacing > size` ⇒ visible gaps the
color of the surface behind the tiling.

## Relativeness

Same model as gradients:

- `auto` (default): tile origin sits at the shape's local origin — except
  for text fills, which behave as if `"parent"`.
- `"self"`: explicit version of the default — origin at the shape's bbox.
- `"parent"`: origin at the surrounding container (page if at top level,
  innermost block/box otherwise).

For text fills set `relative: "parent"` so the same tiling stretches
across the whole text block instead of restarting per glyph.

## Building tile content

The `body` is normal Typst content. Use `place(...)`, lines, shapes, or
even small text. Keep it sized to the tile's `size`.

```typst
#let stripes = tiling(size: (8pt, 8pt))[
  #place(line(start: (0%, 0%), end: (100%, 100%), stroke: 0.5pt))
]
```

## Examples of practical use

| Use case                         | Approach                                                                |
| -------------------------------- | ----------------------------------------------------------------------- |
| Hatch fill (\\\\\\\\\\\\)        | `tiling(size: (6pt, 6pt))[#place(line(end: (100%, 100%)))]`             |
| Dotted background                | `tiling(size: (10pt, 10pt))[#place(circle(radius: 1pt, fill: black))]`   |
| Gradient-textured text           | `set text(fill: tiling(..., relative: "parent", body: gradient...))`    |
| Watermark on the page background | `set page(background: rect(fill: tiling(...)))`                          |

## Tips

- Keep tiles small but not pixel-tiny — very small tiles bloat PDF size.
- For `relative: "parent"` to look right inside boxes, remember that any
  intermediate `box`/`block`/`grid` resets the parent.
