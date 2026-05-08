# `mark-debug(mark, ...)` — visualise a mark's anatomy

Renders a mark together with annotations: the four origin / end
points (`tip-origin`, `tail-origin`, `tip-end`, `tail-end`), the
green/red strokes, and the dashed `cap-offset` curves.

## Signature

```typst
mark-debug(
  mark:         string | dict,
  stroke:       stroke = 5pt,
  show-labels:  bool   = true,
  show-offsets: bool   = true,
  offset-range: number = 6,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `mark` | required | Mark name (e.g. `"stealth"`) or dictionary. |
| `stroke` | `5pt` | Big stroke so the mark is easy to read. |
| `show-labels` | `true` | Toggle label text. |
| `show-offsets` | `true` | Toggle the dashed cap-offset curves. |
| `offset-range` | `6` | Vertical span of the cap-offset visualisation in stroke units. |

## Example

```typst
#context {
  let mark = fletcher.MARKS.get().stealth + (angle: 45deg)
  fletcher.mark-debug(mark)
}
```

See [`examples/04-mark-debug/04-mark-debug.typ`](examples/04-mark-debug/04-mark-debug.typ).

## Pitfalls

- Use `mark-debug` on a **single** mark at a time — it draws a
  full-page diagnostic picture.
- The result is large by default; reduce `stroke` to shrink.

## Related

- Cap geometry: [`01-cap-offset.md`](01-cap-offset.md)
- Resolution: [`02-resolve-mark.md`](02-resolve-mark.md)
- Drawing: [`03-draw-mark.md`](03-draw-mark.md)
