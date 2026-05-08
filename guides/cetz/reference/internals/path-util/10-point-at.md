# `path-util.point-at()` — Point At Distance

Returns the point on the path at the given arc-length distance from the
start (or from the end if `reverse: true`).

## Signature

```text
point-at(path: array, distance: float, reverse: bool = false, samples: int | auto = auto, ignore-subpaths: bool = true) -> vector
```

## Parameters

- **`path`** — array of subpaths.
- **`distance`** — distance from the starting end.
- **`reverse`** — if `true`, measure from the end of the path.
- **`samples`** — sampling resolution.
- **`ignore-subpaths`** — if `true`, treat the path as one continuous
  curve regardless of subpath breaks.

## Example

See [`examples/10-point-at/10-point-at.typ`](./examples/10-point-at/10-point-at.typ).
