# `complex.conj()` — Complex Conjugate

Returns the conjugate `V̄` of a complex number — same real part, negated
imaginary part.

## Signature

```text
conj(V: complex) -> complex
```

## Parameters

- **`V`** — a complex number.

## Reference implementation

```typst
#let conj(V) = (V.at(0), -V.at(1))
```

## Example

See [`examples/04-conj/04-conj.typ`](./examples/04-conj/04-conj.typ).
