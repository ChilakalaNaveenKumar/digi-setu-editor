# Fletcher Tutorial — overview

The Fletcher tutorial walks you from "blank Typst file" to a fully
styled commutative diagram with custom marks and CeTZ overlays.

| # | Page | What you learn |
| - | ---- | -------------- |
| 1 | [`01-introduction.md`](01-introduction.md) | What Fletcher does, importing it, the first diagram. |
| 2 | [`02-diagrams-and-coordinates.md`](02-diagrams-and-coordinates.md) | `diagram(..)` body, elastic vs absolute coords, coord expressions. |
| 3 | [`03-nodes.md`](03-nodes.md) | `node()` basics, shapes, anchors, groups, `enclose:`. |
| 4 | [`04-edges.md`](04-edges.md) | `edge()` vertices, `auto`, relative shorthands, anchors, types, snap. |
| 5 | [`05-marks-and-arrows.md`](05-marks-and-arrows.md) | The mark shorthand string, default mark table. |
| 6 | [`06-custom-marks.md`](06-custom-marks.md) | Mark objects, special properties, defining shorthands. |
| 7 | [`07-cetz-integration.md`](07-cetz-integration.md) | The `render:` callback — Bézier edges with CeTZ. |
| 8 | [`08-touying.md`](08-touying.md) | Incremental reveals via `touying-reducer`. |

## Conventions used in every example

```typst
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)
```

`#set page(width: auto, height: auto)` produces a tight bounding box
so the rendered PNG/PDF only contains the diagram. All examples in
this tree compile cleanly with `typst compile <file>.typ`.

## Where to go after

- Per-function reference: [`reference/main/`](../reference/main/00-main-overview.md)
- Every node shape: [`reference/shapes/`](../reference/shapes/00-shapes-overview.md)
- Internals: [`reference/internals/`](../reference/internals/00-internals-overview.md)
- Famous diagram reproductions: [`demos/`](../demos/00-demos-overview.md)
