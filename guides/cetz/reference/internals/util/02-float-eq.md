# `util.float-eq()` — Approximate Equality

Returns `true` if two numbers are equal within `epsilon`. Uses
`util.float-epsilon` by default.

## Signature

```text
float-eq(a: float, b: float, epsilon: float = util.float-epsilon) -> bool
```

## Parameters

- **`a`**, **`b`** — operands.
- **`epsilon`** — tolerance.

## Example

See [`examples/02-float-eq/02-float-eq.typ`](./examples/02-float-eq/02-float-eq.typ).
