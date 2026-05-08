# `util.as-padding-dict()` — Normalize A Padding Spec

Coerces the various accepted padding forms — single number, 2-tuple
`(x, y)`, 4-tuple `(top, right, bottom, left)`, or dictionary — into a
canonical 4-key dictionary `(left, right, top, bottom)`.

## Signature

```text
as-padding-dict(padding: float | array | dictionary) -> dictionary
```

## Parameters

- **`padding`** — input padding spec.

## Example

See [`examples/17-as-padding-dict/17-as-padding-dict.typ`](./examples/17-as-padding-dict/17-as-padding-dict.typ).
