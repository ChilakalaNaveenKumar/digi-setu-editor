# `on-zy()` — Draw on the ZY Plane

Draws elements on the **zy-plane** with an optional `x` offset.

All vertices of all elements are mapped `(x, y) → (x_argument, y, x)` — the
body's local `x` axis becomes the world `z` axis.

## Signature

```text
on-zy(
  x:    number = 0,
  body: element,
)
```

## Parameters

- **`x`** — x offset for all coordinates in the body.
- **`body`** — elements to draw.

## Example

See [`examples/04-on-zy/04-on-zy.typ`](./examples/04-on-zy/04-on-zy.typ).
