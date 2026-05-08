# `set-transform()` — Replace the Transformation Matrix

Overwrites the current transformation matrix with the given one. Pass `none`
to reset to identity (`matrix.ident(4)`).

## Signature

```text
set-transform(
  mat: none | matrix,
)
```

## Parameters

- **`mat`** — a 4 × 4 matrix, or `none`.

## Pitfalls

- Replaces the matrix completely. To stack a new transformation on top, use
  [`transform`](./02-transform.md) instead.
- Inside a `group` / `scope`, the change reverts when the scope exits.

## Example

See [`examples/01-set-transform/01-set-transform.typ`](./examples/01-set-transform/01-set-transform.typ).
