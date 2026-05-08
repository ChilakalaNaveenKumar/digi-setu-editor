# `line()` — Line / Polyline / Polygon

Draws a line. With more than two coordinates the result is a poly-line; with
`close: true` it becomes a polygon.

## Signature

```text
line(
  ..pts-style: coordinate | style,
  close: bool      = false,
  name:  none | str = none,
)
```

## Forms

| Call | Result |
| ---- | ------ |
| `line(p1, p2)` | Single segment. |
| `line(p1, p2, p3, …)` | Open polyline. |
| `line(p1, …, pN, close: true)` | Closed polygon. |
| `line("a", "b")` | Border-to-border line between named elements `a` and `b`. |

When the first or last coordinate is the **name of an element** (and that
element has a `default` anchor), CeTZ extends the line until it intersects
the element's border. Useful for connecting two shapes:

```typst
circle((1, 2), radius: .5, name: "a")
rect((2, 1), (rel: (1, 1)), name: "b")
line("a", "b")
```

## Styling

- **Root:** `line`
- Inherits `fill`, `stroke`, `mark` (sub-style).

## Anchors

Path anchors. For a closed non self-intersecting polygon whose vertices share
the same z, also `centroid`.

## Pitfalls

- Polylines that close back on themselves don't get a centroid anchor unless
  `close: true`.
- A `fill` only fills the implied closed area when `close: true`.

## Example

See [`examples/06-line/06-line.typ`](./examples/06-line/06-line.typ).

## Related

- [`drawable.line-strip`](../internals/drawable/05-line-strip.md) — the
  underlying polyline drawable
- [`util.line-pt`](../internals/util/05-line-pt.md) — point-on-line math
- [`util.line-normal`](../internals/util/06-line-normal.md) — perpendicular direction
- [`intersection.line-line`](../internals/intersection/01-line-line.md) — line-line intersection
