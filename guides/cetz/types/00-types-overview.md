# CeTZ — Types Glossary

CeTZ uses a small, consistent set of *types* throughout its API. None of
them are Typst classes — they're conventions on top of Typst primitives
(arrays, dictionaries, strings, …) that the engine and every shape /
helper agree on.

This page is the canonical reference for what each type *is*, where it
shows up, and where the rest of the docs go deeper.

## Public types

These appear in user-facing signatures (`canvas`, every shape, every
library function).

### `coordinate`

A position on the canvas. Any of the supported coordinate forms:

| Form | Example | Read more |
| ---- | ------- | --------- |
| 3D xyz tuple | `(1, 2, 0)` | [tutorial/03-coordinates.md](../tutorial/03-coordinates.md) |
| 2D xyz tuple (z = 0) | `(1, 2)` | same |
| Polar | `(45deg, 1.5)` | same |
| Anchor string | `"my-circle.east"` | [tutorial/04-anchors.md](../tutorial/04-anchors.md) |
| Relative dictionary | `(rel: (1, 0))` | tutorial 03 |
| Path interpolation | `"my-line.50%"` | tutorial 03 |
| Barycentric | `(bary: (a: 0.5, b: 0.5))` | tutorial 03 |
| Lerp / tangent / perpendicular / project-point-on-line | `(lerp: ("a", "b", 0.5))` | tutorial 03 |
| Function form | `(ctx => …)` | tutorial 03 |

> Internally these get classified by
> [`coordinate.resolve-system`](../reference/internals/coordinate/01-resolve-system.md)
> and converted into a 3-component float vector by
> [`coordinate.resolve`](../reference/internals/coordinate/02-resolve.md).

### `number`

Any of `int`, `float`, or a Typst `length`. Lengths are coerced into
canvas units via
[`util.resolve-number`](../reference/internals/util/10-resolve-number.md).

### `style`

The collection of named arguments that affect how an element is drawn —
e.g. `fill: red`, `stroke: 1pt + black`, `radius: 0.5`. Every shape
accepts these as `..style: style` and merges them with the inherited
style tree via
[`styles.resolve`](../reference/internals/styles/01-resolve.md) and
[`styles.merge`](../reference/internals/styles/02-merge.md).

See [tutorial/05-styling.md](../tutorial/05-styling.md) for the
inheritance model and per-element style roots.

### `stroke`

A Typst `stroke` value — a number, color, length, dictionary, or
`stroke()` call. Coerced by
[`util.resolve-stroke`](../reference/internals/util/20-resolve-stroke.md).

### `color`

A standard Typst color — `red`, `rgb("#3366ff")`, `gradient.linear(…)`,
etc.

### `padding`

A `number`, 2-tuple, 4-tuple, or dictionary `(top, right, bottom, left)`.
Coerced by
[`util.as-padding-dict`](../reference/internals/util/17-as-padding-dict.md).

## Internal types

These don't appear in user-facing signatures but show up everywhere
inside the engine and the `internals/` reference.

### `vector`

A Typst array of 3 floats `(x, y, z)`. The 2-element form `(x, y)` is
auto-padded by
[`vector.as-vec`](../reference/internals/vector/02-as-vec.md). All
vector math lives in
[`cetz.vector`](../reference/internals/vector/00-vector-overview.md).

### `matrix`

A Typst array of arrays — a list of rows, each row a list of column
entries. CeTZ uses 4×4 affine transforms throughout. Builders and
operators live in
[`cetz.matrix`](../reference/internals/matrix/00-matrix-overview.md).

### `complex`

A 2-element tuple `(re, im)`. Pure-math helpers live in the (unexposed)
[`complex` source module](../reference/internals/complex/00-complex-overview.md).

### `bounds`

A dictionary `(low: vector, high: vector)` describing an axis-aligned
bounding box. Manipulators live in
[`cetz.aabb`](../reference/internals/aabb/00-aabb-overview.md).

### `subpath`

A 3-tuple `(origin: vector, segments: array, closed: bool)` describing
a single connected path. Built by
[`path-util.make-subpath`](../reference/internals/path-util/01-make-subpath.md).

### `path`

A Typst array of `subpath`s. The standard input to
[`drawable.path`](../reference/internals/drawable/04-path.md).

### `segment`

A line or cubic Bézier section inside a `subpath`:

| Kind | Tuple | Meaning |
| ---- | ----- | ------- |
| line | `("l", end-point)` | straight segment ending at `end-point` |
| cubic | `("c", c1, c2, end-point)` | cubic Bézier with off-curve controls `c1`, `c2` |

### `drawable`

The renderable dictionary the engine emits for every primitive — has at
least `type` (`"path"`, `"content"`, etc.), the geometry, and optional
`fill` / `stroke` / `tags`. Constructed by the builders in
[`cetz.drawable`](../reference/internals/drawable/00-drawable-overview.md).

### `mark style`

A dictionary describing arrowheads / bars / dots placed on path shapes —
keys like `start`, `end`, `pos`, `length`, `width`, `inset`, `symbol`,
`flex`, `harpoon`, `slant`. Validated by
[`mark.check-mark`](../reference/internals/mark/01-check-mark.md).

### `palette`

A function returned by
[`cetz.palette.new`](../reference/libraries/palette/01-new.md) that, when
called with an integer, returns a style dictionary with a cyclic colour
/ dash combination.

### `tree node`

A dictionary the
[`cetz.tree.tree`](../reference/libraries/tree/03-tree.md) walker hands
to its `draw-node` / `draw-edge` callbacks. Keys: `name`, `group-name`,
`depth`, `n`, `content`.

## See also

- [Tutorial — Coordinates](../tutorial/03-coordinates.md)
- [Tutorial — Anchors](../tutorial/04-anchors.md)
- [Tutorial — Styling](../tutorial/05-styling.md)
- [Reference — Internals overview](../reference/internals/00-internals-overview.md)
