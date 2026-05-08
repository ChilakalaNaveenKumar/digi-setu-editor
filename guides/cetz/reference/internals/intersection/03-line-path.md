# `intersection.line-path()` — Line × Path Intersection

Returns the intersection points between a line and an arbitrary
multi-segment path (a sequence of line/cubic subpaths produced by
`drawable.path` or `path-util`).

## Signature

```text
line-path(la: vector, lb: vector, path: array) -> array
```

## Parameters

- **`la`**, **`lb`** — line endpoints.
- **`path`** — path segment array.

## Example

See [`examples/03-line-path/03-line-path.typ`](./examples/03-line-path/03-line-path.typ).
