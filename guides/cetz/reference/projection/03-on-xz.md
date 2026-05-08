# `on-xz()` — Draw on the XZ Plane

Draws elements on the **xz-plane** with an optional `y` offset.

All vertices of all elements are mapped `(x, y) → (x, y_argument, y)` — the
body's local `y` axis becomes the world `z` axis.

## Signature

```text
on-xz(
  y:    number = 0,
  body: element,
)
```

## Parameters

- **`y`** — y offset for all coordinates in the body.
- **`body`** — elements to draw.

## Example

See [`examples/03-on-xz/03-on-xz.typ`](./examples/03-on-xz/03-on-xz.typ).
