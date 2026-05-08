# `find-farthest-intersection(objects, target, callback)`

For a set of CeTZ objects (typically a node outline), find the
intersection point that is *farthest* from `target` and pass it to
`callback`. If there are no intersections, `callback` is invoked with
`target` itself.

## Signature

```typst
find-farthest-intersection(
  objects:  cetz | array | none,
  target:   point,                    // (length, length)
  callback: point -> any,
)
```

## Why "farthest"

When you draw an arrow into a thick node, the *line* from the arrow's
tail to the node's centre intersects the node outline twice (front
and back face). Fletcher uses the **back** intersection — i.e. the
one farther from the source — so the arrow's head sits on the
correct side of the node.

## Example

Find where a CeTZ-drawn line enters a node's outline and place an
extra marker there. See
[`examples/05-find-farthest-intersection/05-find-farthest-intersection.typ`](examples/05-find-farthest-intersection/05-find-farthest-intersection.typ).

## Pitfalls

- The helper is callback-style on purpose: the intersection lookup
  needs the live CeTZ context, so you can't return the point — you
  must use it inline.
- For `objects: none`, the callback is fired with `target`; design
  your callback to work both ways.

## Related

- [`get-node-anchor`](06-get-node-anchor.md) — the standard
  (angle-based) version.
- [`defocus-adjustment`](07-defocus-adjustment.md)
