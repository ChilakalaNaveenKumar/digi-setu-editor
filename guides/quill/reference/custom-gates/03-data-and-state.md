# `data:` — per-gate state for custom renderers

`gate(..., data: <any>)` lets you stash arbitrary information on a
gate. Inside the `draw-function`, you read it back as `gate.data`. Use
this when:

- You want one `draw-function` to render multiple shapes based on a
  small parameter (e.g. an icon name, a count, a colour key).
- You need the gate to remember layout state for an annotation later.

## Example: parametric coloured gates

```typst
#let draw-tag(gate, draw-params) = {
  let stroke = draw-params.wire
  let bg = draw-params.at("background", default: white)
  let info = gate.data    // (color: ..., emoji: ...)
  let fill = info.color
  box(
    stroke: stroke,
    fill: fill,
    inset: draw-params.padding,
    radius: 3pt,
    [#info.emoji #gate.content],
  )
}

#quantum-circuit(
  1, gate("apple", draw-function: draw-tag,
    data: (color: red.lighten(70%), emoji: text("🍎"))), 1,
  gate("banana", draw-function: draw-tag,
    data: (color: yellow.lighten(50%), emoji: text("🍌"))), 1,
)
```

See [`examples/03-data-and-state/03-data-and-state.typ`](examples/03-data-and-state/03-data-and-state.typ).

## Pitfalls

- `gate.data` is `none` by default — guard with
  `if gate.data != none { ... }` if you also use the same draw
  function for vanilla gates.
- The contents of `data` are **opaque** to Quill: layout doesn't
  inspect it, so you may have to set a `size-hint:` for accurate
  sizing.

## Related

- Drawing: [`01-draw-function.md`](01-draw-function.md)
- Layout sizing: [`02-size-hint.md`](02-size-hint.md)
