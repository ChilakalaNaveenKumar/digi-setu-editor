# `path-util.shorten-to()` — Shorten A Path

Returns a new path that is shorter by `distance` units of arc length —
trimmed from the end (or the start if `reverse: true`). This is the
operation used to make room for a mark.

## Signature

```text
shorten-to(path: array, distance: float, reverse: bool = false, mode: str = "CURVED") -> array
```

## Parameters

- **`path`** — array of subpaths.
- **`distance`** — arc length to remove.
- **`reverse`** — if `true`, trim from the start instead of the end.
- **`mode`** — either `"CURVED"` (preserve curvature) or `"LINEAR"` (use
  linear shortening, fastest path).

## Example

See [`examples/11-shorten-to/11-shorten-to.typ`](./examples/11-shorten-to/11-shorten-to.typ).
