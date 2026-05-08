# `complex.arg()` — Argument (Phase Angle)

Calculates the argument of a complex number — the angle from the positive
real axis (in radians, returned divided by `1rad` so the result is a unitless
float).

## Signature

```text
arg(V: complex) -> float
```

## Parameters

- **`V`** — a complex number.

## Reference implementation

```typst
#let arg(V) = calc.atan2(..V) / 1rad
```

## Example

See [`examples/14-arg/14-arg.typ`](./examples/14-arg/14-arg.typ).
