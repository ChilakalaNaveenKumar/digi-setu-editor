# `trapezium` — isosceles trapezium

Trapezium with the shorter parallel side on a chosen direction.

## Signature

```typst
trapezium(
  node, extrude,
  dir:   top,
  angle: 20deg,
  fit:   0.8,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `dir` | `top` | Side the shorter parallel edge is on (`top`, `bottom`, `left`, `right`). |
| `angle` | `20deg` | Slant angle. |
| `fit` | `0.8` | How tightly to hug the label. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [Funnel],     shape: trapezium.with(dir: bottom)),
  node((1, 0), [Spread Out], shape: trapezium.with(dir: top, angle: 30deg)),
)
```

See [`examples/06-trapezium/06-trapezium.typ`](examples/06-trapezium/06-trapezium.typ).

## Pitfalls

- For a `dir: left` / `dir: right` trapezium with a wide label, the
  slant compresses the long edge — increase `fit` or the slant becomes
  invisible.
- Same `angle: 90deg` warning as parallelogram — keep below 60deg.
