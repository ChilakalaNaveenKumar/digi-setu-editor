# 5 — Slices and gate groups

To structure a circuit visually, Quill provides two decorations:

- `slice(...)` — a vertical line between columns marking a "phase".
- `gategroup(wires, steps, ...)` — a labelled rectangle around a
  contiguous block of cells.

Both are inserted **inline** at the column where the slice / group
should *begin*. They take a `label` argument (more in
[`06-labels.md`](06-labels.md)).

## `slice(label, n, stroke)`

```typst
slice(label: "1", n: 2, stroke: blue)
```

- `label` — content / string / dictionary, the slice label.
- `n: int` — how many wires to slice down (default = all).
- `stroke` — line style; default is a red dashed `.7pt` line.
- `z: "above" | "below"` — whether the slice draws above or below the
  circuit (default `"below"`).

## `gategroup(wires, steps, ...)`

```typst
gategroup(3, 3, label: (content: "Syndrome", pos: bottom))
```

- `wires` (positional int) — number of wires to span downward.
- `steps` (positional int) — number of columns to span rightward.
- `x: int | auto`, `y: int | auto` — starting column / row (default = current).
- `right: int | auto`, `bottom: int | auto` — alternative end coords.
- `padding: length | dictionary` — inset around the box.
- `stroke`, `fill`, `radius` — usual rectangle styling.
- `label` — group label; can sit at `top | bottom | left | right` etc.

When `right` / `bottom` is set, the corresponding positional arg is
ignored. The padding dictionary keys are `left`, `right`, `top`,
`bottom`, `default`.

## Combined example

```typst
#quantum-circuit(
  1, gate($H$), ctrl(1),
  slice(label: "1"), 1,
  gategroup(3, 3, label: (content: "Syndrome", pos: bottom)),
  1, ctrl(2), ctrl(), 1,
  slice(label: "3", n: 2, stroke: blue),
  2, [\ ],
  2, targ(), 1, ctrl(1), 1, ctrl(), 3, [\ ],
  4, targ(), targ(), meter(target: -2)
)
```

See [`examples/05-slices-and-groups/05-slices-and-groups.typ`](examples/05-slices-and-groups/05-slices-and-groups.typ).

## Pitfalls

- `slice()` always reaches **down to the last wire** unless you set `n:`.
- `gategroup` is positional: `gategroup(3, 3)` is *3 wires × 3 steps*,
  **not** column 3 × row 3. Manual placement uses `x: ...` and `y: ...`.
- `padding: 1.5em` adds **only on the inside** — the outer bounding box
  of the circuit may need `circuit-padding` (see styling) to keep
  labels from being clipped.

## Next

[`06-labels.md`](06-labels.md) — the full label dictionary, used by
gates, slices and groups alike.
