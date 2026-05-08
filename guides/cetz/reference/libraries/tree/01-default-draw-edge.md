# `cetz.tree.default-draw-edge()` — Default Edge Renderer

Default edge-drawing callback used by [`cetz.tree.tree`](./03-tree.md) when
no custom `draw-edge:` is supplied. Draws a straight line between the parent
and child group elements.

## Signature

```text
cetz.tree.default-draw-edge(
  parent: node,
  child:  node,
)
```

## Parameters

- **`parent`** — parent tree node. Field `group-name` (`str`) is the
  parent element's name.
- **`child`** — child tree node. Same fields as `parent`.

## Use case

Wrap and customise inside a custom `draw-edge:` callback if you only want to
adjust styling around the default behaviour:

```typst
draw-edge: (p, c) => {
  set-style(stroke: 1pt + gray)
  cetz.tree.default-draw-edge(p, c)
}
```

(no separate runnable example — it's a building block.)
