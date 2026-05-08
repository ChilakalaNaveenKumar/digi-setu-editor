# `bezier` — Bézier Math

`cetz.bezier` (in the package source: `src/bezier.typ`) supplies the math
behind every Bézier and Catmull-Rom curve in CeTZ — point evaluation,
derivative evaluation, splitting, arclength, shortening, AABB, line
intersection.

> **Internal module — not re-exported.** `cetz.bezier.*` is *not*
> reachable via `cetz.<x>` from outside the package. The functions are
> documented here to mirror the upstream manual; user code interacts with
> the math indirectly through the `bezier`, `bezier-through`, `catmull`
> and `merge-path` shape APIs.

## Functions

| File | Function |
| --- | --- |
| [`01-quadratic-point.md`](./01-quadratic-point.md) | `quadratic-point()` |
| [`02-quadratic-derivative.md`](./02-quadratic-derivative.md) | `quadratic-derivative()` |
| [`03-cubic-point.md`](./03-cubic-point.md) | `cubic-point()` |
| [`04-cubic-derivative.md`](./04-cubic-derivative.md) | `cubic-derivative()` |
| [`05-to-abc.md`](./05-to-abc.md) | `to-abc()` |
| [`06-quadratic-through-3points.md`](./06-quadratic-through-3points.md) | `quadratic-through-3points()` |
| [`07-quadratic-to-cubic.md`](./07-quadratic-to-cubic.md) | `quadratic-to-cubic()` |
| [`08-cubic-through-3points.md`](./08-cubic-through-3points.md) | `cubic-through-3points()` |
| [`09-split.md`](./09-split.md) | `split()` |
| [`10-cubic-arclen.md`](./10-cubic-arclen.md) | `cubic-arclen()` |
| [`11-cubic-shorten-linear.md`](./11-cubic-shorten-linear.md) | `cubic-shorten-linear()` |
| [`12-cubic-t-for-distance.md`](./12-cubic-t-for-distance.md) | `cubic-t-for-distance()` |
| [`13-cubic-shorten.md`](./13-cubic-shorten.md) | `cubic-shorten()` |
| [`14-cubic-extrema.md`](./14-cubic-extrema.md) | `cubic-extrema()` |
| [`15-cubic-aabb.md`](./15-cubic-aabb.md) | `cubic-aabb()` |
| [`16-catmull-to-cubic.md`](./16-catmull-to-cubic.md) | `catmull-to-cubic()` |
| [`17-line-cubic-intersections.md`](./17-line-cubic-intersections.md) | `line-cubic-intersections()` |

## Related

- [`bezier`](../../shapes/12-bezier.md) — quadratic / cubic bezier shape
- [`bezier-through`](../../shapes/13-bezier-through.md) — cubic bezier
  fitted through three points
- [`catmull`](../../shapes/14-catmull.md) — Catmull-Rom spline (built on
  `catmull-to-cubic`)
- [`hobby`](../../shapes/15-hobby.md) — Hobby curve (uses cubic Beziers)
