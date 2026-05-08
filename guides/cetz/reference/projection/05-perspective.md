# `perspective()` — Perspective Projection

Sets up a perspective projection environment. Coordinates are transformed by
a view matrix and then projected with perspective division:

\[
x' = \frac{d_{ref} \cdot x}{w}, \quad y' = \frac{d_{ref} \cdot y}{w}
\]

where `w = max(-z, near)` in view space.

By default this uses the same isometric camera angles as
[`ortho`](./01-ortho.md), but with perspective foreshortening.

## Signature

```text
perspective(
  x: angle,
  y: angle,
  z: angle,
  distance:        number | auto = auto,
  sorted:          bool = false,
  cull-face:       none | str = none,
  reset-transform: bool = false,
  body:            element,
)
```

## Parameters

- **`x` / `y` / `z`** — rotation angles per axis.
- **`distance`** — distance from camera to scene origin. `auto` derives a
  stable value from the scene depth.
- **`sorted`** — sort drawables by depth (back to front).
- **`cull-face`** — `"cw"` or `"ccw"` for back-face culling.
- **`reset-transform`** — ignore the current transform.
- **`body`** — elements to draw.

## Example

See [`examples/05-perspective/05-perspective.typ`](./examples/05-perspective/05-perspective.typ).
