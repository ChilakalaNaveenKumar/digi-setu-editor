# `cetz.tree.tree()` — Lay Out and Render a Tree

Lays out and renders tree nodes from a nested-array description.

For each node, the function creates an anchor of the form
`"[<child-index>-]<child-index>"` (root is `"0"`, its first child `"0-0"`,
second `"0-1"`, …) so you can attach further geometry by node position.

## Signature

```text
cetz.tree.tree(
  root:              array,
  draw-node:         auto | function,
  draw-edge:         none | auto | function,
  direction:         str   = "down",
  grow:              float = 1,
  spread:            float = 1,
  name:              none | str = none,
  node-layer:        int   = 0,
  edge-layer:        int   = 0,
  measure-content:   ,
  anchor:            none | string = none,
  group-name-prefix: string = "",
)
```

## Parameters

- **`root`** — nested array. `([root], [child 1], ([child 2], [grandchild
  1]))`.
- **`draw-node`** — `(node) => elements` to render a node. `auto` draws the
  node's content at the origin via
  [`default-draw-node`](./02-default-draw-node.md).
- **`draw-edge`** — `(parent, child) => elements`. `auto` draws a straight
  line ([`default-draw-edge`](./01-default-draw-edge.md)). `none` disables
  edges.
- **`direction`** — `"down"`, `"up"`, `"left"`, `"right"`.
- **`grow`** — depth grow factor.
- **`spread`** — sibling spread factor.
- **`name`** — element name.
- **`node-layer`** / **`edge-layer`** — draw layer (see
  [`on-layer`](../../grouping/11-on-layer.md)).
- **`anchor`** — name of the anchor to align the tree to (use `"0"` to
  align by the root node's position).
- **`group-name-prefix`** — string to prefix every node's group name with.

## Node fields

The `node` dictionary passed to callbacks has keys:

| Key | Type | Meaning |
| --- | ---- | ------- |
| `name` | `str` | Anchor name |
| `group-name` | `str` | Group element name |
| `depth` | `int` | Depth (root = 0) |
| `n` | `int` | Sibling index |
| `content` | `any` | Node value |

## Example

See [`examples/03-tree/03-tree.typ`](./examples/03-tree/03-tree.typ).
