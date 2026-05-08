# `vector.lerp()` — Linear Interpolation

Linearly interpolates between two vectors — `v1 + t·(v2 − v1)`. `t = 0`
returns `v1`, `t = 1` returns `v2`.

## Signature

```text
lerp(v1: vector, v2: vector, t: float) -> vector
```

## Parameters

- **`v1`** — start.
- **`v2`** — end.
- **`t`** — interpolation parameter, typically in `[0, 1]`.

## Example

See [`examples/16-lerp/16-lerp.typ`](./examples/16-lerp/16-lerp.typ).
