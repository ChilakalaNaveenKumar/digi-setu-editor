# `node()` — labelled point

Draws a node at a coordinate. Auto-sizes to the label by default.

## Signature

```typst
node(
  pos:           coordinate,
  name:          label | string | none = none,
  label:         content,
  inset:         length = auto,
  outset:        length = auto,
  fill:          paint = auto,
  stroke:        stroke = auto,
  extrude:       array = (0,),
  width:         length | auto = auto,
  height:        length | auto = auto,
  radius:        length,
  enclose:       array = (),
  corner-radius: length = auto,
  shape:         rect | circle | function = auto,
  defocus:       number = auto,
  snap:          number | false = 0,
  layer:         number = auto,
  post:          function = x => x,
  ..args:        any,
)
```

The first positional arg is `pos`, the second is `label`.

## Common options

| Option | Effect |
| ------ | ------ |
| `inset` / `outset` | Padding inside / outside the outline. |
| `fill` / `stroke` | Standard. |
| `extrude` | `(0, 2)` draws double outline at offset 0 and 2 units. |
| `width` / `height` / `radius` | Force a size (label centred unless wrapped in `align`). |
| `enclose` | List of coords / names to enclose — node grows to fit. |
| `shape` | A function `(node, extrude, ..) => content` or an entry from `fletcher.shapes`. |
| `defocus` | Edge-attachment offset for non-square nodes (`0` disables). |
| `snap` | Snap priority for incoming edges. `false` = never snap automatically. |
| `layer` | Z-order; nodes with `enclose` default to `-1`. |
| `post` | `cetz objects => cetz objects` — intercept before drawing. |

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), name: <A>)[$A$],
  node((1, 0), name: <B>)[$B$],
  node(text(white)[$Sigma$], enclose: (<A>, <B>),
    fill: black, layer: -1),
  edge(<A>, <B>, "->"),
)
```

See [`examples/02-node/02-node.typ`](examples/02-node/02-node.typ).

## Pitfalls

- `node((1, 0), [hi])` — first positional is *coord*, second is
  *label*. `node([hi])` alone is invalid.
- Node names are **labels** (`<a>`), not strings — to disambiguate
  from string positional args. A bare string is auto-converted.
- `enclose:` resets `pos` to the centroid; the original coord is no
  longer used to grow the grid.
- `extrude: (0, 2)` adds a *second* outline; just `(2,)` would draw
  *only* the outer one (no inner stroke).
- Custom `shape:` must support extrusion via the `extrude` argument
  or the multi-stroke effect won't work.

## Related

- Shapes: [`reference/shapes/`](../shapes/00-shapes-overview.md)
- Anchors: [tutorial 3](../../tutorial/03-nodes.md)
