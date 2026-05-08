# `cetz.tree.default-draw-node()` — Default Node Renderer

Default node-drawing callback used by [`cetz.tree.tree`](./03-tree.md) when
no custom `draw-node:` is supplied. Draws the node's `content` value as
plain content at the (auto-computed) position.

## Signature

```text
cetz.tree.default-draw-node(
  node: node,
)
```

## Parameters

- **`node`** — the node dictionary, with keys:
  - `name` (`str`) — anchor name for this node.
  - `group-name` (`str`) — group element name.
  - `depth` (`int`) — depth in the tree (root is `0`).
  - `n` (`int`) — sibling index.
  - `content` (`any`) — the node's value.

## Use case

Wrap inside a custom `draw-node:` callback for boxed / coloured nodes:

```typst
draw-node: node => {
  rect((-.4, -.3), (.4, .3), fill: aqua.lighten(70%))
  cetz.tree.default-draw-node(node)
}
```

See [`03-tree.md`](./03-tree.md) for a full example.
