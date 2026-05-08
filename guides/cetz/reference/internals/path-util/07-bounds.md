# `path-util.bounds()` — Bounding Points Of A Path

Returns the array of points that contribute to the path's axis-aligned
bounding box — every line endpoint plus the cubic extrema. Feed the
result to `aabb.aabb(...)` to obtain a `(low, high)` pair.

## Signature

```text
bounds(path: array) -> array
```

## Parameters

- **`path`** — array of subpaths.

## Example

See [`examples/07-bounds/07-bounds.typ`](./examples/07-bounds/07-bounds.typ).
