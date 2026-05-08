# `diamond` — rhombus

Rhombus shape — common decision-point in flow charts.

## Signature

```typst
diamond(node, extrude, fit: 0.5)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `fit` | `0.5` | How tightly the diamond fits the label. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [Choice], shape: diamond),
  node((1, 0), [Choice], shape: diamond.with(fit: 0)),
)
```

See [`examples/07-diamond/07-diamond.typ`](examples/07-diamond/07-diamond.typ).

## Pitfalls

- `fit: 0` makes the diamond merely *contain* the label's bounding box
  diagonally — usually too wide. `0.5` (default) is the visual sweet
  spot.
- Long labels can outgrow the diamond at `fit: 0.5`; raise it
  to `0.8` or wrap the label.
