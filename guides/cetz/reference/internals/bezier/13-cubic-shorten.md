# `bezier.cubic-shorten()` — Accurate Arc-Length Shortening

Shortens a cubic Bézier curve by `d` units of arc length and returns a
new cubic curve that ends `d` units short of the input. Slower but more
accurate than `cubic-shorten-linear`.

## Signature

```text
cubic-shorten(s: vector, e: vector, c1: vector, c2: vector, d: float, samples: int = 15) -> (s, e, c1, c2)
```

## Parameters

- **`s`**, **`e`**, **`c1`**, **`c2`** — control points.
- **`d`** — shortening distance.
- **`samples`** — arc-length sampling resolution.

## Example

See [`examples/13-cubic-shorten/13-cubic-shorten.typ`](./examples/13-cubic-shorten/13-cubic-shorten.typ).
