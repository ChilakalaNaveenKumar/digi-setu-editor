# `floating()` — Draw Without Affecting Bounds

Places an element on the canvas but **excludes** it from the bounding-box
calculation. Useful for callouts, badges, or guide labels that shouldn't
push the canvas larger.

## Signature

```text
floating(
  body: element,
)
```

## Parameters

- **`body`** — one or more elements to place.

All other behaviours (anchors, intersections, naming) are unchanged.

## Example

See [`examples/02-floating/02-floating.typ`](./examples/02-floating/02-floating.typ).
