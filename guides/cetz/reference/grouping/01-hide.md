# `hide()` — Hide an Element

Hides an element so it isn't drawn. Useful for construction geometry that
should still be available for [`intersections`](./03-intersections.md) or
anchor queries.

## Signature

```text
hide(
  body:   element,
  bounds: bool = false,
)
```

## Parameters

- **`body`** — one or more elements to hide.
- **`bounds`** — when `true`, the hidden element's bounding box still
  affects canvas resizing. Default `false` (hidden elements are removed
  from the bounding box too).

## Pitfalls

- Hidden elements are **discarded** by [`merge-path`](../shapes/17-merge-path.md)
  unless you set `merge-path(..., ignore-hidden: false, ...)`.
- All other behaviours of the wrapped element (anchors, intersections, name)
  remain.

## Example

See [`examples/01-hide/01-hide.typ`](./examples/01-hide/01-hide.typ).
