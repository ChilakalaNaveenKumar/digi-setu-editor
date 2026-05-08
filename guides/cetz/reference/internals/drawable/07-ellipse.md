# `drawable.ellipse()` — Ellipse Drawable

Constructs a low-level ellipse drawable. The `circle` and `circle-through`
shapes both eventually emit one.

## Signature

```text
ellipse(x: float, y: float, z: float, rx: float, ry: float, fill: color | none = none, stroke: stroke | none = none) -> drawable
```

## Parameters

- **`x`**, **`y`**, **`z`** — centre coordinates.
- **`rx`**, **`ry`** — radii along X and Y.
- **`fill`**, **`stroke`** — render options.

## Example

See [`examples/07-ellipse/07-ellipse.typ`](./examples/07-ellipse/07-ellipse.typ).
