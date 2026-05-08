# `complex.norm()` — Norm (Magnitude)

Calculates the norm `|V| = √(re² + im²)` of a complex number.

## Signature

```text
norm(V: complex) -> float
```

## Parameters

- **`V`** — a complex number.

## Reference implementation

```typst
#let norm(V) = calc.sqrt(V.at(0) * V.at(0) + V.at(1) * V.at(1))
```

## Example

See [`examples/07-norm/07-norm.typ`](./examples/07-norm/07-norm.typ).
