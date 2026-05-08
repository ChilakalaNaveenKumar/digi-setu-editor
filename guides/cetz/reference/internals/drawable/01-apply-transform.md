# `drawable.apply-transform()` — Bake A Transform Into Drawables

Pre-multiplies a 4×4 transform into every point of every drawable in the
list — used internally to flatten transformations once they are no longer
inheritable.

## Signature

```text
apply-transform(transform: matrix, drawables: array) -> array
```

## Parameters

- **`transform`** — 4×4 affine matrix.
- **`drawables`** — array of drawable dictionaries.

## Example

See [`examples/01-apply-transform/01-apply-transform.typ`](./examples/01-apply-transform/01-apply-transform.typ).
