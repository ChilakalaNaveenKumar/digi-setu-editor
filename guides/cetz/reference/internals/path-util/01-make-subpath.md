# `path-util.make-subpath()` — Build A Subpath

Constructs a single subpath triple `(origin, segments, closed)` suitable
for feeding into `drawable.path`.

## Signature

```text
make-subpath(origin: vector, segments: array, closed: bool = false) -> subpath
```

## Parameters

- **`origin`** — start point of the subpath.
- **`segments`** — list of `("l", point)` line or `("c", c1, c2, end)`
  cubic segments.
- **`closed`** — whether the subpath closes back to its origin.

## Example

See [`examples/01-make-subpath/01-make-subpath.typ`](./examples/01-make-subpath/01-make-subpath.typ).
