# `vector.angle()` — Angle At a Vertex

Returns the angle ∠v1‑c‑v2 at vertex `c` formed by vectors `v1` and `v2`.
Equivalent to `acos(dot(v1−c, v2−c) / (|v1−c|·|v2−c|))`.

## Signature

```text
angle(v1: vector, c: vector, v2: vector) -> angle
```

## Parameters

- **`v1`** — first ray endpoint.
- **`c`** — vertex.
- **`v2`** — second ray endpoint.

## Example

See [`examples/15-angle/15-angle.typ`](./examples/15-angle/15-angle.typ).
