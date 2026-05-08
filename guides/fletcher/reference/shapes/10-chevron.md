# `chevron` — arrow-shaped block

A chevron (arrow-shape) — useful for direction blocks in process
diagrams.

## Signature

```typst
chevron(
  node, extrude,
  dir:   right,
  angle: 30deg,
  fit:   0.8,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `dir` | `right` | Direction the chevron points. |
| `angle` | `30deg` | Slant of the arrow tip. `0deg` is a rectangle. |
| `fit` | `0.8` | How tightly to hug the label. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  spacing: 5mm,
  node((0, 0), [Step 1], shape: chevron),
  node((1, 0), [Step 2], shape: chevron),
  node((2, 0), [Step 3], shape: chevron),
)
```

See [`examples/10-chevron/10-chevron.typ`](examples/10-chevron/10-chevron.typ).

## Pitfalls

- Adjacent chevrons need very tight `spacing` (sometimes negative
  via `cell-size`) to overlap visually.
- `dir: top` / `dir: bottom` are valid but visually surprising.
