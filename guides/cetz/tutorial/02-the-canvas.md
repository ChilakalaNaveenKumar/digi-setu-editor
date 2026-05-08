# 02 — The Canvas

> **Source:** `manual.pdf` §3.2 + §4.1

The `canvas(...)` function is the only entry-point CeTZ exposes. Everything
else lives in submodules (`cetz.draw`, `cetz.angle`, `cetz.tree`, `cetz.vector`,
`cetz.matrix`, …).

```typst
#cetz.canvas({
  import cetz.draw: *
  // body of the canvas
})
```

Typst evaluates the code block, hands the result to `canvas`, and the result
is rendered as a single content element (block-level by default, inline if
`baseline` is set).

## Sizing — there is no width/height

The canvas does **not** take `width`/`height` parameters; it grows and shrinks
to fit the drawn graphic. Two knobs that do affect size:

| Parameter | Default | Effect |
| --------- | ------- | ------ |
| `length:` | `1cm` | what one coordinate unit is worth |
| `padding:` | `none` | extra space around the bounding box |

Ratios are *not* supported on `length:`. For a percentage-of-page sized
canvas, use a layout block:

```typst
#layout(ly => cetz.canvas(length: ly.width * 50%, {
  import cetz.draw: *
  rect((0, 0), (1, 0.5))
}))
```

## Setting up the coordinate system

By default `x = (1, 0, 0)`, `y = (0, 1, 0)`, `z = (0, 0, 1)` — a right-handed
system with `+y` up. You can pass:

```typst
#cetz.canvas(x: 2, {              // 1 unit on x = 2 unit lengths
  import cetz.draw: *
  rect((0, 0), (1, 1))
})
```

…or supply a full vector to skew/rotate the basis.

## Debug rendering

Set `debug: true` to draw the bounding box of every element — invaluable
when an `intersections(...)` or anchor query is producing the wrong point.

```typst
#cetz.canvas(debug: true, {
  import cetz.draw: *
  circle((0, 0))
  rect((1, 0), (3, 1))
})
```

## Inline vs block

By default the canvas is **block-level** (like `figure(...)` content). Pass
`baseline:` to make it behave like a `box` — useful for inline icons:

```typst
A wee circle: #cetz.canvas(baseline: (0, 0), length: 0.5em, {
  import cetz.draw: *
  circle((0, 0), radius: 0.6, fill: blue)
}) finishes the sentence.
```

## Background and stroke

Pass `background: <color>` to fill the canvas's container, and `stroke:` to
stroke its outer envelope (useful for visualising padding).

## See also

- The full reference for `canvas(...)`: [`../reference/canvas/01-canvas.md`](../reference/canvas/01-canvas.md)
- Padding helper module: [`../reference/internals/util/17-as-padding-dict.md`](../reference/internals/util/17-as-padding-dict.md)
- Setting the previous coordinate manually:
  [`../reference/transformation/07-move-to.md`](../reference/transformation/07-move-to.md)
