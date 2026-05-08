# `polygon()` — Regular Polygon

Draws a regular polygon (3+ sides).

## Signature

```text
polygon(
  origin: coordinate,
  sides:  int,
  angle:  angle,
  name:   none | str = none,
  anchor: ,
  ..style,
)
```

## Parameters

- **`origin`** — centre coordinate.
- **`sides`** — number of sides (must be `>= 3`).
- **`angle`** — rotation around `origin`. The first vertex is placed at
  `angle`; subsequent vertices follow counter-clockwise.
- **`name`** — element name.
- **`radius`** *(style)* — distance from centre to vertex.

## Styling

- **Root:** `polygon`
- Inherits `fill`, `stroke`. Supports `mark`.

## Anchors

Path anchors plus the standard compass border anchors.

## Example

See [`examples/07-polygon/07-polygon.typ`](./examples/07-polygon/07-polygon.typ).
