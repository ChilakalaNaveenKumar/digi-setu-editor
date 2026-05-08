# `path-util` — Path Manipulation

`cetz.path-util` works on the *path* representation that flows through
the renderer — arrays of subpaths consisting of line and cubic segments.
It provides constructors, length / arclength queries, point-at queries,
shortening, and normalization.

The module is exposed at `cetz.path-util.<fn>`.

## Functions

| File | Function |
| --- | --- |
| [`01-make-subpath.md`](./01-make-subpath.md) | `make-subpath()` |
| [`02-first-subpath-closed.md`](./02-first-subpath-closed.md) | `first-subpath-closed()` |
| [`03-first-subpath-start.md`](./03-first-subpath-start.md) | `first-subpath-start()` |
| [`04-subpath-start.md`](./04-subpath-start.md) | `subpath-start()` |
| [`05-subpath-end.md`](./05-subpath-end.md) | `subpath-end()` |
| [`06-last-subpath-end.md`](./06-last-subpath-end.md) | `last-subpath-end()` |
| [`07-bounds.md`](./07-bounds.md) | `bounds()` |
| [`08-segment-lengths.md`](./08-segment-lengths.md) | `segment-lengths()` |
| [`09-length.md`](./09-length.md) | `length()` |
| [`10-point-at.md`](./10-point-at.md) | `point-at()` |
| [`11-shorten-to.md`](./11-shorten-to.md) | `shorten-to()` |
| [`12-normalize.md`](./12-normalize.md) | `normalize()` |

## Related

- [`drawable.path`](../drawable/04-path.md) — the path data structure
  this module manipulates
- [`compound-path`](../../shapes/16-compound-path.md) /
  [`merge-path`](../../shapes/17-merge-path.md) /
  [`svg-path`](../../shapes/19-svg-path.md) — user-facing path-building shapes
- [`internals/aabb`](../aabb/00-aabb-overview.md) — bounding-box engine
  fed by `path-util.bounds`
- [Types — `path` / `subpath` / `segment`](../../../types/00-types-overview.md)
