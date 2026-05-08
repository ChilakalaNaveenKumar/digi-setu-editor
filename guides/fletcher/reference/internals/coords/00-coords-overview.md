# Coordinates internals — overview

Helpers that convert between Fletcher's two coordinate systems:
**elastic / `uv`** (row-column, depends on grid sizes) and
**absolute / `xy`** (physical lengths in CeTZ space).

| Page | Function | Direction |
| ---- | -------- | --------- |
| [`01-uv-to-xy.md`](01-uv-to-xy.md) | `uv-to-xy(grid, uv)` | `uv → xy` (point) |
| [`02-xy-to-uv.md`](02-xy-to-uv.md) | `xy-to-uv(grid, xy)` | `xy → uv` (point) |
| [`03-duv-to-dxy.md`](03-duv-to-dxy.md) | `duv-to-dxy(grid, uv, duv)` | `uv → xy` (tangent / nudge) |
| [`04-dxy-to-duv.md`](04-dxy-to-duv.md) | `dxy-to-duv(grid, xy, dxy)` | `xy → uv` (tangent / nudge) |
| [`05-vector-polar-with-xy-or-uv-length.md`](05-vector-polar-with-xy-or-uv-length.md) | `vector-polar-with-xy-or-uv-length(grid, xy, target-length, θ)` | Polar offset whose length is in xy *or* uv. |
| [`06-resolve.md`](06-resolve.md) | `resolve(ctx, update, ..coordinates)` | Drop-in `cetz.coordinate.resolve` extended for `uv`. |

## When to use them

- Inside `render:` callbacks when the diagram has been laid out and
  you have access to `grid`.
- When authoring custom `shape:` functions and you need to draw extra
  CeTZ shapes anchored to elastic coordinates.

## Pitfall: nan results

If `resolve` doesn't have a `grid` in its context but you ask for a
`uv` coordinate, it returns `(float.nan, float.nan)` instead of raising
— always guard with a fallback when calling it manually.
