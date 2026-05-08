# Main functions — overview

Fletcher's public surface is just three functions. Everything else
(shapes, marks, internals) is layered on top.

| Page | Function | Purpose |
| ---- | -------- | ------- |
| [`01-diagram.md`](01-diagram.md) | `diagram(..)` | The envelope. Sets defaults for spacing, axes, edges, nodes. |
| [`02-node.md`](02-node.md) | `node(coord, label, ..)` | A labelled point with a shape. |
| [`03-edge.md`](03-edge.md) | `edge(..vertices, marks, label, ..)` | A connecting arrow / line / curve. |

## Tip: pass children as separate args **or** in blocks

```typst
#diagram(
  node((0, 0), $A$),
  node((1, 0), $B$),
  {
    node((2, 0), $C$)
    node((3, 0), $D$)
  },
  for x in range(4) { node((x, 1), [#x]) },
)
```

Both forms are joined; you can mix them freely.

## Math-mode shorthand

```typst
#diagram($
  A & B \
  C edge(->) & D
$)
```

In math mode, identifiers become nodes at successive coordinates and
`edge(->)` calls become edges between them. Useful for inline diagrams.
