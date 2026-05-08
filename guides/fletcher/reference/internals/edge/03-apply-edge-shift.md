# `apply-edge-shift(grid, edge)` — translate edge endpoints

Apply the `shift:` option of `edge(...)` by **translating the edge's
vertices perpendicular to its direction**. This is what keeps parallel
edges between the same two nodes from overlapping.

## Signature

```typst
apply-edge-shift(
  grid: dict,    // computed grid; needed when `shift` is a length
  edge: dict,    // edge with a `shift` entry
) -> dict        // edge with translated vertices
```

## What it does

`shift` may be:

| Form | Meaning |
| --- | --- |
| `0` | No shift (default). |
| number `n` | Shift by `n × stroke-thickness` perpendicular to the edge. |
| `length` | Shift by that absolute physical length. |
| `(a, b)` | First/last vertex shifted by `a` / `b` independently (asymmetric). |

The shift direction is the *perpendicular* of the edge's local
tangent, which is why `apply-edge-shift` needs the grid (so it can
compute the edge's actual angle in xy space).

## Example — three parallel arrows

```typst
#diagram(
  spacing: (24mm, 8mm),
  node-stroke: none,
  node((0, 0), $A$),
  node((1, 0), $B$),
  edge((0, 0), (1, 0), "->", $f$, shift: -4pt),
  edge((0, 0), (1, 0), "->", $g$),
  edge((0, 0), (1, 0), "->", $h$, shift: +4pt),
)
```

See [`examples/03-apply-edge-shift/03-apply-edge-shift.typ`](examples/03-apply-edge-shift/03-apply-edge-shift.typ).

## Pitfalls

- A *length* `shift:` ignores stroke thickness — use a number when
  you want it to scale with `edge-stroke:`.
- `shift:` happens **after** vertex resolution, so combining it with
  `snap-to:` may cause the shifted endpoint to no longer hit the
  expected anchor.

## Related

- `edge(shift: …)` user-facing option.
- [`interpret-edge-args`](02-interpret-edge-args.md) — runs first.
- [Tutorial: edges](../../../tutorial/04-edges.md)
