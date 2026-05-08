# `line()` — Straight Lines

`line` draws a straight segment. You either give it a `start` plus an `end`,
or a `start` plus a `length` and `angle`.

## Signature

```text
line(
  start:  array = (0pt, 0pt),     // (x, y) relative to current container
  end:    none | array = none,    // (x, y); if set, length & angle are ignored
  length: relative = 30pt,        // used when `end` is `none`
  angle:  angle = 0deg,           // 0deg = pointing right, clockwise positive
  stroke: length | color | gradient | stroke | tiling | dictionary = 1pt + black,
) -> content
```

## Two ways to point a line

**By endpoint** — `line(end: (50%, 30pt))` draws from `(0pt, 0pt)` to that
point.

**By length and angle** — `line(length: 4cm, angle: 30deg)` draws a 4 cm
segment rotated 30° clockwise from horizontal.

## Stroking

`line` accepts the full [`stroke`](./12-stroke.md) vocabulary:

```typst
#line(length: 100%, stroke: 2pt + red)
#line(length: 100%, stroke: (paint: blue, thickness: 1pt, dash: "dashed"))
#line(length: 100%, stroke: (paint: blue, thickness: 4pt, cap: "round"))
```

## Common patterns

| Use case                 | Snippet                                             |
| ------------------------ | --------------------------------------------------- |
| Full-width horizontal rule | `#line(length: 100%)`                             |
| Signature line           | `#line(length: 5cm, stroke: 0.5pt)`                 |
| Vertical separator       | `#line(length: 1cm, angle: 90deg)`                  |
| Diagonal pointer         | `#line(end: (40pt, -30pt), stroke: 1pt + red)`      |
| Dashed underline         | `#line(length: 100%, stroke: (dash: "dashed"))`     |

## Tips

- For a rule that spans the full text width, set `length: 100%`.
- For diagonal lines, prefer `end:` over `length` + `angle` — the geometry
  is easier to reason about.
- Need arrows? Compose `line` with small `polygon` / `curve` arrowheads or
  reach for the [`fletcher`](https://typst.app/universe/package/fletcher)
  package.
