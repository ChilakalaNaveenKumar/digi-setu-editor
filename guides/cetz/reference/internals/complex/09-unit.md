# `complex.unit()` — Unit Vector

Returns a unit vector in the direction of a complex number — i.e.
`V / |V|`.

## Signature

```text
unit(V: complex) -> vector
```

## Parameters

- **`V`** — a complex number.

## Reference implementation

```typst
#let norm(V)     = calc.sqrt(V.at(0) * V.at(0) + V.at(1) * V.at(1))
#let unit(V)     = (V.at(0) / norm(V), V.at(1) / norm(V))
```

## Example

See [`examples/09-unit/09-unit.typ`](./examples/09-unit/09-unit.typ).
