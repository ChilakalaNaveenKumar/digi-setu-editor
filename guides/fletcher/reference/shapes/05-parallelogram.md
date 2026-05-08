# `parallelogram` — slanted rectangle

A slanted rectangle. Useful for "input/output" boxes in flow charts.

## Signature

```typst
parallelogram(
  node, extrude, flip,
  angle: 20deg,
  fit:   0.8,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `angle` | `20deg` | Slant angle. `0deg` is a rectangle. |
| `fit` | `0.8` | How tightly the parallelogram hugs the label. `0` = perfect bounding rect, `1` = entire label barely fits inside. |
| `flip` | (positional) | If truthy, slant the other direction. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [In],  shape: parallelogram.with(angle: 30deg)),
  node((1, 0), [Out], shape: parallelogram.with(angle: 30deg, flip: true)),
)
```

See [`examples/05-parallelogram/05-parallelogram.typ`](examples/05-parallelogram/05-parallelogram.typ).

## Pitfalls

- `angle: 90deg` makes a parallelogram so wide it would crash your
  document — keep below 60deg.
- `fit: 0` produces a rectangle that *contains* the label diagonal —
  often visually too wide. Increase to `0.5` or `0.8` for a tight fit.
- `flip` is **positional** in the manual, but in this version of
  Fletcher you set it via `parallelogram.with(flip: true)`.
