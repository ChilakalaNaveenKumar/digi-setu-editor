# `aabb` — Axis-Aligned Bounding Boxes

`cetz.aabb` (in the package source: `src/aabb.typ`) is the bounding-box
math used everywhere CeTZ needs to size things — auto-sizing the canvas,
computing border anchors, deciding which fonts and ratios to use, etc.

A *bounds* dictionary has the form `(low: vector, high: vector)`.

> **Internal module — not re-exported.** `cetz.aabb.*` is *not* reachable
> via `cetz.<x>` from outside the package. The functions are documented
> here for reference; the user-facing way to interact with the same idea
> is through CeTZ's bounding-box anchors and the `debug:` flag on
> `canvas`.

## Functions

| File | Function |
| --- | --- |
| [`01-aabb.md`](./01-aabb.md) | `aabb()` |
| [`02-mid.md`](./02-mid.md) | `mid()` |
| [`03-corner-points.md`](./03-corner-points.md) | `corner-points()` |
| [`04-size.md`](./04-size.md) | `size()` |
| [`05-padded.md`](./05-padded.md) | `padded()` |

## Related

- [`rect-around`](../../shapes/18-rect-around.md) — user-facing
  bounding-rectangle shape
- [`canvas`](../../canvas/00-canvas-overview.md) `debug: true` — visualises
  every drawable's AABB
- [`internals/path-util`](../path-util/00-path-util-overview.md) —
  `path-util.bounds` produces the points that feed into `aabb`
