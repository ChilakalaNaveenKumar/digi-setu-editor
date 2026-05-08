# `interpret-axes(axes)` — normalise the `axes:` argument

Convert Fletcher's `axes:` argument into a canonical form used by the
rest of the layout pipeline.

## Signature

```typst
interpret-axes(axes: (direction, direction)) -> (direction, direction)
```

## What it does

- Accepts a 2-tuple `(horizontal-axis, vertical-axis)`.
- Each axis must be one of `ltr` / `rtl` / `ttb` / `btt`.
- The two axes must be perpendicular — otherwise raises a panic.
- Returns the same tuple (possibly normalised) so other helpers can
  rely on the structure.

## Example (call site you'd never normally touch)

```typst
let (h, v) = fletcher.interpret-axes((rtl, btt))
// h == rtl, v == btt
```

See [`examples/01-interpret-axes/01-interpret-axes.typ`](examples/01-interpret-axes/01-interpret-axes.typ).

## Pitfalls

- Public users typically pass `axes:` directly to `diagram(...)`; only
  reach for `interpret-axes` if you re-implement layout yourself.
- Two horizontal axes (or two vertical axes) raise an error.

## Related

- `diagram(axes: …)` — the user-facing entry point.
- [`compute-grid`](05-compute-grid.md) consumes the normalised axes.
