# Utility internals — overview

Small math / content helpers Fletcher uses internally. They're
exposed on the `fletcher` module and occasionally useful when you
write your own custom shapes / edges / marks.

| Page | Function | Purpose |
| ---- | -------- | ------- |
| [`01-interp.md`](01-interp.md) | `interp(values, index, spacing)` | Linear interpolation across an array of `length`s with linear extrapolation outside the bounds. |
| [`02-interp-inv.md`](02-interp-inv.md) | `interp-inv(values, value, spacing)` | The inverse of `interp` — given a `length`, what fractional index produces it? |
| [`03-get-arc-connecting-points.md`](03-get-arc-connecting-points.md) | `get-arc-connecting-points(from, to, angle)` | Given two points and a bend angle, return the (centre, radius, start, stop) of the arc connecting them. |
| [`04-is-space.md`](04-is-space.md) | `is-space(el)` | True iff a content element is whitespace (spaces, tabs, newlines, …). |

## Common use cases

- `interp` powers the elastic-coordinate map (`uv-to-xy`); calling it
  yourself lets you mimic Fletcher's interpolation on your own data.
- `get-arc-connecting-points` is the *only* practical way to compute
  the same arc geometry Fletcher uses — handy when overlaying
  decorations on an arc edge.
- `is-space` is invaluable for parsers (mark shorthand, edge args)
  that work with content arrays.

## Pitfalls

- `interp` returns a *length*, not a number — keep dimensional
  consistency in mind.
- Pass `length`-typed values; mixing in raw numbers raises a type
  error.
