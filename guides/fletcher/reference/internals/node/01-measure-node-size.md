# `measure-node-size(node, styles)` — measure a node body

Return the bounding rectangle Fletcher will use for the node during
layout. It already accounts for `inset:`, `corner-radius:`, and
explicit `width:` / `height:`.

## Signature

```typst
measure-node-size(
  node:   dict,           // a fully constructed node dict
  styles,                 // styles from `style(...)` or `context`
) -> dict                 // the same node, with `size` filled in
```

The returned dict augments the original node with a `size` field — a
`(width, height)` 2-tuple of `length` values.

## Example

```typst
#context {
  let n = fletcher.node((0, 0), [Hello])
  let measured = fletcher.measure-node-size(n, here())
  measured.size  // → (width, height)
}
```

See [`examples/01-measure-node-size/01-measure-node-size.typ`](examples/01-measure-node-size/01-measure-node-size.typ).

## Pitfalls

- Must be called inside a `context` (or after `style(s => …)`) — the
  raw measurement requires the surrounding text styles.
- The returned size **excludes** any extra padding added later by edge
  routing.

## Related

- [`compute-cell-sizes`](../diagram/03-compute-cell-sizes.md) consumes
  these per-node sizes.
- [`resolve-node-coordinates`](03-resolve-node-coordinates.md) handles
  the *position* part.
