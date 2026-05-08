# `draw-function:` — fully custom rendering

The signature is `(gate, draw-params) => content`. Returning content
draws it inside the gate's reserved cell.

## What's in `gate`

| Key | Type | Notes |
| --- | ---- | ----- |
| `content` | content | Body passed in. |
| `fill` | color / `none` / `auto` | Per-gate fill. |
| `stroke` | stroke / `auto` | Per-gate border. |
| `radius` | length / dictionary | Border radius. |
| `width` | length / `auto` | Forced width. |
| `box` | bool | Whether the wire is broken at the gate. |
| `data` | any | Free-form passed via `gate(..., data: ...)`. |
| `multi.target` | int (mqgate only) | Relative target wire. |
| `multi.num-qubits` | int | Wires spanned. |
| `multi.wire-count` | int | Lines on the control wire. |
| `multi.extent` | length | Above-first / below-last extension. |

## What's in `draw-params`

| Key | Notes |
| --- | ----- |
| `wire` | Global wire stroke (`quantum-circuit(wire: ...)`). |
| `padding` | Default `gate-padding`. |
| `background` | Background fill (may be `auto` or a colour — normalise!). |
| `color` | Foreground colour. |
| `font-size` | Default font size. |

## Vertical-edges-only gate

```typst
#let draw-quill-gate(gate, draw-params) = {
  let stroke = draw-params.wire
  let bg = draw-params.at("background", default: white)
  let fill = if gate.fill != none and gate.fill != auto { gate.fill }
             else if bg == auto { white }
             else { bg }
  box(
    gate.content,
    fill: fill,
    stroke: (left: stroke, right: stroke),
    inset: draw-params.padding,
  )
}

#quantum-circuit(
  1, gate("Quill", draw-function: draw-quill-gate), 1,
)
```

## Diamond-shaped gate

```typst
#let draw-diamond(gate, draw-params) = {
  let s = draw-params.wire
  let bg = draw-params.at("background", default: white)
  let fill = if gate.fill != none and gate.fill != auto { gate.fill }
             else if bg == auto { white }
             else { bg }
  box(
    rotate(45deg, box(
      gate.content,
      stroke: s,
      fill: fill,
      inset: draw-params.padding,
    )),
  )
}

#quantum-circuit(
  1, gate($X$, draw-function: draw-diamond), 1
)
```

See [`examples/01-draw-function/01-draw-function.typ`](examples/01-draw-function/01-draw-function.typ).

## Pitfalls

- **Always normalise** `gate.fill` (may be `auto`) and
  `draw-params.background` (may be `auto`) into a real colour before
  passing to `box(fill: ...)` — otherwise compilation fails with
  `expected color, gradient, tiling, or none, found auto`.
- Use `draw-params.wire` for strokes — that way dark-mode + theming
  still work.
- If your custom gate sizes itself differently from the default, also
  set a `size-hint:` ([`02-size-hint.md`](02-size-hint.md)).

## Related

- Layout sizing: [`02-size-hint.md`](02-size-hint.md)
- Per-gate state: [`03-data-and-state.md`](03-data-and-state.md)
- Tutorial: [tutorial 11](../../tutorial/11-custom-gates.md)
