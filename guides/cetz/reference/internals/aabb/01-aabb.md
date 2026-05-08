# `aabb.aabb()` — Build A Bounding Box

Computes the axis-aligned bounding box that encloses an array of points.

## Signature

```text
aabb(pts: array, init: bounds | none = none) -> bounds
```

## Parameters

- **`pts`** — points to enclose.
- **`init`** — optional starting bounds; the result encloses these too.

## Example

See [`examples/01-aabb/01-aabb.typ`](./examples/01-aabb/01-aabb.typ).
