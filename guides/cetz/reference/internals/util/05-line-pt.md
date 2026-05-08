# `util.line-pt()` — Point On A Line

Returns the point on the line segment `(a, b)` at parameter `t` —
`a + t·(b − a)`.

## Signature

```text
line-pt(a: vector, b: vector, t: float) -> vector
```

## Parameters

- **`a`** — start.
- **`b`** — end.
- **`t`** — interpolation parameter in `[0, 1]`.

## Example

See [`examples/05-line-pt/05-line-pt.typ`](./examples/05-line-pt/05-line-pt.typ).
