# `path-util.length()` — Total Path Length

Returns the total arc length of the supplied segments — the sum of
`segment-lengths(path)`.

## Signature

```text
length(segments: array, samples: int | auto = auto) -> float
```

## Parameters

- **`segments`** — segment array (a path or a single subpath's segments).
- **`samples`** — sampling resolution for cubics.

## Example

See [`examples/09-length/09-length.typ`](./examples/09-length/09-length.typ).
