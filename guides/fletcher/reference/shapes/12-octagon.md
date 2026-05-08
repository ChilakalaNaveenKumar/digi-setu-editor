# `octagon` — truncated rectangle

Rectangle with the four corners truncated.

## Signature

```typst
octagon(
  node, extrude,
  truncate: 0.5,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `truncate` | `0.5` | Size of the truncated corners. A number is a multiple of `min(width, height)`; a length is absolute. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [STOP],     shape: octagon),
  node((1, 0), [tiny cuts], shape: octagon.with(truncate: 0.1)),
  node((2, 0), [big cuts],  shape: octagon.with(truncate: 0.4)),
)
```

See [`examples/12-octagon/12-octagon.typ`](examples/12-octagon/12-octagon.typ).

## Pitfalls

- `truncate: 1` collapses opposite corners to a diamond.
- An absolute length truncate (e.g. `5pt`) is absolute regardless of
  node size — useful for grid-aligned octagons.
