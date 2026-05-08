# `util.resolve-radius()` — Normalize A Radius

Coerces the various accepted "radius" forms — single number, 2-tuple
`(rx, ry)` — into the canonical `(rx, ry)` 2-tuple.

## Signature

```text
resolve-radius(radius: float | (float, float)) -> (float, float)
```

## Parameters

- **`radius`** — radius input.

## Example

See [`examples/12-resolve-radius/12-resolve-radius.typ`](./examples/12-resolve-radius/12-resolve-radius.typ).
