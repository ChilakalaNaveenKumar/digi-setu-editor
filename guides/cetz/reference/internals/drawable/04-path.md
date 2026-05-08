# `drawable.path()` — Generic Path Drawable

Constructs a generic path drawable from one or more *segments*. Each
segment is a tuple beginning with the segment kind (`"line"`, `"cubic"`)
followed by its control vectors.

## Signature

```text
path(
  fill: color | none = none,
  stroke: stroke | none = none,
  fill-rule: "non-zero" | "even-odd" = "non-zero",
  tags: array = (),
  path: array,
) -> drawable
```

## Parameters

- **`fill`**, **`stroke`**, **`fill-rule`** — render options.
- **`tags`** — array of tag names.
- **`path`** — an array of *subpaths*. Each subpath is the triple
  `(origin, closed, segments)` where `segments` is an array of
  `("l", point)` (line) or `("c", c1, c2, end)` (cubic) tuples.

## Example

See [`examples/04-path/04-path.typ`](./examples/04-path/04-path.typ).
