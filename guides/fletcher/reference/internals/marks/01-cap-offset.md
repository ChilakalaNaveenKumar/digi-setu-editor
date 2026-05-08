# `cap-offset(mark, shift)` — where the stroke ends

Computes where the **edge stroke** should terminate, relative to the
mark's origin, as a function of the perpendicular `shift` from the
edge's centerline.

This is what makes multi-stroke marks (e.g. ⇒, ⇛) line up correctly
when extruded to multiple parallel lines.

## Signature

```typst
cap-offset(mark: dict, shift: number) -> number
```

| Arg | Meaning |
| --- | ------- |
| `mark` | A resolved mark dictionary (see `resolve-mark`). |
| `shift` | Perpendicular offset of the stroke from the centerline (in mark units = stroke thicknesses). |

Returns the x-offset (in mark units) at which the stroke should end.

## Visualising

```typst
#context fletcher.mark-debug("O")
```

The dashed green line shows the stroke endpoint as a function of `y`;
the dashed red line is the same for the mark acting as a tail.

See [`examples/01-cap-offset/01-cap-offset.typ`](examples/01-cap-offset/01-cap-offset.typ).

## Pitfalls

- `cap-offset` is **not** about the mark's position along the edge;
  it's about how the edge stroke connects to the mark.
- A custom mark without a `cap-offset` field uses `0` everywhere —
  fine for single-stroke edges but wrong for `extrude: (-1.5, 1.5)`
  multi-stroke edges.
- The default for built-in marks like `head` already encodes the right
  cap geometry; you only need to define your own when designing a new
  mark from scratch.

## Related

- Mark anatomy: [`04-mark-debug.md`](04-mark-debug.md)
- Mark resolution: [`02-resolve-mark.md`](02-resolve-mark.md)
