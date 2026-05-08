# Internals — Overview

> See also: [Types Glossary](../../types/00-types-overview.md) for the
> shape of `vector`, `matrix`, `complex`, `bounds`, `path`, `subpath`,
> `segment`, `drawable`, and `mark style` — the data types these
> internal modules consume and produce.

CeTZ ships a number of internal modules that are documented in the
upstream manual under §4.9. They are split into two groups:

- **Re-exported modules** (reachable as `cetz.<module>.<fn>(...)`):
  `vector`, `matrix`, `coordinate`, `styles`, `process`, `drawable`,
  `mark`, `intersection`, `path-util`, `util`.
- **Source-only modules** (documented but **not** re-exported by
  `cetz/lib.typ`): `complex`, `bezier`, `aabb`, `hobby`, `anchor`. To
  call these from your own code you would have to vendor the
  corresponding `cetz/src/<module>.typ` file. Their `.typ` examples in
  this folder demonstrate either the user-facing equivalent (a
  `cetz.draw` shape that uses the function internally) or a small
  hand-rolled re-implementation.

| Module | Responsibility | Folder |
| ------ | -------------- | ------ |
| `complex` | 2-D complex-number arithmetic on `(re, im)` pairs | [`complex/`](./complex/) |
| `vector` | 3- and 4-component vector arithmetic | [`vector/`](./vector/) |
| `matrix` | 4 × 4 matrix builders, multiplication, inverse | [`matrix/`](./matrix/) |
| `coordinate` | Resolve coordinate strings/objects to vectors | [`coordinate/`](./coordinate/) |
| `styles` | Style-folding algorithm | [`styles/`](./styles/) |
| `process` | Element-evaluation pipeline | [`process/`](./process/) |
| `drawable` | Low-level drawable constructors | [`drawable/`](./drawable/) |
| `anchor` | Anchor calculation infrastructure | [`anchor/`](./anchor/) |
| `mark` | Mark/arrowhead processing | [`mark/`](./mark/) |
| `bezier` | Bezier-math toolkit | [`bezier/`](./bezier/) |
| `aabb` | Axis-aligned bounding-box helpers | [`aabb/`](./aabb/) |
| `hobby` | Hobby-curve algorithm | [`hobby/`](./hobby/) |
| `intersection` | Geometric intersection finders | [`intersection/`](./intersection/) |
| `path-util` | Path inspection and manipulation | [`path-util/`](./path-util/) |
| `util` | Misc helpers (`measure`, `resolve-number`, `min`, `max`, …) | [`util/`](./util/) |

## When to reach for these

- You want to compute coordinates from existing anchors before passing them
  to a draw call → use `coordinate.resolve` inside `get-ctx`.
- You want raw bezier math (find a point at `t`, split a curve, etc.) → use
  the `bezier` module — these don't need `get-ctx`.
- You're writing a custom mark or anchor → use `mark` and `anchor`.
- You're debugging style folding → use `styles.resolve` to mimic CeTZ's
  inheritance.

The `.typ` examples in this folder use `cetz.canvas({ … })` plus a
`content(()`+`repr(...)`+`)` pattern to print the result of pure helpers so
the file actually compiles to a viewable PDF.
