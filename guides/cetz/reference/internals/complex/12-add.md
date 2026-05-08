# `complex.add()` — Addition

Adds two complex numbers — `(V.re + W.re, V.im + W.im)`.

## Signature

```text
add(V: complex, W: complex) -> complex
```

## Parameters

- **`V`**, **`W`** — operands.

## Reference implementation

```typst
#let add(V, W) = (V.at(0) + W.at(0), V.at(1) + W.at(1))
```

## Example

See [`examples/12-add/12-add.typ`](./examples/12-add/12-add.typ).
