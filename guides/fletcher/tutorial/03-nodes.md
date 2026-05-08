# 3 — Nodes

`node(coord, label, ..options)` draws a labelled point at `coord`.
Nodes auto-size to their label (with a default `inset`), but may be
given an explicit `width`, `height`, `radius`, `fill`, or `stroke`.

## Basic options

```typst
#diagram(
  node((0,0), $f$),
  node((1,0), $f$, stroke: 1pt),
  node((2,0), $f$, stroke: blue, shape: rect),
  node((3,0), $f$, stroke: 1pt, radius: 6mm, extrude: (0, 3)),
)
```

| Option | Effect |
| ------ | ------ |
| `inset` | Padding between label and outline. |
| `outset` | How close edges connect to the outline (no layout effect). |
| `fill`, `stroke` | Standard. |
| `width`, `height`, `radius` | Force a size. |
| `extrude` | Multi-stroke offsets `(0, 2)` for double outlines. |
| `shape` | `rect`, `circle`, or any `fletcher.shapes.*`. |
| `corner-radius` | Rounded corners (when shape supports it). |
| `name: <label>` | Address this node from edges and other coords. |

## Node shapes

```typst
#import fletcher.shapes: pill, parallelogram, diamond, hexagon

#diagram(
  node-fill: blue.lighten(80%),
  node-stroke: blue,
  node((0,0), [Pill],         shape: pill),
  node((1,0), [Slant],        shape: parallelogram.with(angle: 20deg)),
  node((0,1), [Choice],       shape: diamond),
  node((1,1), [Stop],         shape: hexagon),
)
```

The `fletcher.shapes` submodule defines `rect`, `circle`, `ellipse`,
`pill`, `parallelogram`, `trapezium`, `diamond`, `triangle`, `house`,
`chevron`, `hexagon`, `octagon`, `cylinder`, plus the
`stretched-glyph`, `brace`, `bracket`, `paren` shapes for use with
node groups.

## Node groups (`enclose:`)

```typst
#diagram(
  node-stroke: 0.6pt,
  node((0,1), [X]),
  node((1,0), [Y], name: <y>),
  node($Sigma$, enclose: ((0,1), <y>),
    stroke: teal, fill: teal.lighten(90%), name: <group>),
  node((2.5, 0.5), [Z], name: <z>),
  edge(<group>, <z>, "->"),
)
```

`enclose:` accepts an array of coordinates and/or named anchors. The
node grows to wrap them.

## Node anchors

If a node has a `name:`, you can address its compass anchors:

| Anchor | Equivalent |
| ------ | ---------- |
| `<A.north>` | `(name: "A", anchor: "north")` |
| `<A.south-east>` | top-right of `A` |
| `<A.center>` | label centre |

These count as **absolute** coords (floating).

See [`examples/03-nodes/03-nodes.typ`](examples/03-nodes/03-nodes.typ).

## Pitfalls

- `width` / `height` are *forced* sizes; the label is centred unless
  you wrap it in `align(...)`.
- `extrude: (0, 2)` draws *two* strokes — at offset 0 and 2 thickness
  units. Just `(2,)` would draw only the outer one.
- `enclose:` makes the node act as a **group**; its `pos` is
  recomputed to the centroid of the enclosed points and stops affecting
  layout.
- Custom shapes are functions `(node, extrude, ..) => content` — see
  [`reference/shapes/`](../reference/shapes/00-shapes-overview.md) for
  signatures.

## Next

[`04-edges.md`](04-edges.md) — `edge()` vertices, snap, types.
