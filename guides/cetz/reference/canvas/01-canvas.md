# `canvas()` — The Drawing Envelope

Sets up a canvas for drawing on. Returns `content` that auto-sizes to the
bounding box of everything drawn inside the body.

## Signature

```text
cetz.canvas(
  length:     length        = 1cm,
  x:          number | vector,
  y:          number | vector,
  z:          number | vector,
  baseline:   none | number | coordinate = none,
  debug:      bool          = false,
  background: none | color  = none,
  stroke:     none | stroke = none,
  padding:    none | number | array | dictionary = none,
  body        none | array | element,
) -> content
```

## Parameters

- **`length`** — what one coordinate unit equals. Default `1cm`. Ratios are
  not supported here; for percentage-of-page sizing wrap in `layout(ly =>
  cetz.canvas(length: ly.width * <ratio>, ...))`.
- **`baseline`** — coordinate to use as the inline baseline. When set, the
  canvas behaves like a `box` element instead of a `block`.
- **`body`** — a code block in which functions from the `cetz.draw` module
  have been called.
- **`background`** — color filling the canvas's container.
- **`stroke`** — stroke applied to the outer canvas element (box/block).
  Useful for visualising padding.
- **`padding`** — extra space around the bounding box. `none` = none,
  `<number>` = same on all sides, dictionary follows Typst's `pad`,
  array follows CSS shorthand `(y, x)`, `(top, x, bottom)`, or
  `(top, right, bottom, left)`.
- **`x` / `y` / `z`** — basis vectors of the coordinate system. A scalar
  sets `(x, 0, 0)` etc.; a 3-vector sets the axis directly. Use this to
  scale, skew, or reverse axes.
- **`debug`** — when `true`, the bounding box of every element is rendered.

## Anchors

`canvas(...)` itself doesn't expose anchors — anchors live on the elements
*inside* the body. The canvas just contains them.

## Pitfalls

- **Always `import cetz.draw: *` inside the body.** Many draw functions share
  names with Typst built-ins (`line`, `rect`, `circle`, `content`, …).
  Importing them inside the canvas body keeps the override scoped.
- **`length:` does not accept ratios.** Wrap in `layout(...)` for
  percentage-of-parent sizing.
- **`y` grows upward** — opposite of Typst layout flow.
- The canvas auto-resizes around hidden / floating elements based on their
  `bounds` flag. See [`hide`](../grouping/01-hide.md) and
  [`floating`](../grouping/02-floating.md).

## Example

See [`examples/01-canvas/01-canvas.typ`](./examples/01-canvas/01-canvas.typ).
