# `curve()` — Vector Drawings

`curve` is Typst's primary vector drawing primitive. A curve is a sequence
of *components* (`curve.move`, `curve.line`, `curve.quad`, `curve.cubic`,
`curve.close`) that describe the pen movements making up the path.

> Replaces the older `path()` function (deprecated since Typst 0.13).

## Signature

```text
curve(
  fill:      none | color | gradient | tiling = none,
  fill-rule: "non-zero" | "even-odd" = "non-zero",
  stroke:    none | auto | length | color | gradient | stroke | tiling | dictionary = auto,
  ..components: content,    // curve.move / line / quad / cubic / close
) -> content
```

If you set `fill`, the default stroke disappears — set `stroke` explicitly
to keep both.

## Components

| Element                                | Effect                                                     |
| -------------------------------------- | ---------------------------------------------------------- |
| `curve.move(point, relative: false)`   | Move the pen without drawing.                              |
| `curve.line(end, relative: false)`     | Straight segment to `end`.                                 |
| `curve.quad(control, end, relative: false)` | Quadratic Bézier; pass `auto` to mirror the previous control, `none` to make it a straight line. |
| `curve.cubic(c1, c2, end, relative: false)` | Cubic Bézier; `c1` may be `auto` (mirror, like SVG `S`) or `none`; `c2` may be `none`. |
| `curve.close(mode: "smooth"\|"straight")` | Closes the current subpath (back to the last `move` point or origin). |

The pen starts at `(0pt, 0pt)`. Pass `relative: true` to interpret a point
as an offset from the previous pen position.

## Multiple subpaths and the fill rule

Each `curve.move` starts a new subpath. With `fill-rule: "even-odd"` you
can punch holes in a shape by drawing inner and outer subpaths in opposite
directions; `"non-zero"` (the default) treats them as merged.

## Tips

- Use `curve.line` with `relative: true` for "turtle-graphics" sketches.
- `auto` on the start control of a `cubic` segment makes a smooth join with
  the previous cubic segment — this is the SVG `S` operator.
- `curve.close(mode: "smooth")` adds a Bézier finishing tangent matching
  the last segment; `"straight"` adds a literal line.

For complex art, prefer drawing in a vector editor and importing as SVG
via [`image`](./06-image.md) — `curve` is great for diagrams, sparklines,
and procedural shapes.
