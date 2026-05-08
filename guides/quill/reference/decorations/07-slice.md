# `slice()` — vertical phase boundary

A vertical line between columns marking a phase of the computation.
Default style is a dashed red line at `0.7pt`.

## Signature

```typst
slice(
  n:      int = 0,
  x:      auto | int = auto,
  y:      auto | int = auto,
  z:      "below" | "above" = "below",
  stroke: stroke = (paint: red, thickness: .7pt, dash: "dashed"),
  label:  label-shape = none,
)
```

| Arg | Meaning |
| --- | ------- |
| `n` | Number of wires to slice down. Default `0` = "all the way down". |
| `x` / `y` | Optional manual placement. |
| `stroke` | Slice line stroke. |
| `label` | Slice label (defaults to top-anchored above the line). |
| `z` | Draw above or below the gates. |

## Examples

```typst
// Plain phase boundary across all wires.
#quantum-circuit(
  1, $H$, slice(label: "1"), ctrl(1), 1, [\ ],
  1, 1, targ(), 1
)

// Limited slice (top two wires only) with custom stroke.
#quantum-circuit(
  1, $H$, slice(label: "2", n: 2, stroke: blue), ctrl(1), 1, [\ ],
  1, 1, targ(), 1, [\ ],
  3, $X$,
)
```

See [`examples/07-slice/07-slice.typ`](examples/07-slice/07-slice.typ).

## Pitfalls

- Default `n: 0` reaches the **bottom** of the circuit. Pass an
  explicit `n: 2` (or any positive value) to limit the height.
- The slice's column is **between** the previous and next columns —
  put it where you want the boundary, not on a gate.
- `slice` ignores `padding` (unlike `gategroup`). To breath room,
  insert a length item next to the slice.

## Related

- Box around a region: [`gategroup`](06-gategroup.md)
- Custom overlay: [`annotate`](08-annotate.md)
- Tutorial: [tutorial 5](../../tutorial/05-slices-and-groups.md)
