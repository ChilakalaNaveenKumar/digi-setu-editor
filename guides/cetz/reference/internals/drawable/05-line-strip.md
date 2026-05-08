# `drawable.line-strip()` — Polyline Drawable

Constructs a polyline drawable from a list of points. Sets up a single
`"line"` segment internally — convenient for axis ticks, polylines, and
anything where you don't need curves.

## Signature

```text
line-strip(
  points: array,
  close: bool = false,
  fill: color | none = none,
  stroke: stroke | none = none,
  fill-rule: "non-zero" | "even-odd" = "non-zero",
  tags: array = (),
) -> drawable
```

## Parameters

- **`points`** — array of 3-vectors.
- **`close`** — if `true`, the last point is joined back to the first.
- **`fill`**, **`stroke`**, **`fill-rule`**, **`tags`** — render options.

## Example

See [`examples/05-line-strip/05-line-strip.typ`](./examples/05-line-strip/05-line-strip.typ).
