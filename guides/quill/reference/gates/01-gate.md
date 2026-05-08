# `gate()` — single-qubit gate (the base constructor)

Creates a single-qubit (or classical) gate. Special variants like
`ctrl`, `swap`, `meter` are derived from `gate` internally; you call
`gate` directly when you need full control over fill, stroke, radius,
labels or the draw function.

## Signature

```typst
gate(
  body:       content,
  x:          auto | int = auto,
  y:          auto | int = auto,
  fill:       auto | none | color | gradient | tiling = auto,
  stroke:     auto | stroke = auto,
  radius:     length | dictionary = 0pt,
  width:      auto | length = auto,
  box:        bool = true,
  floating:   bool = false,
  multi:      none | dictionary = none,
  size-hint:  function = layout.default-size-hint,
  draw-function: function = draw-functions.draw-boxed-gate,
  data:       any = none,
  label:      none | array | str | content | dictionary = none,
)
```

## Variants

| Variant | What changes |
| ------- | ------------ |
| `gate($H$)` | Standard square box. |
| `gate($X$, radius: 100%)` | Round gate. |
| `gate($Y$, radius: (right: 100%))` | D-shaped (rounded right side). |
| `gate(body, fill: red)` | Coloured fill. |
| `gate(body, stroke: blue)` | Custom border. |
| `gate(body, box: false)` | No box, content sits on the wire. |
| `gate(body, draw-function: f)` | Fully custom draw (see custom gates). |

## Examples

```typst
#quantum-circuit(
  1, gate($H$), 1, [\ ],
  1, gate($X$, radius: 100%), 1, [\ ],
  1, gate($Y$, radius: (right: 100%)), 1, [\ ],
  1, gate($Z$, fill: red.lighten(60%)), 1
)
```

See [`examples/01-gate/01-gate.typ`](examples/01-gate/01-gate.typ).

## Pitfalls

- `body` is **content**, not a string — math is `$H$`, not `"H"`. A
  bare string sits on the wire as text.
- `fill: auto` inherits from `quantum-circuit(fill: ...)`. Pass
  `fill: none` for transparent.
- `radius: 100%` takes the *shorter side* — you'll get a stadium /
  pill shape, not a perfect circle, if the gate is wider than tall.

## Related

- Multi-qubit version: [`mqgate`](02-mqgate.md)
- Custom rendering: [`custom-gates/01-draw-function.md`](../custom-gates/01-draw-function.md)
- Labels around a gate: [tutorial 6](../../tutorial/06-labels.md)
