# `rect-around()` — Bounding Rectangle of Children

Draws an axis-aligned bounding box around all given points or elements.
Otherwise styled and anchored exactly like [`rect`](./11-rect.md).

## Signature

```text
rect-around(
  ..pts-style: coordinate | style,
)
```

## Parameters

- **`..pts-style`** — two or more coordinates and/or element references whose
  combined bounding box should be drawn. Style key-value pairs may be mixed
  in by name.
- **`padding`** *(style)* — extra margin around the computed bounding box.
- All other style keys (`fill`, `stroke`, `radius`, …) are forwarded to the
  underlying `rect`.

## Styling

- **Root:** `rect`

## Anchors

Same as [`rect`](./11-rect.md).

## Example

See [`examples/18-rect-around/18-rect-around.typ`](./examples/18-rect-around/18-rect-around.typ).

## Related

- [`rect`](./11-rect.md) — sibling shape with explicit corners
- [`internals/aabb`](../internals/aabb/00-aabb-overview.md) — the
  bounding-box engine (`aabb`, `mid`, `corner-points`, `size`, `padded`)
- [`util.as-padding-dict`](../internals/util/17-as-padding-dict.md) —
  normalises the `padding:` style
