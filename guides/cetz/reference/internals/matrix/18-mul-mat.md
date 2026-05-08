# `matrix.mul-mat()` — Matrix Product

Multiplies an arbitrary number of matrices left-to-right —
`mul-mat(A, B, C) == A * B * C`.

## Signature

```text
mul-mat(..matrices: matrix) -> matrix
```

## Parameters

- **`..matrices`** — variadic positional matrices; all must have
  compatible dimensions.

## Example

See [`examples/18-mul-mat/18-mul-mat.typ`](./examples/18-mul-mat/18-mul-mat.typ).
