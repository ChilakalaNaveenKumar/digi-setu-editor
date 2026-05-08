# `cylinder` — 3D cylinder

A cylinder shape — commonly used for databases.

## Signature

```typst
cylinder(
  node, extrude,
  fit:    0.6,
  tilt:   8deg,
  rings:  () | length | array = (),
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `fit` | `0.6` | How exactly the cylinder fits the label. |
| `tilt` | `8deg` | Perspective tilt; `0deg` is side-on. |
| `rings` | `()` | Vertical positions to draw decorative arcs (lengths or ratios). |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [DB],   shape: cylinder),
  node((1, 0), [Stack], shape: cylinder.with(rings: (10%, 50%, 90%), tilt: 4deg)),
)
```

See [`examples/13-cylinder/13-cylinder.typ`](examples/13-cylinder/13-cylinder.typ).

## Pitfalls

- Negative `tilt` (e.g. `-2deg`) makes the cylinder look "viewed from
  below" — usually unintended.
- `rings` with all values close together may overlap visually; spread
  them.
- The default `fit: 0.6` is loose; raise to `0.9` for very tight
  labels.
