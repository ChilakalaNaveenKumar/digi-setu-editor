# `intersection` — Path-vs-Path Intersections

`cetz.intersection` is the engine behind the `intersections()` element —
it computes intersection points between primitive paths.

The module is exposed at `cetz.intersection.<fn>`.

## Functions

| File | Function |
| --- | --- |
| [`01-line-line.md`](./01-line-line.md) | `line-line()` |
| [`02-line-cubic.md`](./02-line-cubic.md) | `line-cubic()` |
| [`03-line-path.md`](./03-line-path.md) | `line-path()` |
| [`04-path-path.md`](./04-path-path.md) | `path-path()` |

## Related

- [`intersections`](../../grouping/03-intersections.md) — the user-facing
  shape that consumes these functions
- [`internals/bezier`](../bezier/00-bezier-overview.md) — `line-cubic` is
  built on `bezier.line-cubic-intersections`
