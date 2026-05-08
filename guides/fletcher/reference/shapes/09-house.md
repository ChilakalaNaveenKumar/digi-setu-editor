# `house` — pentagonal house

Rectangle with a pitched-roof pentagonal top.

## Signature

```typst
house(
  node, extrude,
  dir:   top,
  angle: 10deg,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `dir` | `top` | Direction of the roof. |
| `angle` | `10deg` | Slant of the roof; `0deg` is a rectangle. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [Roof], shape: house),
  node((1, 0), [Tall roof], shape: house.with(angle: 30deg)),
)
```

See [`examples/09-house/09-house.typ`](examples/09-house/09-house.typ).

## Pitfalls

- The roof angle adds height to the bounding box; `angle: 90deg` is a
  documentation joke, but `45deg` is already taller than most layouts
  expect.
- Roof on `dir: left` / `dir: right` is rare in flow charts but works
  the same way.
