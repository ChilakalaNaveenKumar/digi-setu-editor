# Spacing options

Five global knobs control the horizontal & vertical density of a
circuit.

| Option | Default | Effect |
| ------ | ------- | ------ |
| `row-spacing` | `12pt` | Vertical gap between wires. |
| `column-spacing` | `12pt` | Horizontal gap between columns. |
| `min-row-height` | `10pt` | Minimum row height (e.g. for empty rows). |
| `min-column-width` | `0pt` | Minimum column width. |
| `gate-padding` | `0.4em` | Inset for gate boxes; also the lstick / rstick stand-off. |

For one-off gutters between two specific cells, see
[tutorial 9](../../tutorial/09-fine-tuning.md) (length items).

## Tight circuit

```typst
#quantum-circuit(
  row-spacing: 5pt,
  column-spacing: 5pt,
  gate-padding: 2pt,
  1, $A$, $B$, 1, [\ ],
  1, 1, $S$, 1
)
```

## Wide circuit

```typst
#quantum-circuit(
  row-spacing: 18pt,
  column-spacing: 18pt,
  gate-padding: 6pt,
  lstick($|0〉$, n: 3), $H$, ctrl(1), ctrl(2), 1, rstick("GHZ", n: 3), [\ ],
  1, $H$, ctrl(), 1, $H$, 1, [\ ],
  1, $H$, 1, ctrl(), $H$, 1
)
```

See [`examples/01-spacing/01-spacing.typ`](examples/01-spacing/01-spacing.typ).

## Pitfalls

- `gate-padding` doubles as the stand-off distance for `lstick` /
  `rstick`. Increasing it widens the brace gap.
- `min-row-height` is the floor; it cannot make rows *smaller* than
  the tallest gate body on that row.
- For circuits embedded in line, you usually want `column-spacing: 7pt`
  + `row-spacing: 6pt` to match math-mode density.

## Related

- Per-cell gutters: [tutorial 9](../../tutorial/09-fine-tuning.md)
- Equal heights: [`05-equal-row-heights.md`](05-equal-row-heights.md)
