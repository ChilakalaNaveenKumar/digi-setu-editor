# `cetz.palette.new()` — Build a Cyclic Palette

Creates a new palette function based on a base style and an array of colors
(and optionally dash patterns).

## Signature

```text
cetz.palette.new(
  base:   style,
  colors: none | array = none,
  dash:   none | array = none,
) -> function
```

## Parameters

- **`base`** — base style dictionary used as a template for the styles
  returned for each color.
- **`colors`** — array of colors to cycle through. The returned palette
  function maps an integer index to a style with that color.
- **`dash`** — array of stroke dash patterns to cycle through.

## Returned function

```text
let p = cetz.palette.new(colors: (red, blue, green))
p("len")          // 3
p(0) -> style    // first style
p(1) -> style    // second style
```

The returned style dictionary's named arguments include:

- `fill` *(bool)* — when `true` the fill is the cycled color; otherwise the
  base style's fill is used. Use `red.with(fill: true)` style construction.
- `stroke` *(bool)* — same as above but for stroke.

## Use case

Cycle styles when drawing a series:

```typst
let p = cetz.palette.new(colors: (red, blue, green))
for i in range(0, p("len")) {
  set-style(..p(i))
  circle((0, 0), radius: .5)
  set-origin((1.1, 0))
}
```

You can request stroking via `red.with(stroke: true)` to use the cycled
color for stroke instead of fill.

## Example

See [`examples/01-new/01-new.typ`](./examples/01-new/01-new.typ).
