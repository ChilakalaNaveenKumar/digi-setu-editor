# 11 — Custom gates (writing a `draw-function`)

`gate(...)` and `mqgate(...)` accept a `draw-function:` argument that
controls how the gate is rendered. The signature is:

```typst
draw-function: (gate, draw-params) => content
```

`gate` is a dictionary with the gate's user-facing attributes (`content`,
`fill`, `stroke`, `radius`, `width`, `box`, `multi`, `data`).
`draw-params` carries circuit-wide style (`wire`, `padding`,
`background`, `color`, …).

Use a custom `draw-function` when you want a gate to look completely
different — e.g. only vertical edges, a custom fill pattern, or any
other shape. For colour / radius / fill changes, the regular `fill:`,
`stroke:`, `radius:` arguments on `gate(...)` are enough.

## A minimal example: vertical-edges-only gate

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

> **Pitfall:** `draw-params.background` may be `auto` (the package's
> default), and `gate.fill` may be `auto` too. Both must be normalised
> to a real colour before passing to `box(fill: ...)` — otherwise
> compilation fails with `expected color, gradient, tiling, or none, found auto`.

The custom function pulls the global wire stroke, picks the gate's own
fill (or falls back to `draw-params.background`), and uses Typst's
`box` with only `left` and `right` strokes.

See [`examples/11-custom-gates/11-custom-gates.typ`](examples/11-custom-gates/11-custom-gates.typ).

## What's in `draw-params`?

| Key | Meaning |
| --- | ------- |
| `wire` | Global wire stroke set via `quantum-circuit(wire: ...)`. |
| `padding` | Default gate inset (`gate-padding`). |
| `background` | Circuit background fill (matches dark / light mode). |
| `color` | Foreground colour for text / lines. |
| `font-size` | Default text size. |

## What's in `gate`?

The fields available depend on whether the gate is single- or multi-qubit:

| Key | Meaning |
| --- | ------- |
| `content` | Body passed in (e.g. `$H$`, `"Quill"`). |
| `fill` | Per-gate fill, or `none`. |
| `stroke` | Per-gate stroke, or `auto`. |
| `radius` | Border radius. |
| `width` | Set width if any. |
| `box` | Whether the wire is broken at the gate. |
| `data` | Any extra data you stored via `gate(..., data: ...)`. |
| `multi.target` | (mqgate only) relative target qubit for the control wire. |
| `multi.num-qubits` | Number of wires spanned. |
| `multi.wire-count` | Wire count for the control line. |
| `multi.extent` | Extra extension above first / below last wire. |

## Pitfalls

- Always read the wire stroke from `draw-params.wire`, not a hardcoded
  colour — otherwise dark-mode circuits will look broken.
- `draw-params.background` may be `auto` / `none`; fall back gracefully.
- If your custom gate sizes itself differently from the default, also
  pass a matching `size-hint:` so layout reserves the right cell area.

## Done!

You've reached the end of the tutorial. Continue to the
[reference](../reference/) for function-by-function detail.
