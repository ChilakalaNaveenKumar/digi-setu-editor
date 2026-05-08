# `util.apply-transform()` — Multiply Vectors By Transform

Applies a 4×4 transform to one or more 3-vectors. Returns either a single
vector (when called with one) or an array (when called with several).

## Signature

```text
apply-transform(transform: matrix, ..vecs: vector) -> vector | array
```

## Parameters

- **`transform`** — 4×4 matrix.
- **`..vecs`** — one or more vectors.

## Example

See [`examples/03-apply-transform/03-apply-transform.typ`](./examples/03-apply-transform/03-apply-transform.typ).
