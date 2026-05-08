# Marks internals — overview

Helpers that operate on **mark dictionaries** (the data model behind
arrowheads). Use them when you author custom marks or want to
introspect Fletcher's defaults.

| Page | Function | What it does |
| ---- | -------- | ------------ |
| [`01-cap-offset.md`](01-cap-offset.md) | `cap-offset(mark, shift)` | Where the stroke should terminate relative to the mark origin, as a function of vertical offset. |
| [`02-resolve-mark.md`](02-resolve-mark.md) | `resolve-mark(mark, defaults)` | Apply `inherit`, fill in defaults, evaluate closures. |
| [`03-draw-mark.md`](03-draw-mark.md) | `draw-mark(mark, stroke, origin, angle, debug)` | Render a mark at a given position and angle. |
| [`04-mark-debug.md`](04-mark-debug.md) | `mark-debug(mark, ...)` | Visualise a mark's anatomy (tip-end, tail-end, …). |

## Mark registry

`fletcher.MARKS` is a Typst state holding the named-mark catalog.
Read with:

```typst
#context fletcher.MARKS.get()
```

`fletcher.DEFAULT_MARKS` holds the immutable factory defaults.

## Drawing a mark by hand

`draw-mark(...)` is rarely called directly — it's the building block
used by Fletcher's edge renderer. Useful when you build a custom
`render:` callback and want a mark to "match" the rest of the diagram.
