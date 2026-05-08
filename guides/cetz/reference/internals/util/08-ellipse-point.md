# `util.ellipse-point()` — Point On An Ellipse

Returns the point on an ellipse at the given angle.

## Signature

```text
ellipse-point(center: vector, radius: float | (float, float), angle: angle) -> vector
```

## Parameters

- **`center`** — ellipse centre.
- **`radius`** — radius (single value for circle) or `(rx, ry)` for an
  ellipse.
- **`angle`** — sweep angle from the positive X axis.

## Example

See [`examples/08-ellipse-point/08-ellipse-point.typ`](./examples/08-ellipse-point/08-ellipse-point.typ).
