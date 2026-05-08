# `path()` — Deprecated, use `curve` instead

`path` is the **deprecated** predecessor of [`curve`](./03-curve.md), kept
for backward compatibility. New code should reach for `curve` and its
explicit `curve.move`/`curve.line`/`curve.cubic` components — they are
strictly more expressive and the only ones that will be supported going
forward.

> Typst 0.13 deprecated `path`. The function still works (and compiles
> with a warning) but will eventually be removed.

## Signature (for reference)

```text
path(
  fill:      none | color | gradient | tiling = none,
  fill-rule: "non-zero" | "even-odd" = "non-zero",
  stroke:    none | auto | length | color | gradient | stroke | tiling | dictionary = auto,
  closed:    bool = false,
  ..vertices: array | (point, control) | (point, c-in, c-out)
) -> content
```

A vertex may be:

1. A plain point `(x, y)` — straight segment.
2. `(point, control)` — the control is **mirrored** to produce a smooth
   Bézier through `point`.
3. `(point, c-in, c-out)` — explicit incoming/outgoing controls.

## Migrating to `curve`

| `path(...)` written as                                            | `curve(...)` equivalent                                  |
| ----------------------------------------------------------------- | ------------------------------------------------------- |
| `path((0pt, 0pt), (50pt, 0pt), (25pt, 50pt), closed: true)`       | `curve(curve.line((50pt, 0pt)), curve.line((25pt, 50pt)), curve.close())` |
| `path((0pt, 50pt), ((50pt, 0pt), (40pt, 0pt)))`                   | `curve(curve.move((0pt, 50pt)), curve.cubic(none, (40pt, 0pt), (50pt, 0pt)))` |

Use this page only if you must read older Typst code; otherwise jump to
[`curve`](./03-curve.md) for the supported API.
