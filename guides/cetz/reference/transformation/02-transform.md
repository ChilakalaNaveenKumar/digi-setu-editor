# `transform()` — Stack a Transformation Matrix

Applies a 4 × 4 transformation matrix on top of the current transformation.

Given the current transformation `C` and the new transformation `T`,
`transform` sets the new canvas transform to `C' = C * T`.

## Signature

```text
transform(
  mat: none | matrix,
)
```

## Parameters

- **`mat`** — a 4 × 4 matrix, or `none` (resets to identity).

## See also

- [`rotate`](./03-rotate.md), [`translate`](./04-translate.md),
  [`scale`](./05-scale.md) — common matrices built for you.
- [`internals/matrix/`](../internals/matrix/) — raw matrix builders.

## Example

See [`examples/02-transform/02-transform.typ`](./examples/02-transform/02-transform.typ).
