# `draw-mark(mark, stroke, origin, angle, debug)` — render a mark

Renders a mark at a given position and angle inside a CeTZ canvas.
Used by Fletcher's edge renderer; useful in custom `render:` callbacks.

## Signature

```typst
draw-mark(
  mark:   dict,
  stroke: stroke = 1pt,
  origin: point  = (0, 0),
  angle:  angle  = 0deg,
  debug:  bool   = false,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `mark` | required | A *resolved* mark dictionary (see `resolve-mark`). Must contain `draw`. |
| `stroke` | `1pt` | Stroke; the paint is the default fill. |
| `origin` | `(0, 0)` | Where the mark's `tip-origin` lands in canvas coords. |
| `angle` | `0deg` | Direction of the mark; `0deg` is →. |
| `debug` | `false` | If true, draws the origin point. |

## Example (inside a CeTZ canvas)

```typst
#import "@preview/fletcher:0.5.8" as fletcher
#import fletcher.cetz
#cetz.canvas({
  fletcher.draw-mark(
    fletcher.MARKS.get().head,
    stroke: 2pt + black,
    origin: (1, 0),
    angle: 0deg,
  )
})
```

See [`examples/03-draw-mark/03-draw-mark.typ`](examples/03-draw-mark/03-draw-mark.typ).

## Pitfalls

- `mark` must be **already resolved** (use `resolve-mark` first if
  you built it by hand).
- `origin` is in CeTZ canvas units, *not* mark units.
- `angle: 0deg` points the mark to the right; rotate by 90deg for an
  upward-pointing mark.

## Related

- Resolution: [`02-resolve-mark.md`](02-resolve-mark.md)
- Anatomy: [`04-mark-debug.md`](04-mark-debug.md)
