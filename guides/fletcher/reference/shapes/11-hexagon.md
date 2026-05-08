# `hexagon` — irregular hexagon

A hexagon parameterised by half the exterior angle.

## Signature

```typst
hexagon(
  node, extrude,
  angle: 30deg,
  fit:   0.8,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `angle` | `30deg` | Half the exterior angle. `0deg` is a rectangle. |
| `fit` | `0.8` | How tightly to hug the label. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [Hex],   shape: hexagon),
  node((1, 0), [Wider], shape: hexagon.with(angle: 45deg)),
)
```

See [`examples/11-hexagon/11-hexagon.typ`](examples/11-hexagon/11-hexagon.typ).

## Pitfalls

- `angle: 0deg` produces a rectangle; `60deg` produces a regular
  hexagon (only when `width == height` — otherwise it stretches).
- For honeycomb layouts, set `node-shape: hexagon` and use
  `cell-size:` to control hex size precisely.
