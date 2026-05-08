# Shapes — overview

The `fletcher.shapes` submodule defines every node shape Fletcher
ships with. Pass any of them as `shape:` on a `node(...)` (or set the
diagram-wide `node-shape:` default).

```typst
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: diamond, hexagon, brace
```

| Page | Shape | Notable options |
| ---- | ----- | --------------- |
| [`01-rect.md`](01-rect.md) | `rect` | (none — basic rectangle) |
| [`02-circle.md`](02-circle.md) | `circle` | (none — basic circle) |
| [`03-ellipse.md`](03-ellipse.md) | `ellipse` | `scale` |
| [`04-pill.md`](04-pill.md) | `pill` | (none — capsule) |
| [`05-parallelogram.md`](05-parallelogram.md) | `parallelogram` | `angle`, `fit`, `flip` |
| [`06-trapezium.md`](06-trapezium.md) | `trapezium` | `dir`, `angle`, `fit` |
| [`07-diamond.md`](07-diamond.md) | `diamond` | `fit` |
| [`08-triangle.md`](08-triangle.md) | `triangle` | `dir`, `angle`, `aspect`, `fit` |
| [`09-house.md`](09-house.md) | `house` | `dir`, `angle` |
| [`10-chevron.md`](10-chevron.md) | `chevron` | `dir`, `angle`, `fit` |
| [`11-hexagon.md`](11-hexagon.md) | `hexagon` | `angle`, `fit` |
| [`12-octagon.md`](12-octagon.md) | `octagon` | `truncate` |
| [`13-cylinder.md`](13-cylinder.md) | `cylinder` | `fit`, `tilt`, `rings` |
| [`14-stretched-glyph.md`](14-stretched-glyph.md) | `stretched-glyph` | `glyph`, `dir`, `sep`, `length`, `label`, `label-sep` |
| [`15-brace.md`](15-brace.md) | `brace` | wrapper around `stretched-glyph` |
| [`16-bracket.md`](16-bracket.md) | `bracket` | wrapper around `stretched-glyph` |
| [`17-paren.md`](17-paren.md) | `paren` | wrapper around `stretched-glyph` |

## Pattern: `shape.with(...)`

To set a shape parameter, use `.with(..)`:

```typst
node([Slant], shape: parallelogram.with(angle: 30deg))
node([Wide hex], shape: hexagon.with(angle: 45deg, fit: 0.5))
```

## Custom shapes

A shape is a function `(node, extrude, ..parameters) => content` that
returns CeTZ objects. The `node` argument has `.size`, `.corner-radius`,
`.fill`, `.stroke`, etc.; `extrude` is the offset to apply for
multi-stroke effects.

See `src/shapes.typ` in Fletcher's source for full implementations.
