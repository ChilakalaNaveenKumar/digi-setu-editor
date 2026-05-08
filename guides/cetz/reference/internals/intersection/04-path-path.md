# `intersection.path-path()` — Path × Path Intersection

Returns the intersection points between two arbitrary paths. Internally
walks both paths segment-by-segment and dispatches to `line-line`,
`line-cubic`, or a sampled cubic-cubic search.

## Signature

```text
path-path(a: array, b: array, samples: int = 8) -> array
```

## Parameters

- **`a`**, **`b`** — path segment arrays.
- **`samples`** — sub-sampling resolution for cubic × cubic intersections.

## Example

See [`examples/04-path-path/04-path-path.typ`](./examples/04-path-path/04-path-path.typ).
