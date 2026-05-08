# Tree Library — Overview

`cetz.tree` lays out and renders rooted trees from a nested-array description.

| Function | Purpose | Page |
| -------- | ------- | ---- |
| `cetz.tree.tree(root, ...)` | Layout-and-render | [`03-tree.md`](./03-tree.md) |
| `cetz.tree.default-draw-node(node)` | Default node-rendering callback | [`02-default-draw-node.md`](./02-default-draw-node.md) |
| `cetz.tree.default-draw-edge(parent, child)` | Default edge-rendering callback | [`01-default-draw-edge.md`](./01-default-draw-edge.md) |

## Conceptual model

`cetz.tree.tree(([root], [child 1], ([child 2], [grandchild 1])))` lays out
the nodes automatically. For each node, an anchor of the form
`"[<child-index>-]<child-index>"` is created on the tree element (root is
`"0"`, its first child `"0-0"`, second `"0-1"`, …). Use that anchor to
attach further geometry.

## Related

- [Types — `tree node`](../../../types/00-types-overview.md) — the
  dictionary shape passed to `draw-node` / `draw-edge` callbacks
- [`anchor`](../../grouping/06-anchor.md) — anchors created on tree nodes
