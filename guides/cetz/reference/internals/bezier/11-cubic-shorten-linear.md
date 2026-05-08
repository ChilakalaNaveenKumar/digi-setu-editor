# `bezier.cubic-shorten-linear()` — Quick Linear Shortening

Shortens a cubic Bézier curve by `d` units using a fast linear estimate
of the start/end tangents — produces a less accurate but cheaper result
than `cubic-shorten`.

## Signature

```text
cubic-shorten-linear(s: vector, e: vector, c1: vector, c2: vector, d: float) -> (s, e, c1, c2)
```

## Parameters

- **`s`**, **`e`**, **`c1`**, **`c2`** — control points.
- **`d`** — shortening distance. Positive shortens at the end; negative
  shortens at the start.

## Example

See [`examples/11-cubic-shorten-linear/11-cubic-shorten-linear.typ`](./examples/11-cubic-shorten-linear/11-cubic-shorten-linear.typ).
