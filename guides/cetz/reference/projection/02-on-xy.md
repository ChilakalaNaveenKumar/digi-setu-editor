# `on-xy()` — Draw on the XY Plane

Draws elements on the **xy-plane** with an optional `z` offset.

All vertices of all elements are mapped `(x, y) → (x, y, z_argument)` —
i.e. the body draws in 2-D and the `z` parameter chooses the depth.

## Signature

```text
on-xy(
  z:    number = 0,
  body: element,
)
```

## Parameters

- **`z`** — z offset for all coordinates in the body.
- **`body`** — elements to draw.

## Example

See [`examples/02-on-xy/02-on-xy.typ`](./examples/02-on-xy/02-on-xy.typ).
