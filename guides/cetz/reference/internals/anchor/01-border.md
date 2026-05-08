# `anchor.border()` — Border Anchor Resolver

Returns a *function* that resolves a border anchor (e.g. `"north-east"`,
`"east"`, an angle) to a 3-vector on the boundary of a shape, given the
shape's centre, half-extents, drawables and rotation.

## Signature

```text
border(center: vector, x-dist: float, y-dist: float, drawables: array, angle: angle) -> function
```

## Parameters

- **`center`** — bounding-box centre.
- **`x-dist`**, **`y-dist`** — half-width and half-height of the bounding
  box.
- **`drawables`** — list of the shape's drawables (used for `path:` style
  anchor queries).
- **`angle`** — rotation angle.

## Example

User code interacts with this through ordinary anchor lookups; the
function itself is internal — see
[`examples/01-border/01-border.typ`](./examples/01-border/01-border.typ).
