# `xy-to-uv(grid, xy)` — absolute → elastic

Inverse of [`uv-to-xy`](01-uv-to-xy.md). Convert from physical CeTZ
coordinates back to elastic row/column.

## Signature

```typst
xy-to-uv(grid: dict, xy: (length, length)) -> (float, float)
```

## Example

Inside a `render:` callback, compute which elastic cell a hand-drawn
shape falls inside:

```typst
let uv = fletcher.xy-to-uv(grid, (1.5cm, 0.7cm))
// uv now expresses the same point in row/column form
```

See [`examples/02-xy-to-uv/02-xy-to-uv.typ`](examples/02-xy-to-uv/02-xy-to-uv.typ).

## Pitfalls

- The result is fractional in general — it sits between rows and
  columns when the input doesn't land on a center.
- For points outside the grid, `xy-to-uv` extrapolates linearly using
  `spacing`; the result may be negative or exceed the largest row /
  column index.

## Related

- Inverse: [`uv-to-xy`](01-uv-to-xy.md)
- Tangent inverse: [`dxy-to-duv`](04-dxy-to-duv.md)
