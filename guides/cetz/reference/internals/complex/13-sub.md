# `complex.sub()` — Subtraction

Subtracts two complex numbers — `(V.re − W.re, V.im − W.im)`.

## Signature

```text
sub(V: complex, W: complex) -> complex
```

## Parameters

- **`V`**, **`W`** — operands.

## Reference implementation

```typst
#let sub(V, W) = (V.at(0) - W.at(0), V.at(1) - W.at(1))
```

## Example

See [`examples/13-sub/13-sub.typ`](./examples/13-sub/13-sub.typ).
