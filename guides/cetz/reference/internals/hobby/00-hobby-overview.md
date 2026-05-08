# `hobby` — Hobby Smooth-Curve Algorithm

`cetz.hobby` (in the package source: `src/hobby.typ`) implements John
Hobby's smooth-curve algorithm — the same algorithm Metafont uses to
fit a smooth curve through a sequence of points.

> **Internal module — not re-exported.** `cetz.hobby.*` is *not*
> reachable via `cetz.<x>` from outside the package. The user-facing
> entry point is the `hobby(...)` shape in `cetz.draw`.

## Functions

| File | Function |
| --- | --- |
| [`01-hobby-to-cubic-open.md`](./01-hobby-to-cubic-open.md) | `hobby-to-cubic-open()` |
| [`02-hobby-to-cubic-closed.md`](./02-hobby-to-cubic-closed.md) | `hobby-to-cubic-closed()` |
| [`03-hobby-to-cubic.md`](./03-hobby-to-cubic.md) | `hobby-to-cubic()` |

## Related

- [`hobby`](../../shapes/15-hobby.md) — the user-facing Hobby curve shape
- [`catmull`](../../shapes/14-catmull.md) — alternative smooth-fit shape
- [`internals/bezier`](../bezier/00-bezier-overview.md) — the cubic
  Beziers Hobby produces
