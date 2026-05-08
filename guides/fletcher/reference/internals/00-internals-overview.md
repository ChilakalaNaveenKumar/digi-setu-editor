# Internals — overview

The "Behind the scenes" section of the Fletcher manual documents the
**internal helpers** that the public functions (`diagram`, `node`,
`edge`) compose. You usually don't need them, but they are the right
escape hatch when:

- You want to draw extra shapes with CeTZ inside `render:` and need
  the same anchoring logic Fletcher uses (`get-node-anchor`,
  `find-farthest-intersection`).
- You're authoring a custom node `shape:` and need to project
  coordinates between elastic / absolute systems (`uv-to-xy`,
  `xy-to-uv`).
- You're prototyping a custom mark and want to introspect it
  (`mark-debug`, `cap-offset`).

| Folder | Pages | Topics |
| ------ | ----- | ------ |
| [`marks/`](marks/00-marks-overview.md) | 4 | Mark inspection: `cap-offset`, `resolve-mark`, `draw-mark`, `mark-debug`. |
| [`coords/`](coords/00-coords-overview.md) | 6 | Coordinate maps: `uv-to-xy`, `xy-to-uv`, `duv-to-dxy`, `dxy-to-duv`, `vector-polar-with-xy-or-uv-length`, `resolve`. |
| [`diagram/`](diagram/00-diagram-overview.md) | 5 | Layout helpers: `interpret-axes`, `expand-fractional-rects`, `compute-cell-sizes`, `compute-cell-centers`, `compute-grid`. |
| [`node/`](node/00-node-overview.md) | 3 | `measure-node-size`, `resolve-node-enclosures`, `resolve-node-coordinates`. |
| [`edge/`](edge/00-edge-overview.md) | 3 | `interpret-marks-arg`, `interpret-edge-args`, `apply-edge-shift`. ✅ |
| [`draw/`](draw/00-draw-overview.md) | 9 | Drawing primitives: line / arc / polyline + label placement, anchors, `hide`. ✅ |
| [`utils/`](utils/00-utils-overview.md) | 4 | Math helpers: `interp`, `interp-inv`, `get-arc-connecting-points`, `is-space`. ✅ |

## Naming convention

All internal helpers live on the `fletcher` module — call them as
`fletcher.cap-offset(...)`, `fletcher.uv-to-xy(...)`, etc.

The state variables `fletcher.MARKS` and `fletcher.DEFAULT_MARKS` are
also accessible for mark customisation (see
[tutorial 6](../../tutorial/06-custom-marks.md)).
