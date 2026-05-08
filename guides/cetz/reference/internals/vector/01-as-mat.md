# `vector.as-mat()` — Vector → Matrix

Converts a vector into a matrix (2D array) — by default a single-row matrix.

## Signature

```text
as-mat(v: vector, mode: "row" | "column" = "row") -> array
```

## Parameters

- **`v`** — the vector to wrap.
- **`mode`** — `"row"` for a 1×N matrix, `"column"` for an N×1 matrix.

## Example

See [`examples/01-as-mat/01-as-mat.typ`](./examples/01-as-mat/01-as-mat.typ).
