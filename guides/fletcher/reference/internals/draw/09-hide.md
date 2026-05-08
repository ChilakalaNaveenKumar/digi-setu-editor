# `hide(objects, bounds)`

Mark drawing objects as **invisible**, with the option to keep or
drop their layout footprint. Wraps the result in `cetz.draw.hide` so
it survives layout while disappearing visually.

## Signature

```typst
hide(
  objects: content | array,    // diagram objects to hide
  bounds:  bool default true,  // keep layout space (true) or collapse it (false)
)
```

## Two flavours

| Call | Effect |
| ---- | ------ |
| `fletcher.hide(<objs>, bounds: true)` | Layout proceeds *as if the objects were there*, but they don't render. Useful for "reserving" space. |
| `fletcher.hide(<objs>, bounds: false)` | Like the objects were never written; layout collapses around the gap. Useful for incremental Touying steps. |

## Example — gradual reveal

```typst
#diagram(
  node((0, 0), [A]),
  fletcher.hide(node((1, 0), [B])),
  node((2, 0), [C]),
)
```

`B` is invisible but the diagram still leaves room for it; the arrow
from `A` to `C` therefore goes through the same gap. Replace
`fletcher.hide(...)` with the bare node to "show" `B` later.

See [`examples/09-hide/09-hide.typ`](examples/09-hide/09-hide.typ).

## Pitfalls

- The argument order is `(objects, bounds)`, *not* `(bounds, objects)`.
- For Touying, prefer the `reducer:` pattern from the
  [Touying tutorial](../../../tutorial/08-touying.md) — it composes
  better than manually wrapping nodes in `hide`.

## Related

- [Tutorial: Touying integration](../../../tutorial/08-touying.md)
