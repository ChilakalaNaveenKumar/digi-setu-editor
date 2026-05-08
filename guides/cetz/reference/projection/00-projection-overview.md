# Projection — Overview

Helpers that set up 3-D projections inside a canvas. They wrap the body in a
projection-specific transform so that 3-D coordinates render as expected
2-D drawings.

| Function | Page |
| -------- | ---- |
| `ortho(x:, y:, z:, ..opts, body)` | [`01-ortho.md`](./01-ortho.md) |
| `on-xy(z:, body)` | [`02-on-xy.md`](./02-on-xy.md) |
| `on-xz(y:, body)` | [`03-on-xz.md`](./03-on-xz.md) |
| `on-zy(x:, body)` | [`04-on-zy.md`](./04-on-zy.md) |
| `perspective(x:, y:, z:, distance:, body)` | [`05-perspective.md`](./05-perspective.md) |

## When to use

- **`ortho`** — orthographic projection. The default angles produce an
  isometric view.
- **`on-xy` / `on-xz` / `on-zy`** — draw onto the named plane; specify the
  third-axis offset (`z:` / `y:` / `x:`).
- **`perspective`** — like `ortho` but with foreshortening.

All five share the optional `cull-face:` (back-face culling), `sorted:`
(z-sort drawables), `reset-transform:` (ignore current transform).

## See also

- [`reference/transformation`](../transformation/00-transformation-overview.md)
  — the underlying transform machinery these projections wrap
- [`internals/matrix`](../internals/matrix/00-matrix-overview.md) — the
  raw rotation / translation / scale matrix builders
