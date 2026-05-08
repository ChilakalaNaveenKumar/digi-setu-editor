# Fletcher — diagrams with arrows for Typst

[Fletcher](https://github.com/Jollywatt/typst-fletcher) (v0.5.8 — *a
maker of arrows*) is a Typst package for drawing **diagrams**:
commutative diagrams, flow charts, state machines, block diagrams. It
runs **on top of CeTZ**, so anything Fletcher draws ultimately becomes
CeTZ canvas content.

This sub-corpus mirrors the Fletcher manual one concept per page with
runnable `.typ` examples for each. **Always cite paths under
`guides/fletcher/`** for Fletcher questions.

## Install / import

```typst
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
```

The wildcard import is **not** recommended (Fletcher exports many
internal helpers). Pull just what you need: `diagram`, `node`, `edge`,
plus any shapes from the `fletcher.shapes` submodule.

```typst
#import fletcher.shapes: diamond, hexagon, brace
```

## Folder layout

| Folder | Contents |
| ------ | -------- |
| `tutorial/` | Walkthrough — diagrams, coordinates, nodes, edges, marks, custom marks, CeTZ integration, Touying. |
| `reference/main/` | The three top-level functions: `diagram()`, `node()`, `edge()`. |
| `reference/shapes/` | Every node shape (`rect`, `circle`, `ellipse`, `pill`, `parallelogram`, `trapezium`, `diamond`, `triangle`, `house`, `chevron`, `hexagon`, `octagon`, `cylinder`, `stretched-glyph`, `brace`, `bracket`, `paren`). |
| `reference/internals/marks/` | Mark internals: `cap-offset`, `resolve-mark`, `draw-mark`, `mark-debug`, plus `MARKS` registry. |
| `reference/internals/coords/` | Coordinate maps: `uv-to-xy`, `xy-to-uv`, `duv-to-dxy`, `dxy-to-duv`, `vector-polar-with-xy-or-uv-length`, `resolve`. |
| `reference/internals/diagram/` | Layout helpers: `interpret-axes`, `expand-fractional-rects`, `compute-cell-sizes`, `compute-cell-centers`, `compute-grid`. |
| `reference/internals/node/` | Node helpers: `measure-node-size`, `resolve-node-enclosures`, `resolve-node-coordinates`. |
| `reference/internals/edge/` | Edge helpers: `interpret-marks-arg`, `interpret-edge-args`, `apply-edge-shift`. |
| `reference/internals/draw/` | Drawing primitives: `draw-edge-line`, `draw-edge-arc`, `draw-edge-polyline`, `place-edge-label-on-curve`, `find-farthest-intersection`, `get-node-anchor`, `defocus-adjustment`, `draw-debug-axes`, `hide`. |
| `reference/internals/utils/` | Math helpers: `interp`, `interp-inv`, `get-arc-connecting-points`, `is-space`. |
| `gallery/` | One example per node shape and per arrow style. |
| `demos/` | Larger reproduction figures — semilattice, signal flow, MSE network, CeTZ-extended Bézier. |

## Reading order (suggested)

1. `tutorial/01-introduction.md` — install + first diagram.
2. `tutorial/02-diagrams-and-coordinates.md` — elastic vs absolute coords.
3. `tutorial/03-nodes.md` — node basics, shapes, anchors, groups.
4. `tutorial/04-edges.md` — vertices, `auto`, shorthands, anchors, types.
5. `tutorial/05-marks-and-arrows.md` — marks shorthand + table.
6. `tutorial/06-custom-marks.md` — mark objects + special properties.
7. `tutorial/07-cetz-integration.md` — Bézier escape hatch.
8. `tutorial/08-touying.md` — incremental reveals.

After that, every reference page lists its function signature, defaults,
pitfalls, and links to a paired `.typ` example.

## Cross-references

- Fletcher draws on **CeTZ canvases** — see [`guides/cetz/`](../cetz/00-cetz-overview.md) for low-level drawing primitives.
- Fletcher is **independent** of core Typst layout — search with
  `search_fletcher_docs`, not `search_typst_docs`.
