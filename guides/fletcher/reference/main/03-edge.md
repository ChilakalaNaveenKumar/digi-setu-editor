# `edge()` — connecting arrow / line / curve

Connects two or more coordinates. Auto-snaps to nearby nodes; carries
a label, marks (arrowheads), and a stroke.

## Signature

```typst
edge(
  vertices:           array = (),
  label:              content = none,
  label-side:         left | right | center = auto,
  label-pos:          float | ratio | length | array = 50%,
  label-sep:          length = (diagram default),
  label-angle:        angle | direction | auto = 0deg,
  label-anchor:       anchor = auto,
  label-fill:         bool | paint = auto,
  label-size:         length = auto,
  label-wrapper:      function = auto,
  stroke:             stroke = auto,
  dash:               string = none,
  decorations:        none | string | function = none,
  extrude:            array = (0,),
  shift:              length | number | (start, end) = 0pt,
  kind:               "line" | "arc" | "poly" = auto,
  bend:               angle = 0deg,
  loop-angle:         angle = none,
  corner:             none | left | right = none,
  corner-radius:      length | none = auto,
  marks:              array = (),
  mark-scale:         percent = 100%,
  crossing:           bool = false,
  crossing-thickness: number = (diagram default),
  crossing-fill:      paint = (diagram default),
  snap-to:            (start, end) = (auto, auto),
  layer:              number = 0,
  floating:           bool = false,
  post:               function = x => x,
  ..args:             any,
)
```

## Most-used options

| Option | Effect |
| ------ | ------ |
| Mark shorthand string (`"->"`, `"=>"`, `"hook'-/->>"`, …) | Sets `marks:` and stroke style. |
| `bend: angle` | Curve the edge. Implies `kind: "arc"`. |
| `corner: left | right` | Right-angle bend. Implies `kind: "poly"`. |
| `corner-radius` | Rounding for `"poly"` corners. |
| `extrude: (-1.5, 1.5)` | Multi-stroke effect. |
| `shift: 5pt` | Offset perpendicular to the edge direction. |
| `crossing: true` | Draw a backdrop so this edge appears to cross over others. |
| `floating: true` | Wrap the edge so it doesn't affect the bounding box. |
| `decorations: "wave" | "zigzag" | "coil"` | Apply a CeTZ stroke decoration. |
| `snap-to: (<a>, none)` | Force snap targets / disable. |

## Vertex shorthands

The first vertex must be an explicit coord (or `auto`). Subsequent
vertices may be relative shorthand strings:

| Shorthand | Meaning |
| --------- | ------- |
| `"u"`, `"d"`, `"l"`, `"r"` | up, down, left, right |
| `"n"`, `"s"`, `"e"`, `"w"` | north / south / east / west |
| `"ur"`, `"dl"`, … | combinations |
| `"r,d,r"` | comma-separated path |

## Examples

```typst
#diagram(
  spacing: (12mm, 6mm),
  node((0, 0), $A$),
  node((1, 0), $B$),
  edge((0, 0), (1, 0), "<-<<", bend: -25deg, $f$),
  node((-1, -1), $0$),
  edge((-1, -1), (0, 0), "..|>", corner: right, $g$),
)
```

See [`examples/03-edge/03-edge.typ`](examples/03-edge/03-edge.typ).

## Pitfalls

- The marks string and the label can be in either order — Fletcher
  guesses based on type. If a label happens to look like a mark
  string, pass it via `label:` to disambiguate.
- `bend:` and `corner:` are mutually exclusive in practice — `bend`
  forces an arc, `corner` forces a poly.
- `extrude` shifts the *line ends* slightly to make multi-stroke
  marks line up. The shift is computed by `cap-offset()`.
- `floating: true` is the right way to add edges to inline-math
  diagrams without affecting line height.
- For multi-vertex edges, `label-pos` is **not** a fraction of total
  length — pass `(segment, position)` to land on a specific segment.

## Related

- Mark shorthand grammar: [tutorial 5](../../tutorial/05-marks-and-arrows.md)
- Custom marks: [tutorial 6](../../tutorial/06-custom-marks.md)
- Snap & connection points: [tutorial 4](../../tutorial/04-edges.md)
