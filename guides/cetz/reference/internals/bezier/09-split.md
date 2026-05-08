# `bezier.split()` — Split A Cubic At `t`

Splits a cubic Bézier curve `(s, e, c1, c2)` at parameter `t` into two
new cubic curves that, joined head-to-tail, reproduce the original.

## Signature

```text
split(s: vector, e: vector, c1: vector, c2: vector, t: float) -> (left, right)
```

Each `left`/`right` is a 4-tuple `(s, e, c1, c2)`.

## Parameters

Same as `cubic-point` plus `t` (split parameter).

## Example

See [`examples/09-split/09-split.typ`](./examples/09-split/09-split.typ).
