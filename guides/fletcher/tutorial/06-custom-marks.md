# 6 — Custom marks

When the built-in marks aren't enough, pass an array of *mark
dictionaries* to the `marks:` option. Each dictionary needs at minimum
a `draw:` field — a CeTZ object centred at `(0, 0)` and scaled so
that one unit equals the stroke thickness.

## A minimal custom mark

```typst
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#import fletcher.cetz.draw

#let my-mark = (
  draw: draw.circle((0, 0), radius: 2, fill: none),
)

#diagram(
  edge((0, 0), (1, 0), stroke: 1pt, marks: (my-mark, my-mark), bend: 30deg),
  edge((0, 1), (1, 1), stroke: 3pt + orange, marks: (none, my-mark)),
)
```

`marks: (start, end)` — pass `none` to leave that side bare.

## Parameters that depend on each other

```typst
#let my-mark = (
  size: 2,
  draw: mark => draw.circle((0, 0), radius: mark.size, fill: none),
)

#diagram(edge(stroke: 3pt, marks: (my-mark + (size: 4), my-mark)))
```

`draw:` may be a function `mark => content` — the mark dictionary is
passed in so any field of `mark` is referenceable.

## Inheriting from a built-in mark

```typst
#let my-mark = (
  inherit: "stealth",
  fill: red,
  stroke: none,
  extrude: (0, -3),
)

#diagram(edge("rr", stroke: 2pt, marks: (my-mark, my-mark + (fill: blue))))
```

`inherit:` looks up the named mark in `fletcher.MARKS` and merges its
properties.

## Special properties

| Property | Default | Effect |
| -------- | ------- | ------ |
| `inherit` | — | Name of mark in `fletcher.MARKS` to inherit from. |
| `draw` | required | CeTZ objects centred at `(0, 0)`. |
| `pos` | `auto` | Position along edge (`0`..`1`). |
| `fill` / `stroke` | `auto` | Defaults inherited from edge stroke. |
| `rev` | `false` | Point backwards. |
| `flip` | `false` | Mirror across the edge. |
| `scale` | `100%` | Per-mark scale factor. |
| `extrude` | `(0,)` | Offsets to duplicate the mark for double / triple strokes. |
| `tip-origin` / `tail-origin` | `0` | x-coord of the mark's point relative to `(0, 0)`. |
| `tip-end` / `tail-end` | `0` | x-coord at which the edge stroke terminates. |
| `cap-offset` | — | Function `(mark, y) => x` for extruded edges. |

See [`reference/internals/marks/04-mark-debug.md`](../reference/internals/marks/04-mark-debug.md) for a tool to visualise these.

## Defining mark shorthands

Modify `fletcher.MARKS` to register your own shorthand:

```typst
#fletcher.MARKS.update(m => m + (
  "<": (inherit: "stealth", rev: true),
  ">": (inherit: "stealth", rev: false),
  "multi": (
    inherit: "straight",
    draw: mark => fletcher.cetz.draw.line(
      (0, +mark.size * calc.sin(mark.sharpness)),
      (-mark.size * calc.cos(mark.sharpness), 0),
      (0, -mark.size * calc.sin(mark.sharpness)),
    ),
  ),
))

// Restore at the end of your document so other diagrams aren't affected:
#fletcher.MARKS.update(fletcher.DEFAULT_MARKS)
```

See [`examples/06-custom-marks/06-custom-marks.typ`](examples/06-custom-marks/06-custom-marks.typ).

## Pitfalls

- The `draw:` content must be in *mark units* — one unit = stroke
  thickness, **not** points. A radius of `2` is "twice the stroke
  thickness."
- `cap-offset` is required for marks where the stroke should end
  *inside* the mark (e.g. multi-stroke edges); without it, the
  trailing line pokes through.
- Updating `fletcher.MARKS` is **global** for the rest of the
  document. Restore via `fletcher.MARKS.update(fletcher.DEFAULT_MARKS)`
  to avoid affecting other diagrams.

## Next

[`07-cetz-integration.md`](07-cetz-integration.md) — drawing things
on the diagram canvas yourself.
