# `matrix.diag()` — Diagonal Matrix

Builds a diagonal matrix from the supplied scalars — `diag(a, b, c)`
returns a 3×3 matrix with `a`, `b`, `c` on the main diagonal.

## Signature

```text
diag(..diag: float) -> matrix
```

## Parameters

- **`..diag`** — variadic positional scalars placed on the diagonal.

## Pitfalls

- **Broken in cetz 0.5.0.** The implementation contains a typo
  (`messaged:` instead of `message:`) inside an `assert.eq` call, which
  causes any invocation to fail. The example file therefore re-implements
  `diag` in plain Typst.

## Example

See [`examples/02-diag/02-diag.typ`](./examples/02-diag/02-diag.typ).
