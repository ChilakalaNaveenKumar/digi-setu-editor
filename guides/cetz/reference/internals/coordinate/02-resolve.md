# `coordinate.resolve()` — Resolve Coordinates To 3-Vectors

Resolves one or more coordinate expressions to their canonical 3-vector
representation, optionally updating the context's "previous coordinate".

## Signature

```text
resolve(ctx: dictionary, ..coordinates: any, update: bool = true) -> (dictionary, vector | array)
```

## Parameters

- **`ctx`** — the canvas context.
- **`..coordinates`** — one or more coordinate expressions in any of the
  CeTZ-supported forms.
- **`update`** — if `true`, the context's "previous coordinate" is updated
  to the last resolved point.

Returns the new context plus either a single vector (when one coordinate
was passed) or an array of vectors.

## Example

See [`examples/02-resolve/02-resolve.typ`](./examples/02-resolve/02-resolve.typ).
