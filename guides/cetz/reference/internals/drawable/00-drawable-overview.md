# `drawable` — Low-Level Drawables

`cetz.drawable` constructs the *drawable* dictionaries that the renderer
consumes: paths, line strips, content boxes, ellipses, and arcs. CeTZ
shapes ultimately produce one or more drawables.

The module is exposed at `cetz.drawable.<fn>`.

## Functions

| File | Function |
| --- | --- |
| [`01-apply-transform.md`](./01-apply-transform.md) | `apply-transform()` |
| [`02-apply-tags.md`](./02-apply-tags.md) | `apply-tags()` |
| [`03-filter-tagged.md`](./03-filter-tagged.md) | `filter-tagged()` |
| [`04-path.md`](./04-path.md) | `path()` |
| [`05-line-strip.md`](./05-line-strip.md) | `line-strip()` |
| [`06-content.md`](./06-content.md) | `content()` |
| [`07-ellipse.md`](./07-ellipse.md) | `ellipse()` |
| [`08-arc.md`](./08-arc.md) | `arc()` |

> **Note.** Drawables are rarely constructed by user code — they exist so
> CeTZ shapes (and the occasional custom shape) have a uniform low-level
> representation. The `.typ` examples in this folder mostly show the
> *shape* of the returned dictionary.

## Related (drawable ↔ shape)

| Drawable | User-facing shape |
| -------- | ----------------- |
| [`drawable.path`](./04-path.md) | [`compound-path`](../../shapes/16-compound-path.md), [`merge-path`](../../shapes/17-merge-path.md), [`svg-path`](../../shapes/19-svg-path.md) |
| [`drawable.line-strip`](./05-line-strip.md) | [`line`](../../shapes/06-line.md), [`polygon`](../../shapes/07-polygon.md), [`n-star`](../../shapes/08-n-star.md), [`grid`](../../shapes/09-grid.md) |
| [`drawable.content`](./06-content.md) | [`content`](../../shapes/10-content.md) |
| [`drawable.ellipse`](./07-ellipse.md) | [`circle`](../../shapes/01-circle.md), [`circle-through`](../../shapes/02-circle-through.md) |
| [`drawable.arc`](./08-arc.md) | [`arc`](../../shapes/03-arc.md), [`arc-through`](../../shapes/04-arc-through.md) |

See also [Types — `drawable`](../../../types/00-types-overview.md).
