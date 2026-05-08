# `resolve-node-enclosures(nodes, grid)` — expand `enclose:` lists

The `enclose:` argument on a node may take any number of coordinates,
node-keys, or named anchors. `resolve-node-enclosures` walks every
node and replaces those user inputs with **fully resolved** xy points
that the bounding-box calculator consumes.

## Signature

```typst
resolve-node-enclosures(
  nodes: array,    // post-measure nodes
  grid:  dict,     // computed grid
) -> array         // nodes with enclosures resolved
```

## Example (group via `enclose:`)

```typst
#diagram(
  node((0, 0), [A], name: <a>),
  node((2, 1), [B], name: <b>),
  node(enclose: (<a>, <b>), inset: 8pt, stroke: 0.6pt + gray),
)
```

Inside Fletcher, `enclose: (<a>, <b>)` is rewritten to the four corner
points of the union of those nodes' rectangles, then a node large
enough to wrap them is generated.

See [`examples/02-resolve-enclosures/02-resolve-enclosures.typ`](examples/02-resolve-enclosures/02-resolve-enclosures.typ).

## Pitfalls

- Enclosure resolution happens *after* size measurement — referencing
  a node by name that doesn't exist is silently dropped (no crash, but
  no group either). Always double-check `name:` on referenced nodes.
- Mixing `xy` and `uv` enclosure coords is fine; both end up as `xy`
  in the result.

## Related

- `node(enclose: …)` user-facing argument.
- [`resolve-node-coordinates`](03-resolve-node-coordinates.md)
