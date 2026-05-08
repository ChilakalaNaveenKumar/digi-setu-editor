# `path-util.segment-lengths()` — Per-Segment Arc Lengths

Returns an array of per-segment arc lengths.

## Signature

```text
segment-lengths(path: array, samples: int | auto = auto) -> array
```

## Parameters

- **`path`** — array of subpaths.
- **`samples`** — sampling resolution for cubic-segment arc length;
  defaults to a sensible value.

## Example

See [`examples/08-segment-lengths/08-segment-lengths.typ`](./examples/08-segment-lengths/08-segment-lengths.typ).
