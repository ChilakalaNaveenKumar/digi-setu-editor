# `vector.norm()` — Normalize

Returns a unit-length vector pointing in the same direction.

## Signature

```text
norm(v: vector) -> vector
```

## Parameters

- **`v`** — vector to normalize.

## Pitfalls

- The zero vector cannot be normalized — `len(v) == 0` causes a division
  by zero.

## Example

See [`examples/10-norm/10-norm.typ`](./examples/10-norm/10-norm.typ).
