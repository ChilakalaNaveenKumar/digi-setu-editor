# `vector.as-vec()` — Pad To Length

Pads a 2-element vector to 3 elements (filling with `0`), or returns the
input unchanged if already long enough. Used by other vector functions to
accept both 2D and 3D inputs.

## Signature

```text
as-vec(v: array, init: array = (0, 0, 0)) -> array
```

## Parameters

- **`v`** — vector to coerce.
- **`init`** — fill values; defaults to `(0, 0, 0)`.

## Example

See [`examples/02-as-vec/02-as-vec.typ`](./examples/02-as-vec/02-as-vec.typ).
