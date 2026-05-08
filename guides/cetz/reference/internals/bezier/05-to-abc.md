# `bezier.to-abc()` — Compute Bézier "ABC" Helper Points

Returns the ratio between the *abc* helper points used by the
"Bézier-through-3-points" construction. Given a desired through-point `B`
at parameter `t`, `to-abc(s, e, B, t, deg)` produces the auxiliary
`A`/`C` triangle the algorithm needs to compute the off-curve control
points.

## Signature

```text
to-abc(s: vector, e: vector, B: vector, t: float, deg: int = 2) -> dictionary
```

## Parameters

- **`s`** — start point.
- **`e`** — end point.
- **`B`** — point the curve must pass through at parameter `t`.
- **`t`** — parameter at which `B` lies.
- **`deg`** — curve degree (`2` quadratic, `3` cubic).

## Example

See [`examples/05-to-abc/05-to-abc.typ`](./examples/05-to-abc/05-to-abc.typ).
