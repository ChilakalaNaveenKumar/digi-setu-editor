# `compound-path()` — Multi-Subpath Path (with Holes)

Creates a new path whose **sub-paths** are the paths of each child element.
Used to build shapes with holes (rings, donuts, complex glyphs) — similar to
SVG's even-odd / non-zero fill rules.

Unlike [`merge-path`](./17-merge-path.md), `compound-path` keeps the children
as separate sub-paths instead of concatenating them into one continuous path.

## Signature

```text
compound-path(
  body:  elements,
  name:  none | str = none,
  ..style: style,
)
```

## Parameters

- **`body`** — elements whose paths should become sub-paths.
- **`name`** — element name.
- **`..style`** — typically `fill`, `stroke`, and crucially `fill-rule:` —
  one of `"even-odd"` or `"non-zero"`.

## Anchors

- `centroid` — only when `close: true` (passed via style); the centroid of a
  closed, non self-intersecting shape.
- Path anchors via the resulting compound path.

## Pitfalls

- The fill-rule decides whether the inner sub-path "punches" a hole or not.
  `"even-odd"` is the usual choice for ring-shaped fills.

## Example

See [`examples/16-compound-path/16-compound-path.typ`](./examples/16-compound-path/16-compound-path.typ).

## Related

- [`merge-path`](./17-merge-path.md) — concatenates sub-paths into one
  continuous path instead of keeping them separate
- [`drawable.path`](../internals/drawable/04-path.md) — the underlying
  multi-subpath drawable
- [`path-util.make-subpath`](../internals/path-util/01-make-subpath.md) —
  builds the subpath structure children are converted into
