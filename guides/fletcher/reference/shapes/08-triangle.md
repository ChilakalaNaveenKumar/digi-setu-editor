# `triangle` — isosceles triangle

Isosceles triangle. Either set the apex `angle` *or* the `aspect`
ratio (not both).

## Signature

```typst
triangle(
  node, extrude,
  dir:    top,
  angle:  auto,
  aspect: auto,
  fit:    0.8,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `dir` | `top` | Direction the apex points. |
| `angle` | `auto` | Apex angle (the one opposite the base). |
| `aspect` | `auto` | Base / height ratio. |
| `fit` | `0.8` | How tightly to hug the label. |

If both `angle` and `aspect` are `auto`, the triangle picks an
aspect-equal-to-1 default.

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [Up],   shape: triangle.with(dir: top)),
  node((1, 0), [Down], shape: triangle.with(dir: bottom, angle: 90deg)),
)
```

See [`examples/08-triangle/08-triangle.typ`](examples/08-triangle/08-triangle.typ).

## Pitfalls

- Setting **both** `angle` and `aspect` is undefined behaviour —
  manual says only one should be passed.
- Tall labels with a `dir: top` triangle make the apex very pointy;
  shorten the label or bump `fit` upward.
