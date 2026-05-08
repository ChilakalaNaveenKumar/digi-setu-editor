# Custom gates — overview

When the built-in gate styling isn't enough (you need a different
shape, a custom layout calculation, or per-gate state), `gate(...)`
and `mqgate(...)` accept two function-valued arguments:

- **`draw-function: (gate, draw-params) => content`** — controls how
  the gate is rendered.
- **`size-hint: (gate, draw-params) => (width: ..., height: ...)`** —
  tells the layout pass what cell size to reserve before drawing.

Per-gate metadata (anything you'd otherwise capture in a closure) can
ride along on `gate(..., data: ...)` and is accessible from inside the
draw function as `gate.data`.

| Page | Topic |
| ---- | ----- |
| [`01-draw-function.md`](01-draw-function.md) | Writing your own `draw-function`. |
| [`02-size-hint.md`](02-size-hint.md) | Pairing a `size-hint` with a custom render. |
| [`03-data-and-state.md`](03-data-and-state.md) | Stashing per-gate data via `data:`. |

For a tutorial-style walkthrough see [tutorial 11](../../tutorial/11-custom-gates.md).
