# `grid()` — Coordinate Grid

Draws a regular grid between two coordinates.

## Signature

```text
grid(
  from: coordinate,
  to:   coordinate,
  name: none | str = none,
  ..style: style,
)
```

## Parameters

- **`from`** — top-left coordinate (or any corner; CeTZ infers the
  rectangle).
- **`to`** — opposite corner.
- **`name`** — element name.
- **`step`** *(style)* — `number | array | dictionary`. Distance between
  lines. `1` = one grid line every coordinate unit. A 2-tuple or
  `(x: …, y: …)` dict sets per-axis steps.
- **`shift`** *(style)* — `(x, y)` offset for grid lines.
- **`help-lines`** *(style)* — `bool`. When `true`, forces stroke to
  `gray + 0.2pt` (TikZ "help-lines" convention).

## Styling

- **Root:** `grid`
- Inherits `stroke`.

## Anchors

Border anchors (compass) on the implied bounding rectangle.

## Example

See [`examples/09-grid/09-grid.typ`](./examples/09-grid/09-grid.typ).
