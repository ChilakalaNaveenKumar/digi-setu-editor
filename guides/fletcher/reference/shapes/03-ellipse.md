# `ellipse` — elliptical shape

Hugs the label aspect ratio more closely than `circle`.

## Signature

```typst
ellipse(node, extrude, scale: 1)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `scale` | `1` | Scale factor for the ellipse radii. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [wide label], shape: ellipse),
  node((1, 0), [wide label], shape: ellipse.with(scale: 1.4)),
)
```

See [`examples/03-ellipse/03-ellipse.typ`](examples/03-ellipse/03-ellipse.typ).

## Pitfalls

- `scale: 0` collapses the ellipse to a degenerate point.
- Combine with `width: ...` and `height: ...` to force a specific
  ellipse size.
