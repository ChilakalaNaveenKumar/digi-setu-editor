# `circle()` — Circle / Ellipse

Draws a circle or ellipse.

## Signature

```text
circle(
  ..points-style: coordinate | style,
  name:   none | str = none,
  anchor: none | str = none,
)
```

Plus the style key:

- **`radius`** — `number | array`. A single number sets the circle radius;
  a 2-tuple `(rx, ry)` makes an ellipse.

## Forms

| Form | Example | Effect |
| ---- | ------- | ------ |
| `circle(p)` | `circle((0, 0))` | Circle centred at `p`, radius from style. |
| `circle(p, radius: r)` | `circle((0, 0), radius: 2)` | Sets radius inline. |
| `circle(p, radius: (rx, ry))` | `circle((2, 0), radius: (1, 0.5))` | Ellipse. |
| `circle(a, b)` | `circle((2,1), (1,1))` | Circle centred at `a`, passing through `b`. |

## Styling

- **Root:** `circle`
- Inherits the universal `fill` and `stroke` keys.

## Anchors

Supports **border anchors** and **path anchors**. The default anchor is
`center`.

## Pitfalls

- Setting a `fill` does **not** automatically remove the default 1pt black
  stroke (different from Typst's `circle`).
- For a circle through *three* points use [`circle-through`](./02-circle-through.md).
- For partial arcs use [`arc`](./03-arc.md) or [`arc-through`](./04-arc-through.md).

## Example

See [`examples/01-circle/01-circle.typ`](./examples/01-circle/01-circle.typ).

## Related

- [`circle-through`](./02-circle-through.md) — circle through 3 points
- [`drawable.ellipse`](../internals/drawable/07-ellipse.md) — the
  underlying low-level drawable
- [`util.calculate-circle-center-3pt`](../internals/util/09-calculate-circle-center-3pt.md)
  — circumcentre math used by `circle-through`
