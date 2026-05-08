# `complex.scale()` — Scalar Multiplication

Multiplies a complex number by a scalar `t` and returns the result.

## Signature

```text
scale(V: complex, t: float) -> complex
```

## Parameters

- **`V`** — the complex number to scale.
- **`t`** — the scale factor.

## Reference implementation

```typst
#let scale(V, t) = (V.at(0) * t, V.at(1) * t)
```

## Example

See [`examples/08-scale/08-scale.typ`](./examples/08-scale/08-scale.typ).
