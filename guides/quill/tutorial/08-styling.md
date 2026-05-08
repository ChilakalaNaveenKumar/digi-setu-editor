# 8 — Circuit styling (`wire`, `color`, `fill`, `scale`)

`quantum-circuit(..)` exposes a small set of options that change the
look of the entire circuit at once. They are the right knobs for
themed diagrams (e.g. dark mode in slides) without touching every gate.

## Options

| Option | Type | Default | Effect |
| ------ | ---- | ------- | ------ |
| `wire` | stroke | `0.7pt + black` | Style of the wires (any `line()` stroke). |
| `color` | color | `black` | Foreground for strokes, text, controls, brackets. |
| `fill` | color | `white` | Default fill for gate boxes. |
| `font-size` | length | `10pt` | Default text size inside the circuit. |
| `scale` | ratio | `100%` | Scales every dimension proportionally (layout-aware, unlike Typst's `scale()`). |
| `row-spacing` | length | `12pt` | Vertical gap between rows. |
| `column-spacing` | length | `12pt` | Horizontal gap between columns. |
| `min-row-height` | length | `10pt` | Minimum row height (e.g. for empty rows). |
| `min-column-width` | length | `0pt` | Minimum column width. |
| `gate-padding` | length | `0.4em` | Inset for gate boxes; also the lstick/rstick stand-off. |
| `equal-row-heights` | bool | `false` | Force every row to the height of the tallest. |
| `baseline` | length / content / str | `0pt` | Vertical anchor of the circuit (e.g. `"="` to align with an equals sign). |
| `circuit-padding` | length / dictionary | `0.4em` | Bounding-box padding for annotations & labels that exceed the circuit. |
| `wires` | auto / int / array | `auto` | Force a wire count or list (e.g. `(1, 1, 2)` for two quantum + one classical). |
| `fill-wires` | bool | `true` | Auto-extend wires to the right edge. |

## Dark mode

```typst
#box(fill: black, quantum-circuit(
  wire: .7pt + white,
  color: white,
  fill: black,
  1, $X$, ctrl(1), rstick([*?*]), [\ ],
  1, 1, targ(), meter(),
))
```

Three knobs (`wire`, `color`, `fill`) recolour everything: lines,
brackets, text, gate boxes.

## Scale

`scale: 60%` shrinks the circuit *and* its layout (so the bounding box
also gets smaller). This is **different** from wrapping the circuit in
`scale(60%, ...)` (Typst's built-in), which keeps the layout slot the
same.

## `equal-row-heights`

By default, each row is sized to its largest gate. Set
`equal-row-heights: true` to use the tallest row's height for all rows
— useful when stacked controls would otherwise misalign.

```typst
#quantum-circuit(
  equal-row-heights: true,
  row-spacing: 2pt, min-row-height: 4pt,
  1, $H$, ctrl(1), $H$, 1, [\ ],
  1, $H$, targ(), $H$, 1, [\ ],
  2, ctrl(1), 2, [\ ],
  1, $H$, targ(), $H$, 1
)
```

See [`examples/08-styling/08-styling.typ`](examples/08-styling/08-styling.typ).

## `baseline`

Setting `baseline: "="` makes the circuit's vertical anchor align with
the centre of the equals sign, which is often what you want when
embedding a circuit inline in math.

## Pitfalls

- `scale: 60%` reduces every length proportionally — labels stay
  readable. Wrapping `quantum-circuit(...)` in `scale(60%, ...)` keeps
  the original bounding box and clips badly.
- `circuit-padding` is **not** the same as `gate-padding`. The first is
  the *outer* margin of the circuit (for annotations); the second is
  the *inner* padding of every gate box.
- Setting `fill: none` removes the default white fill — gate boxes will
  be transparent, which can look strange against a coloured background.

## Next

[`09-fine-tuning.md`](09-fine-tuning.md) — length items as gutters,
vertical spacing.
