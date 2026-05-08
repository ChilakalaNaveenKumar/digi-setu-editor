# Transformation — Overview

Functions that mutate the current 4 × 4 transformation matrix and the
"previous coordinate". They take effect for **everything drawn after them**
in the same scope and reset at the end of the surrounding `group` /
`scope` / canvas body.

| Function | Page |
| -------- | ---- |
| `set-transform(mat)` | [`01-set-transform.md`](./01-set-transform.md) |
| `transform(mat)` | [`02-transform.md`](./02-transform.md) |
| `rotate(..angles, origin: ...)` | [`03-rotate.md`](./03-rotate.md) |
| `translate(..args, pre: ...)` | [`04-translate.md`](./04-translate.md) |
| `scale(..args, origin: ...)` | [`05-scale.md`](./05-scale.md) |
| `set-origin(origin)` | [`06-set-origin.md`](./06-set-origin.md) |
| `move-to(pt)` | [`07-move-to.md`](./07-move-to.md) |
| `set-viewport(from, to, bounds: ...)` | [`08-set-viewport.md`](./08-set-viewport.md) |

## Mental model

The canvas keeps a single 4 × 4 transformation matrix `C`. Every
draw-coordinate is multiplied through `C` before being rendered.

- `transform(T)` applies a new matrix `T` on top: `C' = C * T`.
- `set-transform(M)` replaces `C` entirely. Pass `none` to reset to
  identity (`matrix.ident(4)`).
- `rotate`, `translate`, `scale`, `set-origin` are convenience wrappers
  that build a small matrix `T` and call `transform(T)` for you.
- `move-to` doesn't modify `C` — it sets the *previous coordinate* used by
  relative coordinates and `()`.
- `set-viewport` rescales the unit so a logical bounds box maps to a
  physical box on the canvas (handy for plotting frameworks).

## See also

- [`projection/`](../projection/) — 3-D projections (`ortho`, `perspective`,
  `on-xy`, `on-xz`, `on-zy`).
- [`internals/matrix/`](../internals/matrix/) — raw 4×4 matrix builders.
