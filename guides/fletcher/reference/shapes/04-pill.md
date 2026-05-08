# `pill` — capsule

Capsule (stadium) shape — rectangle with full-height rounded sides.

## Signature

```typst
pill(node, extrude)
```

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [Status: OK], shape: pill, fill: green.lighten(80%)),
)
```

See [`examples/04-pill/04-pill.typ`](examples/04-pill/04-pill.typ).

## Pitfalls

- `pill` is `circle` when `width == height`. For perfect circles, use
  `shape: circle` for clarity.
- The end caps ignore `corner-radius` — they always span the full
  height.
