# `matrix.inverse()` — Matrix Inverse

Returns the inverse of a square matrix using a fast WASM solver. CeTZ uses
this internally for un-projecting input coordinates and other reverse
operations.

## Signature

```text
inverse(matrix: matrix) -> matrix
```

## Parameters

- **`matrix`** — square matrix.

## Pitfalls

- Singular matrices have no inverse — calling `inverse(...)` on one will
  raise an assertion.

## Example

See [`examples/21-inverse/21-inverse.typ`](./examples/21-inverse/21-inverse.typ).
