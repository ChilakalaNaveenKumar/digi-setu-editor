# `uv-to-xy(grid, uv)` — elastic → absolute

Convert from Fletcher's elastic (row/column) coordinates to absolute
(physical) coordinates in CeTZ space.

## Signature

```typst
uv-to-xy(grid: dict, uv: (float, float)) -> (length, length)
```

| Arg | Meaning |
| --- | ------- |
| `grid` | The grid dictionary (`origin`, `centers`, `spacing`, `flip`). Provided to `render:` callbacks. |
| `uv` | Elastic coordinate `(u, v)`, possibly fractional. |

## Example (inside a `render:` callback)

```typst
#diagram(
  node((0, 0), [A]),
  node((2, 1), [B]),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    // Draw a marker at the elastic centre between (0, 0) and (2, 1).
    let xy = fletcher.uv-to-xy(grid, (1, 0.5))
    fletcher.cetz.draw.circle(xy, radius: 3pt, fill: red)
  })
)
```

See [`examples/01-uv-to-xy/01-uv-to-xy.typ`](examples/01-uv-to-xy/01-uv-to-xy.typ).

## Pitfalls

- `uv-to-xy` returns physical lengths — pass them straight to CeTZ
  drawing functions.
- Fractional `uv` is supported and computed by linear interpolation
  between row / column positions.

## Related

- Inverse: [`xy-to-uv`](02-xy-to-uv.md)
- Tangent version: [`duv-to-dxy`](03-duv-to-dxy.md)
