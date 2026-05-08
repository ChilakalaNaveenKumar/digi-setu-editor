# Edge internals — overview

Helpers that turn an `edge(...)` call into a list of fully-resolved
edges with marks, vertices, labels, and routing parameters.

| Page | Function | Purpose |
| ---- | -------- | ------- |
| [`01-interpret-marks-arg.md`](01-interpret-marks-arg.md) | `interpret-marks-arg(arg)` | Parse the `marks:` argument (string shorthand or list of mark dicts). |
| [`02-interpret-edge-args.md`](02-interpret-edge-args.md) | `interpret-edge-args(args)` | Sort positional args into vertices, marks, label. |
| [`03-apply-edge-shift.md`](03-apply-edge-shift.md) | `apply-edge-shift(grid, edge)` | Apply parallel `shift:` to keep parallel edges separated. |

## Why these exist

`edge` is *very* overloaded — `edge(<a>, <b>, "->")` and
`edge(<a>, "->", <b>, [my label])` should both work. The two
`interpret-*` helpers normalise everything into a strict, predictable
edge dict before the rest of the pipeline runs.

## Pitfalls

- `interpret-marks-arg` may *silently* accept malformed shorthands by
  ignoring the unknown bits. If a custom mark doesn't appear, fall
  back to the explicit list form.
- `apply-edge-shift` operates **in xy space**; you must already have a
  resolved grid to use it manually.
