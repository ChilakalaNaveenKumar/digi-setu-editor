# `rect()` — Rectangle

Draws a rectangle between two coordinates.

## Signature

```text
rect(
  a: coordinate,
  b: coordinate,
  name:   none | str = none,
  anchor: none | str = none,
  ..style: style,
)
```

## Parameters

- **`a`** — bottom-left corner.
- **`b`** — top-right corner. Use a relative coordinate
  `(rel: (width, height))` to size by extent rather than absolute corner.
- **`name`** / **`anchor`** — standard.
- **`radius`** *(style)* — `number | ratio | dictionary`. Corner radius.
  See **Corner radii** below.

## Corner radii

`radius:` accepts:

- A `number` — same radius on all four corners.
- A `ratio` — relative to the rectangle's width/height.
- A dictionary — per-corner control. Valid keys:
  `north`, `east`, `south`, `west`, `north-west`, `north-east`,
  `south-west`, `south-east`. The cardinal keys (`north`, `east`, …) target
  *both* corners on that side. Use `rest:` to set a default for unmentioned
  corners.
- Each value can be a `number`, `ratio`, or `(rx, ry)` array for an
  elliptical corner.

## Styling

- **Root:** `rect`
- Inherits `fill`, `stroke`.

## Anchors

Supports border and path anchors. Default is `center`.

## Example

See [`examples/11-rect/11-rect.typ`](./examples/11-rect/11-rect.typ).
