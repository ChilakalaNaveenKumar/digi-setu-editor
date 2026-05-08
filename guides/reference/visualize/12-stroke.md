# `stroke` — Line Appearance

`stroke` is the type that describes how Typst draws line-like things —
borders of shapes, ruled lines, the outline of curves and polygons.

You almost never construct one by hand: most parameters that accept a
stroke also accept a `length`, a `color`, or a `length + color`
combination, and Typst converts implicitly.

## Shorthand

| Value passed                   | Resulting stroke                                |
| ------------------------------ | ----------------------------------------------- |
| `2pt`                          | 2pt thick, color inherited (defaults to black). |
| `red`                          | 1pt thick (default), red.                       |
| `2pt + red`                    | 2pt thick, red.                                 |
| `(paint: blue, thickness: 1pt, dash: "dashed")` | Full dictionary form.          |
| `stroke(...)`                  | Explicit constructor (all defaults inheritable).|

A dictionary may set any of the constructor's fields below; missing fields
default to `auto` (= "inherit from context").

## Constructor

```text
stroke(
  paint:        auto | color | gradient | tiling = auto,   // default black
  thickness:    auto | length             = auto,          // default 1pt
  cap:          auto | "butt" | "round" | "square" = auto, // default "butt"
  join:         auto | "miter" | "round" | "bevel" = auto, // default "miter"
  dash:         none | auto | str | array | dictionary = auto, // default none (solid)
  miter-limit:  auto | float = auto,                       // default 4.0
) -> stroke
```

`auto` means **inherit** from the surrounding context (e.g. a `set rect(stroke: ...)`).

### Fields

After construction you can read every field back: `(2pt + blue).thickness ==
2pt`, `stroke(red).cap == auto`. Inheritable defaults stay `auto` until
they're resolved.

## Caps and joins

| `cap`        | Visual                                                     |
| ------------ | ---------------------------------------------------------- |
| `"butt"`     | Square cap exactly at the endpoint.                        |
| `"round"`    | Circular cap centered at the endpoint (extends past it).   |
| `"square"`   | Square cap centered at the endpoint (extends past it).     |

| `join`       | Visual                                                     |
| ------------ | ---------------------------------------------------------- |
| `"miter"`    | Sharp angle (becomes bevel beyond `miter-limit`).          |
| `"round"`    | Circular corner.                                           |
| `"bevel"`    | Flat cut between segments.                                 |

`miter-limit` (default `4.0`) is the maximum ratio of corner-protrusion to
stroke-thickness before a `"miter"` join falls back to a bevel. Lower
values produce more bevels; higher ones allow sharper points.

## Dash patterns

Built-in patterns: `"solid"` (== `none`), `"dotted"`, `"densely-dotted"`,
`"loosely-dotted"`, `"dashed"`, `"densely-dashed"`, `"loosely-dashed"`,
`"dash-dotted"`, `"densely-dash-dotted"`, `"loosely-dash-dotted"`.

You can also pass an array describing the on/off lengths (mix `length` and
`"dot"` for dots that follow `thickness`):

```typst
#line(length: 100%, stroke: (
  thickness: 2pt,
  dash: (10pt, 5pt, "dot", 5pt),
))
```

For more control, pass a dictionary:

```typst
#line(length: 100%, stroke: (
  dash: (array: (10pt, 5pt, "dot", 5pt), phase: 10pt),
))
```

`phase` shifts the start position of the dash pattern.

## Per-side strokes (rectangle, square)

When passed to `rect`/`square`, `stroke` may be a dictionary keyed by
`top`, `right`, `bottom`, `left`, `x`, `y`, `rest`. See the
[`rect` page](./10-rect.md#stroke-accepts-a-per-side-dictionary).
