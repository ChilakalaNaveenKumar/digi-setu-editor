# `size-hint:` — telling Quill how big the gate is

`size-hint:` is the layout-pass companion to `draw-function:`. The
signature is:

```typst
size-hint: (gate, draw-params) => (width: <length>, height: <length>)
```

Quill calls `size-hint` *first* to reserve the cell, then
`draw-function` to actually render. Without a matching size-hint your
custom render may overflow into adjacent cells.

## Default

If you don't set `size-hint`, Quill uses `layout.default-size-hint`,
which measures `gate.content` plus `2 * draw-params.padding`.

## Custom width example

```typst
#let always-wide(gate, draw-params) = {
  let m = measure(gate.content)
  (width: 2cm, height: m.height + 2 * draw-params.padding)
}

#let draw-wide(gate, draw-params) = box(
  gate.content,
  width: 2cm,
  height: auto,
  fill: white,
  stroke: draw-params.wire,
  inset: draw-params.padding,
  align(center + horizon, gate.content),
)

#quantum-circuit(
  1, gate($H$,
    draw-function: draw-wide,
    size-hint: always-wide), 1,
)
```

See [`examples/02-size-hint/02-size-hint.typ`](examples/02-size-hint/02-size-hint.typ).

## Pitfalls

- `size-hint` must return a dictionary with **both** `width` and
  `height` keys.
- **Do not** return a `height` containing `em` units — Quill's layout
  cannot compare `1em + 8pt` to a pure `pt` row height and crashes
  with `cannot compare 8pt + 1em with 10pt`. Use `measure(...)` to
  resolve the body height into pure points first.
- The cell reserved is exactly the size you return — make sure your
  draw function fits inside (or use `box(..., clip: true)` to keep it
  contained).
- For `mqgate(...)`, `size-hint` is responsible for the *whole* gate
  body (across all spanned wires); the multi-wire layout is handled
  separately by Quill.

## Related

- Drawing: [`01-draw-function.md`](01-draw-function.md)
- Per-gate state: [`03-data-and-state.md`](03-data-and-state.md)
