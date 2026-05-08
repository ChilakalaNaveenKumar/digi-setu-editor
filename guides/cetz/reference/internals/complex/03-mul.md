# `complex.mul()` — Complex Multiplication

Multiplies two complex numbers and returns the result `V * W`.

## Signature

```text
mul(V: complex, W: complex) -> complex
```

## Parameters

- **`V`** — left-hand operand.
- **`W`** — right-hand operand.

## Reference implementation

```typst
#let mul(V, W) = (
  V.at(0) * W.at(0) - V.at(1) * W.at(1),
  V.at(1) * W.at(0) + V.at(0) * W.at(1),
)
```

## Example

See [`examples/03-mul/03-mul.typ`](./examples/03-mul/03-mul.typ).
