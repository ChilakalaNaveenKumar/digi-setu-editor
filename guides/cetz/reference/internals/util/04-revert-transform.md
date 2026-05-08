# `util.revert-transform()` — Inverse-Multiply Vectors

Equivalent to `apply-transform(matrix.inverse(transform), ..vecs)` —
reverses the effect of a transformation on each input vector.

## Signature

```text
revert-transform(transform: matrix, ..vecs: vector) -> vector | array
```

## Parameters

- **`transform`** — 4×4 matrix.
- **`..vecs`** — one or more vectors.

## Example

See [`examples/04-revert-transform/04-revert-transform.typ`](./examples/04-revert-transform/04-revert-transform.typ).
