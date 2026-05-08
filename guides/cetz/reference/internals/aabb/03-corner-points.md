# `aabb.corner-points()` — Corner Vertices Of Bounds

Returns the corner vertices of a bounding box. With `front: true` only
the front face (z = high.z) corners are returned; with `front: false`
both faces are returned.

## Signature

```text
corner-points(bounds: bounds, front: bool = true) -> array
```

## Parameters

- **`bounds`** — bounds dictionary.
- **`front`** — `true` returns only the front face's 4 corners; `false`
  returns all 8.

## Example

See [`examples/03-corner-points/03-corner-points.typ`](./examples/03-corner-points/03-corner-points.typ).
