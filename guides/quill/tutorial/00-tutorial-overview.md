# Quill Tutorial — overview

The Quill tutorial walks you from "I have a blank Typst file" to a
fully-styled multi-qubit circuit with annotations and a custom gate.
Every page has a paired runnable example under `examples/`.

| # | Page | What you learn |
| - | ---- | -------------- |
| 1 | [`01-introduction.md`](01-introduction.md) | What Quill does, importing it, the very first circuit. |
| 2 | [`02-basics.md`](02-basics.md) | `quantum-circuit`, `gate()` shorthand, integers as empty cells, `[\\ ]` row breaks. |
| 3 | [`03-multi-qubit-and-labels.md`](03-multi-qubit-and-labels.md) | `mqgate(...)`, `lstick`, `rstick`, multi-wire braces. |
| 4 | [`04-wires.md`](04-wires.md) | `setwire(count, stroke, wire-distance)` for classical / bundled wires. |
| 5 | [`05-slices-and-groups.md`](05-slices-and-groups.md) | `slice()` and `gategroup()` to label phases of the circuit. |
| 6 | [`06-labels.md`](06-labels.md) | The full label dictionary (`content`, `pos`, `dx`, `dy`); multi-label arrays. |
| 7 | [`07-gate-placement.md`](07-gate-placement.md) | Manual placement with `x:` / `y:` (table-cell-style). |
| 8 | [`08-styling.md`](08-styling.md) | `wire`, `color`, `fill`, `scale`, dark-mode example. |
| 9 | [`09-fine-tuning.md`](09-fine-tuning.md) | Length items as gutters, vertical spacing after `[\\ ]`. |
| 10 | [`10-annotations.md`](10-annotations.md) | `annotate(columns, rows, callback)` for arbitrary overlays. |
| 11 | [`11-custom-gates.md`](11-custom-gates.md) | Writing a `draw-function: (gate, draw-params) => ...`. |

## Conventions used in every example

```typst
#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)
```

`#set page(width: auto, height: auto)` produces a tight bounding box so
the rendered PNG / PDF only contains the circuit. All examples in this
tree are runnable as-is — `typst compile <file>.typ` should produce a
clean PDF.

## Where to go after

- Function-by-function reference: [`reference/`](../reference/)
- Gallery of every gate symbol: [`gallery/`](../gallery/)
- Famous-circuit reproductions: [`demos/`](../demos/)
