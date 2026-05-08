# `set-viewport()` — Span a Logical Viewport

Spans a viewport between two coordinates and sets up scaling and translation
so that drawing in **logical bounds** maps to the physical rectangle on the
canvas.

## Signature

```text
set-viewport(
  from: coordinate,
  to:   coordinate,
  bounds: vector,
)
```

## Parameters

- **`from`** — bottom-left physical coordinate.
- **`to`** — top-right physical coordinate.
- **`bounds`** — vector that describes the inner width, height and depth of
  the viewport in **logical units**. Subsequent draws use logical units;
  CeTZ scales them into the physical rectangle.

## Use case

Plotting libraries often use this to keep the data range arbitrary while
the rendered chart occupies a fixed area:

```typst
rect((0, 0), (2, 2))
set-viewport((0, 0), (2, 2), bounds: (10, 10))
circle((5, 5))   // logical (5,5) → physical (1,1) (centre of the rect)
```

## Example

See [`examples/08-set-viewport/08-set-viewport.typ`](./examples/08-set-viewport/08-set-viewport.typ).
