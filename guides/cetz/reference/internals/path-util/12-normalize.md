# `path-util.normalize()` — Normalise A Path

Returns a normalised path: empty subpaths removed, segments rounded to
the floating-point precision used elsewhere, and `("l", point)` /
`("c", c1, c2, end)` segment types canonicalised. This is what
`drawable.path` calls before storing the path.

## Signature

```text
normalize(path: array) -> array
```

## Parameters

- **`path`** — array of subpaths.

## Example

See [`examples/12-normalize/12-normalize.typ`](./examples/12-normalize/12-normalize.typ).
