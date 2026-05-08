# `gategroup()` — labelled rectangle around a block

Draws a rectangle around a contiguous block of cells, optionally with
a label, padding, fill, and corner radius.

## Signature

```typst
gategroup(
  wires:   int,
  steps:   int,
  x:       auto | int = auto,
  y:       auto | int = auto,
  right:   auto | int = auto,
  bottom:  auto | int = auto,
  z:       "below" | "above" = "below",
  padding: length | dictionary = 0pt,
  stroke:  stroke = .7pt,
  fill:    color = none,
  radius:  length | dictionary = 0pt,
  label:   label-shape = none,
)
```

## Sizing modes

- **By extent** — pass `wires` and `steps` (number of rows / columns
  to span starting from the cursor).
- **By corners** — pass `x`, `y`, `right`, `bottom` (absolute cell
  indices). Setting `right` ignores `steps`; setting `bottom` ignores
  `wires`.

## Padding dictionary

```typst
padding: (left: 4pt, right: 4pt, top: 0pt, bottom: 0pt, default: 2pt)
```

Keys: `left`, `right`, `top`, `bottom`, `default`. Missing sides fall
back to `default` (or `0pt` if `default` is absent).

## Examples

```typst
// Inline group spanning 2 wires × 3 columns.
#quantum-circuit(
  1, gate($H$), gategroup(2, 3, label: "syndrome", stroke: blue),
  ctrl(1), $H$, $S$, [\ ],
  3, targ(),
)

// Pinned group placed last in source.
#quantum-circuit(
  1, $H$, $X$, $Y$, 1,
  gategroup(1, 3, x: 1, y: 0, fill: rgb("#a0d8ff40"),
    label: (content: "phase 1", pos: bottom)),
)
```

See [`examples/06-gategroup/06-gategroup.typ`](examples/06-gategroup/06-gategroup.typ).

## Pitfalls

- `gategroup(3, 5)` is *3 wires × 5 columns* — **not** column 3 × row
  5. For absolute coords use `x:` / `y:`.
- `padding: 1.5em` adds inside-the-rectangle padding. The circuit's
  outer bounding box is unaffected; for label clearance set
  `circuit-padding`.
- Default `stroke: .7pt` is solid black. Use a dictionary for dashed
  groups: `stroke: (dash: "dashed", thickness: .5pt)`.

## Related

- Vertical separator: [`slice`](07-slice.md)
- Custom overlay: [`annotate`](08-annotate.md)
- Tutorial: [tutorial 5](../../tutorial/05-slices-and-groups.md)
