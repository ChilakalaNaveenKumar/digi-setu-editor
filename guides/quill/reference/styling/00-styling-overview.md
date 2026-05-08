# Styling — overview

Recipes that touch the **whole** circuit at once via
`quantum-circuit(...)` options.

| Page | What you change |
| ---- | --------------- |
| [`01-spacing.md`](01-spacing.md) | `row-spacing`, `column-spacing`, `min-row-height`, `min-column-width`, `gate-padding`. |
| [`02-colors.md`](02-colors.md) | `color`, `fill`, `wire` — including a dark-mode recipe. |
| [`03-scale.md`](03-scale.md) | `scale: %` vs Typst's built-in `scale()`. |
| [`04-baseline.md`](04-baseline.md) | `baseline:` for inline math alignment. |
| [`05-equal-row-heights.md`](05-equal-row-heights.md) | Force every row to the tallest height. |
| [`06-circuit-padding.md`](06-circuit-padding.md) | Outer bounding-box padding for annotations. |
| [`07-wires-explicit.md`](07-wires-explicit.md) | `wires: int | array` to force a specific wire layout. |
| [`08-fill-wires.md`](08-fill-wires.md) | `fill-wires: bool` — auto-extend wires to the right edge. |

These pages cross-reference the [`quantum-circuit` reference](../quantum-circuit/00-quantum-circuit.md) but focus on
common recipes (rather than the full signature) so you can copy & paste.
