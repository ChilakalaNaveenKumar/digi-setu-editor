# `ortho()` — Orthographic Projection

Sets up an orthographic projection environment. The body is rendered through
a transform matrix that rotates everything around the x, y, z axes by the
given angles.

By default an **isometric** projection is set: `x ≈ 35.264°`, `y = 45°`.

## Signature

```text
ortho(
  x: angle,
  y: angle,
  z: angle,
  sorted:           bool = false,
  cull-face:        none | str = none,
  reset-transform:  bool = false,
  flatten:          bool = false,
  body:             element,
)
```

## Parameters

- **`x` / `y` / `z`** — rotation angles per axis.
- **`sorted`** — sort drawables by max distance (front-to-back).
- **`cull-face`** — `"cw"` or `"ccw"`. Polygons of the specified winding
  order are not drawn (back-face culling).
- **`reset-transform`** — ignore the current transformation matrix when
  building the projection.
- **`flatten`** — set all `z` components to `0` after projection.
- **`body`** — the elements to draw.

## Example

See [`examples/01-ortho/01-ortho.typ`](./examples/01-ortho/01-ortho.typ).
