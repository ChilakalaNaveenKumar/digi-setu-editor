# `vector-polar-with-xy-or-uv-length(grid, xy, target-length, θ)`

A polar offset that lets you specify length **either** in elastic units
(`uv`) **or** in absolute units (`xy`), so you can mix expressive
nudges with grid-aware ones.

## Signature

```typst
vector-polar-with-xy-or-uv-length(
  grid: dict,
  xy:   (length, length),         // base point
  target-length: length | float,  // length OR uv units
  θ:    angle,
) -> (length, length)
```

If `target-length` is a `length`, the result is a polar offset of
exactly that physical length at angle `θ`.

If `target-length` is a `float` / unit-less number, it is interpreted as
*uv* units along the direction `θ`, then converted to xy through
[`duv-to-dxy`](03-duv-to-dxy.md).

## Example

```typst
let p1 = (10pt, 0pt)
// 5pt physical to the upper-right
let off-xy = fletcher.vector-polar-with-xy-or-uv-length(grid, p1, 5pt, 45deg)
// 0.5 elastic units to the upper-right (size depends on grid spacing)
let off-uv = fletcher.vector-polar-with-xy-or-uv-length(grid, p1, 0.5, 45deg)
```

See [`examples/05-vector-polar/05-vector-polar.typ`](examples/05-vector-polar/05-vector-polar.typ).

## Pitfalls

- For unit-less arguments the helper depends on the local grid
  geometry — the *physical* length will differ across cells.
- Always pass an `angle`, not a number.

## Related

- [`duv-to-dxy`](03-duv-to-dxy.md) (does the conversion under the hood)
- [`uv-to-xy`](01-uv-to-xy.md)
